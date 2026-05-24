# telegram_bot.py (비동기 텔레그램 봇 데몬 및 알림 브릿지)

import os
import sys
import asyncio
import re
import json
import sqlite3
import logging
import threading
import urllib.parse
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# agents 및 shared 설정 임포트
from agents.shared.config import (
    WIKI_DIR, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, FINANCIAL_DATA_PATH, DECISIONS_PATH, ROOT_DIR,
    CHAT_LOG_DIR, TELEGRAM_DB_PATH
)
from agents.shared.text_utils import escape_markdown_for_telegram
from agents.shared.file_utils import write_file_safely
from agents.chief_agent import ChiefAgent
from agents.wiki_manager import WikiManager
from agents.shared.ollama_client import call_ollama, call_ollama_json  # [R7 추가] call_ollama_json 임포트 보완
from agents.db_manager import DBManager

# [R11 신설] 능동형 프로액티브 모니터링 임계값 및 쿨다운 설정 (주기 극소화 튜닝)
PROACTIVE_BTC_CHANGE_THRESHOLD = 1.5   # BTC 1시간 변동률 1.5%
PROACTIVE_FX_CHANGE_THRESHOLD = 0.5    # 원/달러 환율 1시간 변동률 0.5%
PROACTIVE_COOLDOWN_HOURS = 0.25         # [극소화] 경보 발령 후 쿨다운 15분 (0.25시간)
last_proactive_alert_time = None       # 마지막 경보 발송 시각

# 중복 수집/분석 방지용 전역 락 플래그
is_updating = False

# 봇 기동 준비용 토큰 검증
BOT_TOKEN = TELEGRAM_BOT_TOKEN
CHAT_ID = TELEGRAM_CHAT_ID

# 멀티스레드/멀티세션 환경 보호를 위한 전역 SQLite 락
db_lock = threading.Lock()

def init_chat_db():
    """telegram_chat.db 초기화 (에러 추적용 FileHandler 동적 인스턴스화 수행)"""
    chat_error_logger = logging.getLogger("chat_error")
    if not chat_error_logger.handlers:
        chat_error_logger.setLevel(logging.ERROR)
        try:
            file_handler = logging.FileHandler(CHAT_LOG_DIR / "chat_error.log", encoding="utf-8")
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            chat_error_logger.addHandler(file_handler)
        except Exception as e:
            print(f"[!] 에러 로그 파일 핸들러 초기화 실패: {e}")
            
    with db_lock:
        try:
            conn = sqlite3.connect(TELEGRAM_DB_PATH, timeout=30.0)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telegram_chat_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    message_text TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("PRAGMA journal_mode=WAL;")
            conn.commit()
            conn.close()
            print("[+] 텔레그램 로컬 SQLite 대화 데이터베이스 초기화 완료 (WAL & Lock).")
        except Exception as e:
            chat_error_logger.error(f"SQLite DB 초기화 중 오류 발생: {e}", exc_info=True)
            print(f"[!] SQLite DB 초기화 중 치명적 오류 발생: {e}")

async def log_chat_message(sender: str, message_text: str, session_id: str):
    """비동기 이벤트 루프 블로킹 소거를 위해 SQLite Insert 작업을 스레드 풀에 위임하여 기록"""
    main_loop = asyncio.get_running_loop()
    safe_text = message_text or ""
    kst = timezone(timedelta(hours=9))
    now_str = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")

    def _send_emergency_notification(err_msg: str):
        """SQLite 로그 저장 실패 시 비상 알림 발송 (스레드 안전)"""
        try:
            from telegram import Bot
            if BOT_TOKEN and CHAT_ID:
                emergency_bot = Bot(token=BOT_TOKEN)
                asyncio.run_coroutine_threadsafe(
                    emergency_bot.send_message(
                        chat_id=CHAT_ID,
                        text=f"⚠️ *[SQLite DB 경보]* 대화 로그 적재 실패!\n에러: `{err_msg}`",
                        parse_mode="Markdown"
                    ),
                    main_loop
                )
        except Exception as notify_err:
            chat_error_logger = logging.getLogger("chat_error")
            chat_error_logger.error(f"비상 에러 통보 발송 실패: {notify_err}")

    def _sync_insert():
        chat_error_logger = logging.getLogger("chat_error")
        with db_lock:
            try:
                conn = sqlite3.connect(TELEGRAM_DB_PATH, timeout=30.0)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO telegram_chat_logs (session_id, sender, message_text, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (str(session_id), sender, safe_text, now_str)
                )
                conn.commit()
                conn.close()
            except Exception as e:
                chat_error_logger.error(f"SQLite 대화 로그 저장 실패 (발신자: {sender}, 세션: {session_id}): {e}", exc_info=True)
                _send_emergency_notification(str(e))

    await asyncio.to_thread(_sync_insert)

def is_token_valid() -> bool:
    """토큰 설정 여부 유효성 검사"""
    return BOT_TOKEN and BOT_TOKEN != "your_telegram_bot_token" and CHAT_ID != "your_telegram_chat_id"

def parse_wiki_for_telegram(wiki_name: str) -> str:
    """
    위키 마크다운 파일에서 YAML Frontmatter 및 코드 블록 메타데이터를 정밀 소거하고,
    '## 📌 종합 요약 (Executive Summary)' 섹션 하위의 3줄 핵심 알짜 요약문만
    가독성 높게 추출하여 텔레그램으로 반환합니다.
    """
    file_path = WIKI_DIR / f"{wiki_name}.md"
    if not file_path.exists():
        return f"📂 아직 생성된 [[{wiki_name}]] 위키 페이지가 없습니다.\n먼저 수집 및 분석을 가동해주세요."
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
            
        # 1. 상단 YAML Frontmatter (--- ... ---) 제거
        yaml_pattern = re.compile(r'^---\s*\n.*?\n---\s*\n', re.DOTALL | re.MULTILINE)
        text = yaml_pattern.sub("", text)
        
        # 2. 본문에 중복 포함될 수 있는 ```yaml / ```markdown 등 코드 블록 메타데이터 영역 일체 제거
        code_block_pattern = re.compile(r'```(?:yaml|markdown|text)?\n.*?\n```', re.DOTALL)
        text = code_block_pattern.sub("", text)
        
        # 3. '## 📌 종합 요약 (Executive Summary)' 섹션 내용만 정밀 캡처
        summary_pattern = re.compile(
            r'## 📌 종합 요약 \(Executive Summary\)\s*\n(.*?)(?=\n##|\n#|$)', 
            re.DOTALL | re.IGNORECASE
        )
        match = summary_pattern.search(text)
        if match:
            summary = match.group(1).strip()
            
            # [가독성 극대화 가공] 만약 기존 문서가 불릿 포인트(•)가 아닌 단순 줄글 서술형인 경우
            # 즉시 문장 단위로 분해하여 • 핵심, • 이슈, • 전망 기반의 모바일 특화 개조식 카드로 실시간 포맷 보정
            if not summary.startswith("•") and not summary.startswith("-"):
                # 마침표 및 공백 기준으로 문장 쪼개기
                sentences = re.split(r'\.(?:\s+|$)', summary)
                sentences = [s.strip() for s in sentences if s.strip()]
                
                bulleted = []
                labels = ["핵심", "변수", "전망"]
                for idx, sentence in enumerate(sentences[:3]):
                    lbl = labels[idx] if idx < len(labels) else "분석"
                    bulleted.append(f"• **{lbl}:** {sentence}.")
                summary = "\n".join(bulleted)
                
            return summary
            
        # 4. Fallback: 만약 '종합 요약' 섹션 포착에 실패할 경우, 본문 중 제목/테이블 등을 쳐낸 최상단 3문장만 반환
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        paragraphs = []
        for line in lines:
            if line.startswith("#") or line.startswith("`") or line.startswith("|") or line.startswith("-"):
                continue
            paragraphs.append(line)
            if len(paragraphs) >= 2:
                break
                
        fallback_body = "\n\n".join(paragraphs).strip()
        if not fallback_body:
            fallback_body = text[:400].strip() + "..."
            
        return fallback_body
    except Exception as e:
        return f"❌ [[{wiki_name}]] 로딩 실패: {e}"

def make_financial_card() -> str:
    """실시간 금융 지표 캐시 파일을 텔레그램 마크다운 카드로 포맷팅 (BTC USD + 알트코인 포함)"""
    if not FINANCIAL_DATA_PATH.exists():
        return ""
    try:
        with open(FINANCIAL_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        btc_krw = data.get("btc_krw", 0)
        btc_krw_change = data.get("btc_krw_change", 0)
        btc_usd = data.get("btc_usd", 0)
        exchange_rate = data.get("exchange_rate", 0)
        bok_rate = data.get("bok_rate", 0)
        kimchi_premium = data.get("kimchi_premium", 0)
        updated_at = data.get("updated_at", "")
        altcoins: dict = data.get("altcoins", {})

        btc_change_sign = "+" if btc_krw_change > 0 else ""
        kimp_sign = "+" if kimchi_premium > 0 else ""

        # 알트코인 이모지 매핑
        ALTCOIN_EMOJI = {
            "ETH": "🔷", "XRP": "🔵", "SOL": "🟣",
            "SAND": "🏖", "MANA": "🌐", "DOGE": "🐶", "WAVES": "🌊"
        }

        # 알트코인 라인 생성 (KRW + USD 둘 다 표기, 미지원 코인도 항상 표시)
        alt_lines = ""
        ALT_ORDER = ["ETH", "XRP", "SOL", "DOGE", "SAND", "MANA", "WAVES"]
        for symbol in ALT_ORDER:
            emoji = ALTCOIN_EMOJI.get(symbol, "🔹")
            if symbol not in altcoins:
                # Upbit 미지원 또는 수집 실패
                alt_lines += f"• {emoji} *{symbol}*: `N/A`\n"
                continue
            info = altcoins[symbol]
            krw_p = info.get("krw", 0)
            usd_p = info.get("usd", 0)
            chg = info.get("change", 0)
            chg_sign = "+" if chg >= 0 else ""
            # KRW 포맷: 가격대별 소수점 자동 조정
            if krw_p < 1:
                krw_str = f"{krw_p:.4f}원"
            elif krw_p < 10:
                krw_str = f"{krw_p:.2f}원"
            else:
                krw_str = f"{krw_p:,.0f}원"
            # USD 포맷
            if usd_p < 0.001:
                usd_str = f"${usd_p:.6f}"
            elif usd_p < 1:
                usd_str = f"${usd_p:.4f}"
            else:
                usd_str = f"${usd_p:,.4f}"
            alt_lines += f"• {emoji} *{symbol}*: `{krw_str}` / `{usd_str}` ({chg_sign}{chg:.2f}%)\n"

        card = f"""📊 *[실시간 금융/크립토 주요 지표]*
• 🪙 *Bitcoin (Upbit)*: `{btc_krw:,.0f}원` / `${btc_usd:,.2f}` ({btc_change_sign}{btc_krw_change:.2f}%)
• ⚡ *김치 프리미엄*: `{kimp_sign}{kimchi_premium:.2f}%`
• 💵 *원/달러 환율*: `{exchange_rate:,.2f}원`
• 🇰🇷 *한국 기준금리*: `{bok_rate:.2f}%`
• 🕒 *기준시*: `{updated_at}`
━━━━━━━━━━━━━━━━━━━━━
📈 *[알트코인 시세]*
{alt_lines.rstrip()}
━━━━━━━━━━━━━━━━━━━━━
"""
        return card
    except Exception as e:
        print(f"[!] 금융 지표 카드 렌더링 에러: {e}")
    return ""

# --- 텔레그램 대화형 명령어 핸들러 정의 ---

async def _send_help_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Message:
    """순수하게 명령어 안내 템플릿만 전송하는 헬퍼 (사용자 발화 로그 꼬임 방지 공용 참조)"""
    help_text = """
🤖 *로컬 Obsidian LLM Wiki 비서 (Multi-Agent v3.0)* 입니다.
매일 로컬 에이전트들이 협업하여 뉴스를 학습하고 점진적으로 누적(Compounding)한 지식을 이곳에서 바로 조회하실 수 있습니다.

*📬 지식 조회 및 제어 명령어 목록:*
• /update - 🔄 실시간 에이전트 릴레이 파이프라인 가동 (0선 금융 ➡️ 3대 수집 ➡️ 위키 누적 분석)
• /비트코인 또는 /bitcoin - 가상자산/비트코인 누적 위키 요약 조회
• /세계경제 또는 /fed - 미국 연준 통화정책 및 글로벌 매크로 분석 조회
• /국내경제 또는 /korea - 한국 기준금리 및 거시경제 지표 추이 조회
• /log - 오늘 수행된 에이전트 릴레이 활동 성능 성적표 조회
"""
    return await update.message.reply_text(help_text, parse_mode="Markdown")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start 및 /help 명령어 수신 시 지원 목록 반환"""
    actual_input = update.message.text or "/start"
    await log_chat_message(sender="user", message_text=actual_input, session_id=str(update.message.chat_id))

    msg = await _send_help_template(update, context)
    await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(update.message.chat_id))

async def bitcoin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """비트코인 위키 전송"""
    actual_input = update.message.text or "/bitcoin"
    await log_chat_message(sender="user", message_text=actual_input, session_id=str(update.message.chat_id))

    report = parse_wiki_for_telegram("Bitcoin")
    msg = await update.message.reply_text(f"🪙 *[Bitcoin] 가상자산 지식 누적 분석*\n\n{report}")
    await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(update.message.chat_id))

async def fed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """글로벌 매크로 위키 전송"""
    actual_input = update.message.text or "/fed"
    await log_chat_message(sender="user", message_text=actual_input, session_id=str(update.message.chat_id))

    report = parse_wiki_for_telegram("US-Fed")
    msg = await update.message.reply_text(f"🌍 *[US-Fed] 글로벌 거시경제 지식 누적 분석*\n\n{report}")
    await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(update.message.chat_id))

async def korea_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """국내 경제 위키 전송"""
    actual_input = update.message.text or "/korea"
    await log_chat_message(sender="user", message_text=actual_input, session_id=str(update.message.chat_id))

    report = parse_wiki_for_telegram("Korea-Economy")
    msg = await update.message.reply_text(f"🇰🇷 *[Korea-Economy] 국내 경제 지식 누적 분석*\n\n{report}")
    await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(update.message.chat_id))

async def log_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """log.md of 최근 5개 로그 발송"""
    actual_input = update.message.text or "/log"
    await log_chat_message(sender="user", message_text=actual_input, session_id=str(update.message.chat_id))

    log_file = WIKI_DIR / "log.md"
    if not log_file.exists():
        msg = await update.message.reply_text("📂 에이전트 활동 로그가 아직 없습니다.")
        await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(update.message.chat_id))
        return
        
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # 최근 5개 로그 항목 추출 (## [ 으로 시작하는 로그)
        recent_logs = []
        for line in reversed(lines):
            if line.startswith("## "):
                recent_logs.append(line.strip())
                if len(recent_logs) >= 5:
                    break
                    
        log_text = "📋 *최근 5건의 에이전트 활동 이력:*\n\n" + "\n".join(recent_logs)
        msg = await update.message.reply_text(log_text)
        await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(update.message.chat_id))
    except Exception as e:
        msg = await update.message.reply_text(f"❌ 로그 조회 오류: {e}")
        await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(update.message.chat_id))

async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """실시간 에이전트 릴레이 협업(0선 DB 수집 ➡️ 3대 리포터 Ingestion ➡️ 위키 누적 합성) 가동"""
    global is_updating

    actual_input = update.message.text or "/update"
    await log_chat_message(sender="user", message_text=actual_input, session_id=str(update.message.chat_id))

    if is_updating:
        msg = await update.message.reply_text("🔄 현재 AI 비서 패키지가 다른 뉴스들을 열심히 분석하는 중입니다. 완료 후 안내해 드릴게요! 잠시만 기다려 주세요.")
        await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(update.message.chat_id))
        return
        
    status_msg = await update.message.reply_text("🔄 *1단계: 0선 금융 데이터를 선행 수집하고 3대 경제/크립토 에이전트를 동원 중입니다...* (약 10~30초 소요)", parse_mode="Markdown")
    await log_chat_message(sender="bot", message_text=status_msg.text or "", session_id=str(update.message.chat_id))
    is_updating = True
    
    try:
        # 1. ChiefAgent를 활용한 순차 릴레이 구동 (비동기 루프 친화적으로 asyncio.to_thread 실행)
        agent = ChiefAgent()
        briefing_message = await asyncio.to_thread(agent.run_relay)
        
        # 2. 완료 갱신 및 전송
        await status_msg.delete()  # 상태 메시지 삭제
        msg_briefing = await update.message.reply_text(briefing_message, parse_mode="Markdown")
        await log_chat_message(sender="bot", message_text=msg_briefing.text or "", session_id=str(update.message.chat_id))
        
        # [R4 추가] 임시 대기실(approvals/pending)에 합성 초안이 존재한다면, 사용자 승인 카드 발송
        draft_dir = ROOT_DIR / "_company" / "approvals" / "pending"
        if draft_dir.exists():
            drafts = list(draft_dir.glob("*_draft.md"))
            if drafts:
                for draft in drafts:
                    wiki_name = draft.name.replace("_draft.md", "")
                    keyboard = [
                        [
                            InlineKeyboardButton("🟢 승인 및 위키 병합", callback_data=f"approve_{wiki_name}"),
                            InlineKeyboardButton("🔴 반려 및 삭제 파기", callback_data=f"reject_{wiki_name}")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    msg_card = await update.message.reply_text(
                        text=f"⚖️ *[금융 위키 합성 승인 대기]*\n\n"
                             f"대상 위키: `[[{wiki_name}]]`\n"
                             f"수집된 정보와 당일 지표가 반영된 위키 초안이 대기 중입니다. 하단의 버튼을 통해 처리해 주십시오.",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                    await log_chat_message(sender="bot", message_text=msg_card.text or "", session_id=str(update.message.chat_id))
        
    except Exception as e:
        try:
            msg_err = await status_msg.edit_text(f"❌ 에이전트 릴레이 가동 중 오류 발생:\n`{e}`", parse_mode="Markdown")
            await log_chat_message(sender="bot", message_text=msg_err.text or "", session_id=str(update.message.chat_id))
        except Exception as edit_err:
            msg_err = await update.message.reply_text(f"❌ 에이전트 릴레이 가동 중 오류 발생:\n`{e}`", parse_mode="Markdown")
            await log_chat_message(sender="bot", message_text=msg_err.text or "", session_id=str(update.message.chat_id))
    finally:
        is_updating = False

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """[R4 신설] 텔레그램 컨펌 버튼 클릭 시 decisions.md 이력 누적 파일 I/O 및 사후 index/log 업데이트 콜백 핸들러"""
    global is_updating
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # [R11 프로액티브 분기 확인]
    if data.startswith("proactive_"):
        action = data
        wiki_name = ""
    else:
        action, wiki_name = data.split("_", 1)
    
    draft_path = ROOT_DIR / "_company" / "approvals" / "pending" / f"{wiki_name}_draft.md"
    official_path = Path(WIKI_DIR) / f"{wiki_name}.md"
    
    await log_chat_message(sender="user", message_text=f"[Callback Click] {data}", session_id=str(query.message.chat_id))

    if action == "proactive_run":
        if is_updating:
            await query.edit_message_text(text="🔄 현재 이미 경제 뉴스 분석이 백그라운드에서 실행 중입니다. 잠시만 대기해 주십시오!")
            return
            
        try:
            await query.edit_message_text(
                text="⚡ *[능동형 모니터 분석 개시]* 지식 릴레이 파이프라인(0선~4선) 및 AI 합동 언론 데스크를 즉시 긴급 구동합니다... (약 1~2분 소요)",
                parse_mode="Markdown"
            )
            is_updating = True
            
            # ChiefAgent 릴레이 실행
            agent = ChiefAgent()
            briefing_message = await asyncio.to_thread(agent.run_relay)
            
            # 릴레이 브리핑 메시지 송출
            await query.message.reply_text(briefing_message, parse_mode="Markdown")
            
            # 위키 승인 대기실 초안 체크
            draft_dir = ROOT_DIR / "_company" / "approvals" / "pending"
            if draft_dir.exists():
                drafts = list(draft_dir.glob("*_draft.md"))
                if drafts:
                    for draft in drafts:
                        wiki_name_pending = draft.name.replace("_draft.md", "")
                        keyboard = [
                            [
                                InlineKeyboardButton("🟢 승인 및 위키 병합", callback_data=f"approve_{wiki_name_pending}"),
                                InlineKeyboardButton("🔴 반려 및 삭제 파기", callback_data=f"reject_{wiki_name_pending}")
                            ]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await query.message.reply_text(
                            text=f"⚖️ *[금융 위키 합성 승인 대기]*\n\n"
                                 f"대상 위키: `[[{wiki_name_pending}]]`\n"
                                 f"수집된 정보와 당일 지표가 반영된 위키 초안이 대기 중입니다. 하단의 버튼을 통해 처리해 주십시오.",
                            reply_markup=reply_markup,
                            parse_mode="Markdown"
                        )
        except Exception as e:
            await query.message.reply_text(f"❌ 프로액티브 릴레이 가동 실패: {e}")
        finally:
            is_updating = False
        return

    elif action == "proactive_dismiss":
        await query.edit_message_text(text="✅ *경보 확인 완료.* 향후 15분 동안 동종 경보는 비활성화(쿨다운) 처리됩니다.", parse_mode="Markdown")
        return

    elif action == "approve":
        if draft_path.exists():
            try:
                # 1. 초안 마크다운 파일을 공식 마스터 위키 경로에 안전하게 저장
                with open(draft_path, "r", encoding="utf-8") as df:
                    content = df.read()
                write_file_safely(official_path, content)
                draft_path.unlink()  # 대기실의 초안 삭제
                
                # 2. decisions.md 파일에 실시간 의사결정 이력 추가 기록 (Append) - 이중 래핑 소거
                decisions_path = DECISIONS_PATH
                decisions_path.parent.mkdir(parents=True, exist_ok=True)
                
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                decision_entry = f"\n## [{now_str}] {wiki_name} 지식 컴파운딩 승인\n" \
                                 f"- [[{wiki_name}]] 위키 초안이 사용자의 수동 승인을 받아 공식 지식베이스에 통합 갱신되었습니다.\n"
                                 
                with open(decisions_path, "a", encoding="utf-8") as f:
                    f.write(decision_entry)
                
                # 3. 사후 index.md와 log.md 업데이트
                try:
                    wm = WikiManager()
                    wm._update_index_and_log("telegram_approved", "수동 승인 위키 합성", wiki_name)
                    print(f"[+] 위키 승인 성공 및 사후 index/log 업데이트 완료: {wiki_name}")
                except Exception as e:
                    print(f"[!] 사후 index/log 업데이트 중 오류: {e}")
                
                msg = await query.edit_message_text(
                    text=f"✅ *[[{wiki_name}]] 승인 완료*\n"
                          f"공식 위키 병합 완료 및 `decisions.md` 기록이 업데이트되었습니다.",
                    parse_mode="Markdown"
                )
                await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(query.message.chat_id))
            except Exception as e:
                chat_error_logger = logging.getLogger("chat_error")
                chat_error_logger.error(f"콜백 처리 도중 예외 발생 (approve_{wiki_name}): {e}", exc_info=True)
                try:
                    msg = await query.edit_message_text(text=f"❌ 승인 처리 중 파일 I/O 오류 발생: {e}")
                    await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(query.message.chat_id))
                except Exception as edit_err:
                    chat_error_logger.error(f"예외 상황 메시지 수정 실패: {edit_err}", exc_info=True)
        else:
            try:
                msg = await query.edit_message_text(text="⚠️ 오류: 대기 중인 초안 파일을 찾을 수 없습니다.")
                await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(query.message.chat_id))
            except Exception as edit_err:
                logging.getLogger("chat_error").error(f"예외 상황 메시지 수정 실패: {edit_err}", exc_info=True)
            
    elif action == "reject":
        if draft_path.exists():
            try:
                draft_path.unlink()
                msg = await query.edit_message_text(
                    text=f"❌ *[[{wiki_name}]] 반려 완료*\n"
                          f"작성된 초안 마크다운이 대기실에서 삭제 파기되었습니다.",
                    parse_mode="Markdown"
                )
                await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(query.message.chat_id))
            except Exception as e:
                chat_error_logger = logging.getLogger("chat_error")
                chat_error_logger.error(f"콜백 처리 도중 예외 발생 (reject_{wiki_name}): {e}", exc_info=True)
                try:
                    msg = await query.edit_message_text(text=f"❌ 파일 삭제 중 오류 발생: {e}")
                    await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(query.message.chat_id))
                except Exception as edit_err:
                    chat_error_logger.error(f"예외 상황 메시지 수정 실패: {edit_err}", exc_info=True)
        else:
            try:
                msg = await query.edit_message_text(text="⚠️ 오류: 이미 처리되었거나 대기 중인 초안 파일을 찾을 수 없습니다.")
                await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(query.message.chat_id))
            except Exception as edit_err:
                logging.getLogger("chat_error").error(f"예외 상황 메시지 수정 실패: {edit_err}", exc_info=True)

# --- 브리핑 알림(Push) 발송용 비동기 함수 ---

def _read_latest_risk_score() -> str:
    """
    obsidian-vault/raw/strategy/ 에서 가장 최신 *_risk_assessment.md 파일을 탐색하여
    리스크 점수 및 한줄 요약을 추출합니다. 실패 시 빈 문자열 반환.

    실제 LLM 출력 포맷 기준:
      - 점수: '### 📉 종합 리스크 등급: 8/10'
      - 요약: '**[판단 근거 요약]**' 이후 첫 문단, fallback → '**[핵심 경고]**' 이후 첫 문장
    """
    try:
        strategy_dir = ROOT_DIR / "obsidian-vault" / "raw" / "strategy"
        if not strategy_dir.exists():
            return ""
        candidates = sorted(strategy_dir.glob("*_risk_assessment.md"), reverse=True)
        if not candidates:
            return ""
        latest = candidates[0]
        content = latest.read_text(encoding="utf-8")

        import re

        # ── 1. 리스크 점수 추출 ──────────────────────────────────────
        # 포맷: "종합 리스크 등급: 8/10"  또는  "리스크 등급: 7/10"
        score_match = re.search(
            r"(?:종합\s*)?리스크\s*등급[:\s：]*(\d+)\s*/\s*10",
            content, re.IGNORECASE
        )
        # fallback: "8등급" 단독 표현
        if not score_match:
            score_match = re.search(r"(\d+)\s*등급", content)
        score_str = f"{score_match.group(1)}/10" if score_match else "N/A"

        # ── 2. 한줄 요약 추출 ────────────────────────────────────────
        one_line = ""
        # 우선순위 1: **[판단 근거 요약]** 이후 첫 문단
        summary_match = re.search(
            r"\*\*\[판단\s*근거\s*요약\]\*\*\s*\n+(.*?)(?:\n\n|\n\*\*|\n#+|$)",
            content, re.DOTALL
        )
        if summary_match:
            raw = summary_match.group(1).strip().split("\n")[0]
            one_line = re.sub(r"\*+", "", raw).strip()[:90]

        # 우선순위 2: **[핵심 경고]** 이후 첫 문장
        if not one_line:
            warn_match = re.search(
                r"\*\*\[핵심\s*경고\]\*\*\s*\n+(.*?)(?:\n\n|\n#|$)",
                content, re.DOTALL
            )
            if warn_match:
                raw = warn_match.group(1).strip().split("\n")[0]
                one_line = re.sub(r"\*+", "", raw).strip()[:90]

        # 우선순위 3: 헤더·테이블·코드 제외 첫 일반 텍스트 줄
        if not one_line:
            for line in content.split("\n"):
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and not stripped.startswith("|") \
                        and not stripped.startswith("```") and not stripped.startswith("**["):
                    one_line = re.sub(r"\*+", "", stripped).strip()[:90]
                    break

        summary_part = f"\n   _{one_line}_" if one_line else ""
        return f"🚨 *리스크 점수*: `{score_str}`{summary_part}"
    except Exception as e:
        print(f"[!] 리스크 점수 읽기 실패: {e}")
        return ""


async def send_briefing_notification():
    """정기 스케줄 뉴스 분석 완료 시 텔레그램 채널에 브리핑 요약을 푸시 발송하는 함수"""
    if not is_token_valid():
        print("[!] 텔레그램 알림 발송 생략 (유효한 TOKEN 및 CHAT_ID 미설정)")
        return

    print("[*] 텔레그램 알림 브리핑 발송 준비 중...")
    app = Application.builder().token(BOT_TOKEN).build()

    # 3대 위키 문서 요약 추출
    btc_report = escape_markdown_for_telegram(parse_wiki_for_telegram("Bitcoin"))
    fed_report = escape_markdown_for_telegram(parse_wiki_for_telegram("US-Fed"))
    kor_report = escape_markdown_for_telegram(parse_wiki_for_telegram("Korea-Economy"))

    # 실시간 금융 지표 카드 (BTC KRW/USD + 알트코인)
    fin_card = make_financial_card()

    # 5선 리스크 점수 (최신 세션 파일에서 추출)
    risk_section = _read_latest_risk_score()

    # AI 분석 면책 문구
    ai_disclaimer = "⚠️ _아래 요약은 로컬 AI(Ollama)가 생성한 분석으로, 실제 수치와 다를 수 있습니다._"

    briefing_message = f"""🔔 *[로컬 LLM Wiki] 자동 정기 요약 브리핑*

{fin_card}"""

    # 5선 리스크 점수 섹션 (있을 때만 추가)
    if risk_section:
        briefing_message += f"""🎯 *[5선 전략 분석 — 리스크 진단]*
{risk_section}
━━━━━━━━━━━━━━━━━━━━━
"""

    briefing_message += f"""{ai_disclaimer}

🪙 *비트코인 동향 요약:*
{btc_report}

🌍 *글로벌 매크로 요약:*
{fed_report}

🇰🇷 *국내 경제 요약:*
{kor_report}

💡 상세 분석 및 전체 지식 크로스링크는 옵시디언 앱(Vault)에서 확인하세요!
"""

    try:
        await app.bot.send_message(chat_id=CHAT_ID, text=briefing_message, parse_mode="Markdown")
        print("[+] 텔레그램 일일 브리핑 메시지 발송 완료!")
        await log_chat_message(sender="bot", message_text=briefing_message or "", session_id=str(CHAT_ID))
    except Exception as e:
        chat_error_logger = logging.getLogger("chat_error")
        chat_error_logger.error(f"텔레그램 브리핑 발송 실패 (챗 로그 적재 생략): {e}", exc_info=True)
        print(f"[!] 텔레그램 브리핑 발송 실패: {e}")

def fetch_realtime_news(query: str, limit: int = 5) -> list:
    """구글 뉴스 RSS 피드를 활용하여 실시간 뉴스를 안전하게 스크래핑합니다."""
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    articles = []
    try:
        response = requests.get(rss_url, headers=headers, timeout=12)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            items = root.findall(".//item")
            for item in items[:limit]:
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                description = item.find("description").text if item.find("description") is not None else ""
                
                soup_desc = BeautifulSoup(description, "html.parser")
                clean_desc = soup_desc.get_text().strip()
                
                # 언론사 정보 파싱 시도 (제목의 ' - 언론사' 포맷 활용)
                publisher = "구글 뉴스"
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title = parts[0].strip()
                    publisher = parts[1].strip()
                
                articles.append({
                    "title": title,
                    "url": link,
                    "pub_date": pub_date,
                    "description": clean_desc,
                    "publisher": publisher
                })
    except Exception as e:
        print(f"[!] 실시간 뉴스 RSS 수집 장애 발생: {e}")
    return articles

async def analyze_news_request(text: str) -> tuple:
    """
    사용자의 입력이 실시간 뉴스/이슈 검색 및 요약 요청인지 AI를 통해 분석하고,
    검색 엔진에 전달할 핵심 키워드를 추출합니다.
    """
    keywords = ["뉴스", "이슈", "소식", "최근", "요약", "정리", "근황", "보여줘", "알려줘", "보고해"]
    # 1. 1차 빠른 매칭 검사
    if not any(kw in text for kw in keywords):
        return False, ""
        
    # 2. 2차 Ollama 기반 지능형 스키마 분석
    prompt = (
        f"사용자의 자연어 질문: '{text}'\n\n"
        "위 질문이 실시간 인터넷 뉴스, 기업 근황, 거시경제 이슈 등에 대한 웹 검색 요약을 요청하는 내용인지 판별해 주세요.\n"
        "만약 검색이 필요하다면, 구글 뉴스 RSS 피드에 전달할 명사 위주의 가장 핵심적인 검색 키워드(예: '삼성전자', '비트코인 규제', '금리 인하' 등)를 단 한 개만 추출하십시오.\n"
        "반드시 다음 JSON 형식에 정확히 맞춰서만 답변해야 하며, 사족이나 보충 설명은 절대로 출력하지 마십시오:\n"
        '{"is_news_request": true, "search_keyword": "추출한키워드"}'
    )
    
    def _call():
        return call_ollama_json(prompt, "당신은 한국어 핵심 키워드 및 의도 판정기입니다. 사족 없이 오직 JSON만 반환합니다.")

    try:
        res = await asyncio.to_thread(_call)
        if res and isinstance(res, dict):
            return res.get("is_news_request", False), res.get("search_keyword", "")
    except Exception as e:
        print(f"[!] 올라마 뉴스 의도 판단 실패: {e}")
    return False, ""

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """사용자가 슬래시 없이 한글로 텍스트 메시지를 보냈을 때 지능적으로 판단하여 위키 전송 혹은 LLM 기반 지능형 일상대화 수행"""
    text = update.message.text.strip() if update.message.text else ""
    
    # 1. 키워드 기반 위키 요약/제어 분기 매칭
    if any(kw in text for kw in ["업데이트", "가져와", "동기화"]):
        await update_command(update, context)
        return
    elif any(kw in text.lower() for kw in [
        "시황", "코인", "크립토", "crypto", "현재가", "시세", "브리핑", "지표"
    ]):
        # 시황/코인/시세 관련 질문 → 실시간 금융 카드 + BTC 위키 + 알트코인 즉시 발송
        await log_chat_message(sender="user", message_text=text, session_id=str(update.message.chat_id))
        fin_card = make_financial_card()
        btc_report = escape_markdown_for_telegram(parse_wiki_for_telegram("Bitcoin"))
        risk_line = _read_latest_risk_score()
        reply = (
            f"📊 *[실시간 코인 시황 브리핑]*\n\n"
            f"{fin_card}"
            + (f"🎯 *[5선 리스크 진단]*\n{risk_line}\n━━━━━━━━━━━━━━━━━━━━━\n" if risk_line else "")
            + f"🪙 *비트코인 동향 요약:*\n{btc_report}\n\n"
            f"💡 세계경제·국내경제 분석은 /fed /korea 로 조회하세요."
        )
        msg = await update.message.reply_text(reply, parse_mode="Markdown")
        await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(update.message.chat_id))
        return
    elif "비트코인" in text or "bitcoin" in text.lower():
        await bitcoin_command(update, context)
        return
    elif "세계경제" in text or "fed" in text.lower() or "연준" in text:
        await fed_command(update, context)
        return
    elif "국내경제" in text or "korea" in text.lower() or "한국경제" in text:
        await korea_command(update, context)
        return
    elif "로그" in text or "log" in text.lower() or "기록" in text:
        await log_command(update, context)
        return
    elif text.startswith("/") or any(text.startswith(kw) for kw in ["도움말", "명령어", "메뉴", "시작"]):
        await start_command(update, context)
        return

    # 2. [R7 지능형 실시간 뉴스 RAG 검색 기능] 도입
    # 사용자의 질문이 특정 이슈/실시간 뉴스를 요구하는지 지능적으로 확인
    is_news, search_kw = await analyze_news_request(text)
    
    if is_news and search_kw:
        # 사용자 질문(발화) 로깅
        await log_chat_message(sender="user", message_text=text, session_id=str(update.message.chat_id))
        
        # 봇이 검색 및 분석 중 상태를 텔레그램 화면에 실시간 노출
        try:
            await context.bot.send_chat_action(chat_id=update.message.chat_id, action="typing")
            # "실시간 뉴스를 검색하고 정리 중입니다" 선행 알림
            temp_msg = await update.message.reply_text(
                f"🔍 *[실시간 웹 검색 RAG 가동]*\n사용자님의 요청을 위해 인터넷에서 `{search_kw}` 관련 최신 뉴스를 수집하고 있습니다. 잠시만 기다려 주세요... 💬",
                parse_mode="Markdown"
            )
            await context.bot.send_chat_action(chat_id=update.message.chat_id, action="typing")
        except Exception:
            temp_msg = None

        news_list = await asyncio.to_thread(fetch_realtime_news, search_kw, 5)
        
        if not news_list:
            if temp_msg:
                try:
                    await temp_msg.delete()
                except Exception:
                    pass
            msg = await update.message.reply_text(f"📂 죄송합니다. 인터넷에서 `{search_kw}` 관련 최신 뉴스를 수집하는 데 실패했거나 뉴스가 존재하지 않습니다.")
            await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(update.message.chat_id))
            return
            
        context_str = ""
        for idx, news in enumerate(news_list):
            context_str += f"[{idx+1}] {news['title']}\n- 언론사: {news['publisher']} | 발송일시: {news['pub_date']}\n- 요약: {news['description']}\n\n"
            
        system_prompt = (
            f"당신은 실시간 인터넷 뉴스 RAG 브리핑을 담당하는 비서 에이전트 'Antigravity 비서'입니다.\n"
            f"검색된 최신 뉴스 컨텍스트를 종합하여, 사용자의 질문에 객관적이고 사실 위주로 세련되게 답변하십시오.\n"
            f"추측이나 왜곡된 사실(Hallucination)은 엄격히 거부하며, 중립적이고 다정한 한국어로 500자 내외로 품격 있게 작성하십시오."
        )
        
        rag_prompt = (
            f"사용자 질문: '{text}'\n\n"
            f"[실시간 검색된 `{search_kw}` 관련 뉴스 기사 컨텍스트]\n"
            f"{context_str}\n"
            "위 컨텍스트를 활용하여 사용자가 만족할 수 있는 세련되고 명쾌한 요약 보고를 작성해 주십시오."
        )

        # 요약 생성 위임
        ai_response = await asyncio.to_thread(call_ollama, rag_prompt, system_prompt)
        
        if temp_msg:
            try:
                await temp_msg.delete()
            except Exception:
                pass

        if not ai_response:
            # Fallback
            fallback_msg = (
                f"🔌 *[AI 분석 지연 안내]*\n"
                f"`{search_kw}` 관련 뉴스는 성공적으로 검색되었으나 로컬 AI 요약 엔진이 일시적인 대기 상태입니다.\n\n"
                f"수집된 최신 뉴스 제목 목록입니다:\n" + 
                "\n".join([f"• {n['title']} ({n['publisher']})" for n in news_list])
            )
            msg = await update.message.reply_text(fallback_msg, parse_mode="Markdown")
            await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(update.message.chat_id))
        else:
            msg = await update.message.reply_text(ai_response, parse_mode="Markdown")
            await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(update.message.chat_id))
            
        return

    # 3. 만약 뉴스 검색이 아니라면 기존 다정한 일상 잡담 대화 (R6 흐름) 진행
    # 사용자 질문(발화) 로깅
    await log_chat_message(sender="user", message_text=text, session_id=str(update.message.chat_id))
    
    # 봇이 입력 중(typing...) 상태를 화면에 실시간 노출하여 UX 편의 극대화
    try:
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action="typing")
    except Exception as chat_action_err:
        print(f"[!] Chat Action 발송 실패: {chat_action_err}")
        
    system_prompt = (
        "당신은 로컬 Obsidian LLM Wiki를 보좌하는 지능형 비서 에이전트 'Antigravity 비서'입니다.\n"
        "사용자의 물음에 다정하고, 프로페셔널하며, 지적이고 예의바르게 한국어로 답변해주세요.\n"
        "너무 딱딱한 로봇 같은 서술형식 대신 자연스럽고 친근한 비서 톤의 구어체로 짧고 명료하게 소통하십시오."
    )
    
    # 비동기 이벤트 루프를 블로킹하지 않고 별도 동기 스레드 풀에 로컬 Ollama 호출 위임
    ai_response = await asyncio.to_thread(call_ollama, text, system_prompt)
    
    if not ai_response:
        # Ollama 오프라인/연결 실패 시 세련된 가이드라인 폴백 제공
        fallback_msg = (
            "🔌 *[AI 지능형 비서 안내]*\n"
            "현재 로컬 AI 엔진(Ollama)이 대기 모드이거나 오프라인 상태입니다.\n"
            "자유로운 자연어 대화를 원하시면 컴퓨터의 Ollama 서비스를 실행해 주십시오.\n\n"
            "임시로 아래 단축 명령어 목록을 통해 금융 위키 지식을 조회하실 수 있습니다."
        )
        msg = await update.message.reply_text(fallback_msg, parse_mode="Markdown")
        await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(update.message.chat_id))
        
        # 사용자 중복 로깅 없이 도움말 템플릿만 봇 응답으로 추가 전송 및 저장
        msg_help = await _send_help_template(update, context)
        await log_chat_message(sender="bot", message_text=msg_help.text or "", session_id=str(update.message.chat_id))
    else:
        msg = await update.message.reply_text(ai_response, parse_mode="Markdown")
        await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(update.message.chat_id))

# --- 12시간 백그라운드 자동 스케줄러 태스크 ---

async def scheduled_update_loop():
    """1시간 주기 [대폭 축소 가동] 자동 수집/분석 백그라운드 태스크"""
    global is_updating
    
    # [R11 극소화 조율] 최초 기동 시 즉시 웅장하게 돌기 위해 1분(60초)만 대기하고 정기 파이프라인 작동
    await asyncio.sleep(60)
    
    while True:
        print("[*] [스케줄러] 백그라운드 정기 수집/분석 에이전트 릴레이 스케줄러 시작")
        if not is_updating:
            is_updating = True
            try:
                print("[*] [스케줄러] ChiefAgent 릴레이 백그라운드 위임 실행 중...")
                agent = ChiefAgent()
                await asyncio.to_thread(agent.run_relay)
                
                print("[*] [스케줄러] send_briefing_notification() 텔레그램 푸시 발송 중...")
                await send_briefing_notification()
            except Exception as e:
                print(f"[!] [스케줄러 에러] 백그라운드 자동 실행 실패: {e}")
            finally:
                is_updating = False
        else:
            print("[*] [스케줄러] 다른 릴레이 파이프라인이 이미 실행 중이므로 이번 스케줄 주기는 건너뜁니다.")
            
        # 12시간 대기 ➡️ 1시간 (3600초) 대폭 축소! AI들 끊임없이 가동!
        await asyncio.sleep(3600)

# --- [R12 신설] 공인 IP 변경 감지 및 Upbit API 재등록 알림 ---

IP_CONFIG_PATH = ROOT_DIR / "_company" / "ip_config.json"
IP_CHECK_URLS = [
    "https://api.ipify.org",
    "https://api4.my-ip.io/ip",
    "https://checkip.amazonaws.com",
]

def _get_current_public_ip() -> str:
    """공인 IP를 외부 API 3종 중 하나로 조회합니다. 실패 시 빈 문자열 반환."""
    headers = {"User-Agent": "Mozilla/5.0"}
    for url in IP_CHECK_URLS:
        try:
            res = requests.get(url, headers=headers, timeout=6)
            if res.status_code == 200:
                ip = res.text.strip()
                if ip and len(ip) <= 45:   # IPv4/IPv6 길이 범위
                    return ip
        except Exception:
            continue
    return ""

def _get_registered_ip() -> str:
    """ip_config.json 에서 현재 등록된 IP를 읽습니다."""
    try:
        if IP_CONFIG_PATH.exists():
            data = json.loads(IP_CONFIG_PATH.read_text(encoding="utf-8"))
            return data.get("registered_ip", "")
    except Exception:
        pass
    return ""

def _save_registered_ip(new_ip: str):
    """ip_config.json 의 registered_ip 를 새 IP로 업데이트합니다."""
    try:
        data = {}
        if IP_CONFIG_PATH.exists():
            data = json.loads(IP_CONFIG_PATH.read_text(encoding="utf-8"))
        data["registered_ip"] = new_ip
        data["registered_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        IP_CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[!] ip_config.json 저장 실패: {e}")

async def ip_monitor_loop():
    """
    30분 주기로 공인 IP를 확인하여, ip_config.json 의 등록 IP와 달라졌을 경우
    텔레그램으로 즉시 경보를 발송합니다. (Upbit API 재등록 안내 포함)
    """
    # 봇 기동 후 2분 대기 (다른 루프 안정화 우선)
    await asyncio.sleep(120)
    print("[*] [IP 모니터] 공인 IP 변경 감지 시스템 가동.")

    while True:
        try:
            current_ip = await asyncio.to_thread(_get_current_public_ip)
            registered_ip = _get_registered_ip()

            if current_ip and registered_ip and current_ip != registered_ip:
                print(f"[!] [IP 모니터] 공인 IP 변경 감지: {registered_ip} → {current_ip}")

                alert_msg = (
                    f"🌐 *[공인 IP 변경 감지 경보]*\n\n"
                    f"컴퓨터의 공인 IP가 바뀌었습니다!\n"
                    f"Upbit API가 차단될 수 있으니 즉시 재등록해 주세요.\n\n"
                    f"• 이전 IP: `{registered_ip}`\n"
                    f"• *새 IP: `{current_ip}`* ← 이걸 등록하세요\n\n"
                    f"📋 *재등록 순서:*\n"
                    f"1. Upbit 로그인 → My → Open API 관리\n"
                    f"2. 기존 Key 삭제 후 재발급 (또는 변경 버튼)\n"
                    f"3. IP 주소 칸에 `{current_ip}` 입력\n"
                    f"4. 자산조회 체크 → 발급\n\n"
                    f"_등록 완료 후 봇에 '업데이트' 또는 /update 를 보내주세요._"
                )

                try:
                    app_notif = Application.builder().token(BOT_TOKEN).build()
                    await app_notif.bot.send_message(
                        chat_id=CHAT_ID,
                        text=alert_msg,
                        parse_mode="Markdown"
                    )
                    await log_chat_message(sender="bot", message_text=alert_msg, session_id=str(CHAT_ID))
                    # ip_config.json 에 새 IP 기록 (다음 루프에서 중복 알림 방지)
                    await asyncio.to_thread(_save_registered_ip, current_ip)
                    print(f"[+] [IP 모니터] IP 변경 경보 발송 완료. 새 IP {current_ip} 저장.")
                except Exception as send_err:
                    print(f"[!] [IP 모니터] 경보 발송 실패: {send_err}")

            elif current_ip:
                print(f"[*] [IP 모니터] 공인 IP 정상: {current_ip}")

        except Exception as e:
            print(f"[!] [IP 모니터] 루프 오류: {e}")

        # 30분마다 체크
        await asyncio.sleep(1800)


# --- [R11 신설] 1시간 주기 능동형 프로액티브 모니터링 루프 ---

async def proactive_monitoring_loop():
    """
    5분 주기 [대폭 축소 가동] 금융 데이터를 선행 수집하여, 이전 캐시값 대비 급격한 변동이 포착되면
    텔레그램으로 즉시 알림 카드를 발송합니다.
    """
    global last_proactive_alert_time
    
    # 봇 구동 초기 안정화 대기 (10초)
    await asyncio.sleep(10)
    print("[*] [프로액티브 모니터] 능동형 변동성 감시 시스템 작동 개시.")
    
    while True:
        # 현재 쿨다운 확인
        now = datetime.now()
        in_cooldown = False
        if last_proactive_alert_time:
            elapsed_cooldown = (now - last_proactive_alert_time).total_seconds() / 3600.0
            if elapsed_cooldown < PROACTIVE_COOLDOWN_HOURS:
                in_cooldown = True
        
        if not in_cooldown:
            try:
                print("[*] [프로액티브 모니터] 5분 주기 실시간 지표 변동 감시 가동 중...")
                db_agent = DBManager()
                db_res = await asyncio.to_thread(db_agent.collect)
                
                if db_res.success and db_res.payload:
                    financial_data = db_res.payload
                    btc_change = abs(financial_data.get("btc_krw_change", 0.0))
                    # 환율 변동성 (이전 캐시 대비)
                    exchange_rate = financial_data.get("exchange_rate", 0.0)
                    
                    # 이전 캐시 금융 지표와 비교
                    prev_rate = 0.0
                    if FINANCIAL_DATA_PATH.exists():
                        try:
                            with open(FINANCIAL_DATA_PATH, "r", encoding="utf-8") as f:
                                prev_data = json.load(f)
                                prev_rate = prev_data.get("exchange_rate", 0.0)
                        except Exception:
                            pass
                    
                    fx_change_pct = 0.0
                    if prev_rate > 0:
                        fx_change_pct = abs((exchange_rate - prev_rate) / prev_rate) * 100.0
                        
                    # 변동률 조건 만족 여부 확인
                    trigger_btc = btc_change >= PROACTIVE_BTC_CHANGE_THRESHOLD
                    trigger_fx = fx_change_pct >= PROACTIVE_FX_CHANGE_THRESHOLD
                    
                    if trigger_btc or trigger_fx:
                        last_proactive_alert_time = now
                        
                        reason_list = []
                        if trigger_btc:
                            reason_list.append(f"🪙 비트코인 변동률 ({financial_data.get('btc_krw_change', 0.0):+.2f}%)이 임계값({PROACTIVE_BTC_CHANGE_THRESHOLD}%)을 초과")
                        if trigger_fx:
                            reason_list.append(f"💵 원/달러 환율 변동률 ({fx_change_pct:+.2f}%)이 임계값({PROACTIVE_FX_CHANGE_THRESHOLD}%)을 초과")
                            
                        reasons = "\n".join(reason_list)
                        
                        kimp_sign = "+" if financial_data.get("kimchi_premium", 0.0) > 0 else ""
                        btc_sign = "+" if financial_data.get("btc_krw_change", 0.0) > 0 else ""
                        
                        alert_message = f"""🚨 *[Antigravity 능동 모니터링 변동성 경보]*
                        
시장 지표 of 이상 급변동이 감지되어 비서가 긴급히 안내드립니다!

{reasons}

📊 *[오늘의 실시간 금융/크립토 주요 지표]*
• 🪙 *Bitcoin (Upbit)*: `{financial_data.get('btc_krw', 0):,.0f}원` ({btc_sign}{financial_data.get('btc_krw_change', 0.0):.2f}%)
• ⚡ *김치 프리미엄 (Premium)*: `{kimp_sign}{financial_data.get('kimchi_premium', 0.0):.2f}%`
• 💵 *원/달러 환율 (USD/KRW)*: `{exchange_rate:,.2f}원`
• 🕒 *지표 갱신시*: `{financial_data.get('updated_at', '')}`

💡 아래 버튼을 눌러 즉시 3대 경제/크립토 에이전트를 동원한 종합 분석을 지시하거나 본 경보를 확인 처리 하실 수 있습니다.
"""
                        
                        keyboard = [
                            [
                                InlineKeyboardButton("🔍 지금 전체 분석 가동", callback_data="proactive_run"),
                                InlineKeyboardButton("✅ 확인했어", callback_data="proactive_dismiss")
                            ]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        # 메신저 봇 생성 후 직접 발송
                        app = Application.builder().token(BOT_TOKEN).build()
                        await app.bot.send_message(
                            chat_id=CHAT_ID,
                            text=alert_message,
                            reply_markup=reply_markup,
                            parse_mode="Markdown"
                        )
                        print(f"[+] [프로액티브 모니터] 능동 경보 발송 완료: BTC {btc_change:.2f}%, FX {fx_change_pct:.2f}%")
                        await log_chat_message(sender="bot", message_text=alert_message, session_id=str(CHAT_ID))
                        
            except Exception as e:
                print(f"[!] [프로액티브 모니터] 변동 감시 중 오류 발생: {e}")
                
        # 1시간 대기 ➡️ 5분 (300초) 대폭 단축!
        await asyncio.sleep(300)

# --- 봇 대화형 폴링 기동 함수 ---

def main():
    # SQLite 데이터베이스 생성/초기화 보증
    init_chat_db()
    
    if not is_token_valid():
        print("\n[!] =========================================")
        print("[!] 텔레그램 봇 토큰 및 Chat ID가 정의되지 않았습니다.")
        print("[!] .env 파일에 실제 텔레그램 봇 토큰 정보를 기입해주시면 대화형 명령어 기능이 활성화됩니다.")
        print("[!] 현재는 로컬 위키 요약 보고서 파일 작성이 완벽하게 검증된 단계입니다.")
        print("[!] =========================================\n")
        return
        
    print("[*] 텔레그램 대화형 에이전트 봇 구동 시작 (Polling 모드)...")
    
    async def post_init(application: Application):
        asyncio.create_task(scheduled_update_loop())
        asyncio.create_task(proactive_monitoring_loop())  # [R11]
        asyncio.create_task(ip_monitor_loop())            # [R12 IP 변경 감지]
        print("[+] 백그라운드 스케줄러 / 능동 모니터링 / IP 변경 감지 등록 완료.")
        try:
            await application.bot.send_message(
                chat_id=CHAT_ID,
                text="🤖 *텔레그램 봇이 성공적으로 재시작되었습니다!*",
                parse_mode="Markdown"
            )
            print("[+] 텔레그램 재시작 알림 메시지 발송 완료.")
        except Exception as e:
            print(f"[!] 텔레그램 재시작 알림 메시지 발송 실패: {e}")

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CallbackQueryHandler(button_callback_handler))
    app.add_handler(CommandHandler("start",   start_command))
    app.add_handler(CommandHandler("help",    start_command))
    app.add_handler(CommandHandler("update",  update_command))
    app.add_handler(CommandHandler("bitcoin", bitcoin_command))
    app.add_handler(CommandHandler("fed",     fed_command))
    app.add_handler(CommandHandler("korea",   korea_command))
    app.add_handler(CommandHandler("log",     log_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))
    print("[+] 봇 준비 완료. 텔레그램에서 명령어를 보내 대화하세요.")
    app.run_polling()

if __name__ == "__main__":
    init_chat_db()
    if len(sys.argv) > 1 and sys.argv[1] == "--send-briefing":
        asyncio.run(send_briefing_notification())
    else:
        main()
