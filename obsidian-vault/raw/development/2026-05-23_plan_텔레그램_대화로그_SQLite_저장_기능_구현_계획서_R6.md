← [[Development_Hub|개발 마스터 대시보드]]

# 텔레그램 LLM 지능형 일상대화 기능 연동 계획서 (R6)

본 계획서는 사용자의 **"비서 에이전트와 지능적이고 자유로운 일반 대화 기능 탑재"** 요구사항 및 승인에 의거하여, 텔레그램 봇에 로컬 AI 엔진(Ollama / `gemma4:e4b`)을 유기적으로 연동하여 저와 대화하는 것처럼 다정하고 스마트하게 일상 대화 및 잡담을 나눌 수 있는 지능형 챗 모듈 연동 패치를 명세하는 단독 구현 계획서(R6)입니다.

기존 특정 금융/뉴스 키워드에서 이탈할 경우 기계적으로 도움말 리스트만 발송하던 밋밋한 자연어 핸들러의 구조를 정교하게 리팩토링하고, 사용자 입력이 중복 적재되거나 꼬이지 않도록 이중 로깅 차단 설계를 유지하면서도 시각적인 피드백(typing...)과 비동기 논블로킹 스레드 위임을 결합하여 안정적이고 세련된 사용자 경험을 실현하도록 설계했습니다.

---

## 1. 지능형 자유대화 핵심 보완 및 연동 설계 명세 (R6)

| 번호 | 보완 설계 및 구현 피처 | 상세 동작 로직 및 기술 설계 | 비고 / 세이프망 |
| :---: | :--- | :--- | :--- |
| **1** | **Ollama AI 엔진 API 연동 및 비동기 스레드 위임** | 키워드 분기에서 제외된 자유 자연어 유입 시, 동기 통신 차단 및 비동기 이벤트 루프 보호를 위해 `asyncio.to_thread`를 사용하여 로컬 Ollama API 호출(`call_ollama`)을 스레드 풀에 위임함. | `agents.shared.ollama_client` 임포트 |
| **2** | **실시간 시각적 상태 피드백 (typing챗 액션)** | Ollama 답변 생성이 일어나는 대기 시간(약 1~5초) 동안 사용자가 먹통 현상으로 오인하지 않도록 텔레그램 채널 상에 **`💬 비서가 입력하는 중...`** 애니메이션 피드백을 실시간으로 발송함. | `context.bot.send_chat_action` 활용 |
| **3** | **도움말 전송 구조 리팩토링 및 이중 로깅 원천 차단** | `start_command`와 Ollama 미가동 폴백 분기 모두가 중복/꼬임 로깅 없이 동일한 템플릿을 발송하도록, 순수 발송 헬퍼 `_send_help_template()`을 신설하여 로깅 무결성을 보호함. | 유저 발화 중복 기록 방지 |
| **4** | **세련된 에러 가드 및 AI 오프라인 폴백 수립** | 사용자의 컴퓨터에서 로컬 Ollama 서비스가 꺼져 있는 오프라인 상태일 경우, 크래시 없이 "AI 엔진이 대기 중입니다"라는 지능형 세련된 안내 문구 및 도움말 가이드를 발송하고 SQLite에 1회만 단독 로깅함. | 데이터 무결성 보장 |

---

## 2. 텔레그램 봇 지능형 일상대화 패치 범위 (R6)

### 1) [MODIFY] [telegram_bot.py](file:///C:/Users/jmj/Desktop/안티그래비티/new/telegram_bot.py) - 임포트 및 유틸 헬퍼 추가
* **Before (L14 ~ L25)**:
```python
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
```

* **After**:
```python
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
from agents.shared.ollama_client import call_ollama  # [R6 추가] 지능형 일상대화용 Ollama API 임포트
```

---

### 2) [MODIFY] [telegram_bot.py](file:///C:/Users/jmj/Desktop/안티그래비티/new/telegram_bot.py) - `start_command` 리팩토링 및 헬퍼 신설
* **Before (L133 ~ L147)**:
```python
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start 및 /help 명령어 수신 시 지원 목록 반환"""
    # 사용자 입력 로깅 (하드코딩 배제 및 실제 입력 텍스트 캡처)
    actual_input = update.message.text or "/start"
    await log_chat_message(sender="user", message_text=actual_input, session_id=str(update.message.chat_id))

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
    msg = await update.message.reply_text(help_text, parse_mode="Markdown")
    # 봇 응답 로깅 (msg.text None 방어 가드 적용)
    await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(update.message.chat_id))
```

* **After**:
```python
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
```

---

### 3) [MODIFY] [telegram_bot.py](file:///C:/Users/jmj/Desktop/안티그래비티/new/telegram_bot.py) - `text_message_handler` 지능형 자유대화 이식
* **Before (L336 ~ L353)**:
```python
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """사용자가 슬래시 없이 한글로 텍스트 메시지를 보냈을 때 지능적으로 판단하여 위키를 전송"""
    text = update.message.text.strip() if update.message.text else ""
    
    # [R5 해결 - 이중 로깅 차단 방안 A 적용]
    # text_message_handler 내부의 로깅을 전면 제거하여 하위 커맨드 핸들러의 1회 로깅과 충돌/중복을 완전히 예방합니다.

    # 실시간 업데이트 제어용 한글 자연어 키워드 매칭
    if any(kw in text for kw in ["업데이트", "가져와", "수집", "분석", "동기화", "뉴스"]):
        await update_command(update, context)
    elif "비트코인" in text or "bitcoin" in text.lower():
        await bitcoin_command(update, context)
    elif "세계경제" in text or "fed" in text.lower() or "연준" in text:
        await fed_command(update, context)
    elif "국내경제" in text or "korea" in text.lower() or "한국경제" in text:
        await korea_command(update, context)
    elif "로그" in text or "log" in text.lower() or "기록" in text:
        await log_command(update, context)
    else:
        await start_command(update, context)
```

* **After**:
```python
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """사용자가 슬래시 없이 한글로 텍스트 메시지를 보냈을 때 지능적으로 판단하여 위키 전송 혹은 LLM 기반 지능형 일상대화 수행"""
    text = update.message.text.strip() if update.message.text else ""
    
    # [R5 해결 - 이중 로깅 차단 방안 A 적용]
    # text_message_handler 내부의 로깅을 전면 제거하여 하위 커맨드 핸들러의 1회 로깅과 충돌/중복을 완전히 예방합니다.

    # 1. 키워드 기반 위키 요약/제어 분기 매칭
    if any(kw in text for kw in ["업데이트", "가져와", "수집", "분석", "동기화", "뉴스"]):
        await update_command(update, context)
    elif "비트코인" in text or "bitcoin" in text.lower():
        await bitcoin_command(update, context)
    elif "세계경제" in text or "fed" in text.lower() or "연준" in text:
        await fed_command(update, context)
    elif "국내경제" in text or "korea" in text.lower() or "한국경제" in text:
        await korea_command(update, context)
    elif "로그" in text or "log" in text.lower() or "기록" in text:
        await log_command(update, context)
    elif text.startswith("/") or any(text.startswith(kw) for kw in ["도움말", "명령어", "메뉴", "시작"]):
        await start_command(update, context)
    else:
        # [R6 지능형 일상대화 피처 연동]
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
```

---

## 3. 구현 검증 계획 (R6)

### 1) 자동화 검증
- SQLite WAL 모드가 안정적으로 활성화되어 동시 락 충돌 현상을 막을 수 있는지 확인합니다.
- `call_ollama` 호출을 가상 목킹하여, Ollama 연동 성공 시 자연스러운 대화문이 반환되고 `telegram_chat_logs` 테이블에 중복 없이 정확히 2건(사용자 1건 + 봇 1건)으로 로깅되는지 검증합니다.
- Ollama 서버가 연결이 불가능한 상태일 때(오프라인 상태 모사), 폴백 알림 메시지와 명령어 리스트가 차례로 송출된 뒤 DB에 정상 적재되는지 검증합니다.

### 2) 수동 검증 시나리오
- 텔레그램을 기동하여 사용자가 "지금 뭐하고 있어?" 또는 "비서야 안녕?" 등의 일반적인 자유 대화를 발송합니다.
- 텔레그램 채팅창 상단에 `[💬 비서가 입력하는 중...]` 상태 액션이 생동감 있게 깜빡이는지 확인합니다.
- 봇이 사용자가 보낸 일반 대화 내용에 대해 다정하고 자연스러운 비서 톤의 한글 구어체 답변을 쏘는지 검증합니다.
- CLI 환경 터미널 스크립트(`sqlite3 _company/telegram_chat.db "SELECT * FROM telegram_chat_logs"`)를 가동하여 자유대화 입력 및 AI 응답 텍스트 전문이 깨짐 없이 정확하게 1건씩 단독 누적 적재되는지 대조합니다.

---

## 4. Known Unknowns (스스로 확신하지 못하는 미결 리스크 명시)

- **Known Unknowns**:
  1. Ollama의 로컬 로딩 상태(VRAM 부족 혹은 모델 최초 로드 지연)로 인해 최초 답변 생성 시간이 10초 이상 극도로 지연될 경우, python-telegram-bot의 내부 타임아웃 예외가 유발되어 메시지 전송이 누락되거나 대화로그가 불일치할 수 있는 네트워크 리스크. (향후 비동기 타임아웃 세이프 가드 보강 필요성 검토).
  2. 사용자의 연속적인 다중 텍스트 폭탄 입력 시, Ollama 비동기 스레드 풀 위임(`asyncio.to_thread`)이 병렬로 무수히 적체되면서 로컬 CPU/GPU 연산 자원이 오버플로우되거나 챗 로그 DB의 쓰기 순서가 뒤틀릴 수 있는 비상 동시성 리스크.

---

## 5. 사용자 승인 대기

> [!IMPORTANT]
> - 본 **텔레그램 LLM 지능형 일상대화 기능 연동 계획서 (R6)**는 사용자님이 요청하신 저와 대화하는 것처럼 다정하고 유연하게 잡담 및 소통할 수 있는 프리미엄 연동 설계서입니다.
> - 사용자님께서 이 정교하게 수립된 R6 지능형 일상대화 계획을 꼼꼼하게 확인해 주시고 **"승인"**, **"진행"** 또는 **"시작"** 등 승인 키워드를 주시면, 즉각 실물 패치 작업을 가동하여 비서를 지능형 AI 비서로 완벽하게 진화시키겠습니다!
