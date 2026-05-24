← [[Development_Hub|개발 마스터 대시보드]]

# 텔레그램 대화로그 SQLite 저장 기능 구현 계획서 (R1)

본 계획서는 사용자의 **"텔레그램 대화 로그 SQLite 저장 기능 탑재"** 요구사항에 의거하여, 가상 기업 OS 환경 내에 텔레그램 채팅 대화 로그를 실시간으로 영속화하여 적재하는 로컬 SQLite 데이터베이스 인프라 구축 및 연동 설계를 명세하는 단독 구현 계획서(R1)입니다.

이전 R0 설계본에 대한 검토 의견서(R0 검토 리포트)의 지적 사항인 **즉시 수정 버그 2건, 설계 결함 3건, 명세 누락 3건**을 완벽하게 보완 및 반영하여 실물 반영이 가능한 프로덕션 수준의 사양을 명세하였습니다.

---

## 1. 피드백 수용 및 신규 설계 조치 명세 (R1 보완)

| 번호 | 검토 의견서 지적 사항 (R0) | 원인 및 기술 분석 | R1 보완 설계 및 조치 사항 (해결책) |
| :---: | :--- | :--- | :--- |
| **1** | **비동기 루프 블로킹 동기 SQLite I/O** | `sqlite3` 동기 함수 호출이 비동기 이벤트 루프(`asyncio`) 전체를 멈추는 리스크. | `log_chat_message` 자체를 `async` 함수로 설계하고, 내부 DB 파일 I/O 구역을 **`asyncio.to_thread`를 사용하여 별도 스레드 풀에 위임 처리**하도록 변경. |
| **2** | **`message_text NOT NULL` 제약 실패** | 스티커, 사진, 파일 등 텍스트가 없는 텔레그램 메시지 수신 시 `text`가 `None`이 되어 SQLite 인서트가 깨지는 현상. | 테이블 스키마에서 **`message_text TEXT` (NULL 허용)**으로 변경하며, 함수 내부에서 **`message_text = message_text or ""`** 방어 코드를 적용함. |
| **3** | **`init_chat_db()` 호출 위치 미명세** | 봇 기동 라이프사이클 내에서 DB 초기화 호출 지점이 명확하지 않음. | `telegram_bot.py` 의 **`main()` 진입부(토큰 검증 직후)에서 즉시 동기식으로 호출**되도록 기동 흐름을 명문화함. |
| **4** | **송신 래퍼 마이그레이션 누락 및 콜백 로깅 부재** | `reply_and_log` 적용 시 `button_callback_handler` 등 `edit_message_text` 호출지 로깅 누락 및 9개소 마이그레이션 누락. | 대안 래퍼를 전수 조사하여 **기존 호출부 반환 Message 객체를 직접 가로채어 `log_chat_message`를 호출하는 마이그레이션 계획(9개소)을 확정 명세**함. |
| **5** | **Race Condition 보호 불완전** | 멀티에이전트 및 봇 데몬 멀티스레드 혼합 환경에서 `SQLITE_BUSY` 락 충돌 리스크. | SQLite의 **WAL(Write-Ahead Logging) 모드를 강제 활성화**하고, 파이썬 전역 **`threading.Lock` 보호막** 및 **`timeout=30.0`** 옵션을 적용함. |
| **6** | **`created_at` 타임존 미명세** | 서버 가동 환경에 따라 저장되는 시간이 달라져 한국 표준시(KST) 대조 시 시간 불일치 가능성. | 시스템 시간 설정을 배제하고 **`timezone(timedelta(hours=9))`를 활용한 KST(한국 표준시, UTC+9)**로 강제 변환 포맷 저장 명세. |
| **7** | **`session_id` 기본값 "default" 위험성** | `chat_id` 누락 시 서로 다른 유저의 대화 이력이 섞이는 리스크. | **기본값 `"default"`를 제거하고 필수 인자(str)로 강제 지정**하며, 콜백 쿼리 시 `query.message.chat_id` 바인딩을 명확히 명세함. |
| **8** | **로그 저장 실패 시 알림 수단 전무** | DB 쓰기 오류 시 단순 `print` 출력 후 소멸하여 복구가 불가능한 결함. | 전역 logging을 활용해 **별도 에러 로그 파일(`_company/logs/chat_error.log`)에 스택을 기록**하고, 봇이 동작 중인 경우 **운영자 텔레그램 채널로 즉시 에러 푸시 메시지를 쏘는 안전망 구축**. |

---

## 2. 텔레그램 대화 로그 SQLite 데이터베이스 설계 (R1 개정)

### 1) DB 물리 경로
- **`ROOT_DIR / "_company" / "telegram_chat.db"`**
- OS의 최고 신뢰 통제 계층 하위에 격리 개설하여 외부 접근을 제한합니다.

### 2) 테이블 명 및 스키마 명세 (`telegram_chat_logs`)
| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| :--- | :---: | :---: | :--- |
| **`id`** | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | 고유 식별 일련번호 (PK) |
| **`session_id`** | `TEXT` | `NOT NULL` | 텔레그램 사용자 고유 `chat_id` (세션 식별자) |
| **`sender`** | `TEXT` | `NOT NULL` | 발신 주체 (`user` 또는 `bot`) |
| **`message_text`** | `TEXT` | `NULL` | 송수신된 실제 채팅 대화 내용 전문 (텍스트 미존재 시 NULL/빈값 허용) |
| **`created_at`** | `TEXT` | `NOT NULL` | 대화가 일어난 시각 (KST 한국 표준시 기준 포맷: `YYYY-MM-DD HH:MM:SS`) |

---

## 3. SQLite 연동 및 텔레그램 봇 삽입 소스 코드 명세 (R1 개정)

`telegram_bot.py`에 구현될 스레드 안전 및 비동기 이벤트 루프 친화적인 SQLite 모듈 코드입니다.

### 1) 전역 객체 및 초기화 / 저장 함수
```python
import sqlite3
import logging
import threading
from datetime import datetime, timezone, timedelta
from agents.shared.config import ROOT_DIR

# 멀티스레드/멀티세션 환경 보호를 위한 전역 락 설정
db_lock = threading.Lock()

# 텔레그램 에러 로그 기록 전용 로거 설정
chat_error_logger = logging.getLogger("chat_error")
chat_error_logger.setLevel(logging.ERROR)
chat_log_dir = ROOT_DIR / "_company" / "logs"
chat_log_dir.mkdir(parents=True, exist_ok=True)
file_handler = logging.FileHandler(chat_log_dir / "chat_error.log", encoding="utf-8")
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
chat_error_logger.addHandler(file_handler)

def init_chat_db():
    """telegram_chat.db 초기화 (WAL 모드 활성화 및 timeout 강화)"""
    db_path = ROOT_DIR / "_company" / "telegram_chat.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    with db_lock:
        try:
            # 커넥션 락 방지를 위한 timeout=30초 설정
            conn = sqlite3.connect(db_path, timeout=30.0)
            cursor = conn.cursor()
            # 1. 텔레그램 대화 로그 테이블 생성 (message_text NULL 허용)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telegram_chat_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    message_text TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            # 2. 동시 성능 극대화를 위한 WAL 모드 활성화 
            cursor.execute("PRAGMA journal_mode=WAL;")
            conn.commit()
            conn.close()
            print("[+] 텔레그램 로컬 SQLite 대화 데이터베이스 초기화 완료 (WAL 모드 가동).")
        except Exception as e:
            chat_error_logger.error(f"SQLite DB 초기화 중 오류 발생: {e}", exc_info=True)
            print(f"[!] SQLite DB 초기화 중 치명적 오류 발생: {e}")

async def log_chat_message(sender: str, message_text: str, session_id: str):
    """비동기 스레드 풀 위임을 통해 이벤트 루프 블로킹 없이 원자적/안전하게 SQLite 적재"""
    db_path = ROOT_DIR / "_company" / "telegram_chat.db"
    
    # 텍스트 없는 메시지 방어 처리
    safe_text = message_text or ""
    
    # 한국 표준시(KST, UTC+9)로 강제 시간대 바인딩
    kst = timezone(timedelta(hours=9))
    now_str = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")

    # 텔레그램 봇을 통한 비상 통보 메커니즘을 위한 클로저 에러 헬퍼
    def _send_emergency_notification(err_msg: str):
        # 봇 토큰 및 챗 아이디가 유효할 경우 텔레그램으로 SQLite 에러 다이렉트 전송
        try:
            from telegram import Bot
            from agents.shared.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                emergency_bot = Bot(token=TELEGRAM_BOT_TOKEN)
                # 비동기 발송이 아닌 단순 통보용이므로 asyncio.run_coroutine_threadsafe 등 활용
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(emergency_bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=f"⚠️ *[SQLite DB 경보]* 대화 로그 적재 실패!\n에러: `{err_msg}`",
                        parse_mode="Markdown"
                    ))
        except Exception as notify_err:
            chat_error_logger.error(f"비상 에러 통보 발송 실패: {notify_err}")

    # 동기 SQLite I/O 동작부
    def _sync_insert():
        with db_lock:
            try:
                conn = sqlite3.connect(db_path, timeout=30.0)
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
                print(f"[!] SQLite 대화 로그 저장 실패 (발신자: {sender}): {e}")

    # asyncio.to_thread를 호출하여 이벤트 루프 전체 멈춤 차단
    await asyncio.to_thread(_sync_insert)
```

---

## 4. 라이프사이클 호출 및 기존 핸들러 마이그레이션 명세 (R1 개정)

### 1) DB 초기화 (`init_chat_db`) 호출 시점
`telegram_bot.py` 의 `main()` 함수 최상단 진입 지점에서 동기식으로 최초 실행하여 테이블의 영속 안전성을 담보합니다.
```python
def main():
    if not is_token_valid():
        ...
        return
        
    # [R1 신규] 토큰 검증 통과 직후 SQLite DB 기동 및 테이블 검증
    init_chat_db()
    
    print("[*] 텔레그램 대화형 에이전트 봇 구동 시작 (Polling 모드)...")
    ...
```

### 2) 핸들러 내 메시지 수발신 로깅 인터셉트 패치 범위 (9대 마이그레이션)

#### ① 사용자 발신(User Input) 기록 지점
* **`text_message_handler` 최상단 진입 시**:
  ```python
  async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
      text = update.message.text.strip() if update.message.text else ""
      # [R1 패치] 유저 입력 비동기 SQLite 영속화 (이벤트 루기 블로킹 완치)
      await log_chat_message(sender="user", message_text=text, session_id=update.message.chat_id)
      ...
  ```

#### ② 봇 송신(Bot Output) 기록 지점 (전체 9개 핸들러 대상)
기존 `update.message.reply_text` 또는 `query.edit_message_text`를 통해 생성된 반환 Message 객체를 직접 캡처하여 비동기로 로깅합니다.

1. **`start_command` (L146)**:
   ```python
   msg = await update.message.reply_text(help_text, parse_mode="Markdown")
   await log_chat_message(sender="bot", message_text=msg.text, session_id=update.message.chat_id)
   ```
2. **`bitcoin_command` (L151)**:
   ```python
   msg = await update.message.reply_text(f"🪙 *[Bitcoin] 가상자산 지식 누적 분석*\n\n{report}")
   await log_chat_message(sender="bot", message_text=msg.text, session_id=update.message.chat_id)
   ```
3. **`fed_command` (L156)**:
   ```python
   msg = await update.message.reply_text(f"🌍 *[US-Fed] 글로벌 거시경제 지식 누적 분석*\n\n{report}")
   await log_chat_message(sender="bot", message_text=msg.text, session_id=update.message.chat_id)
   ```
4. **`korea_command` (L161)**:
   ```python
   msg = await update.message.reply_text(f"🇰🇷 *[Korea-Economy] 국내 경제 지식 누적 분석*\n\n{report}")
   await log_chat_message(sender="bot", message_text=msg.text, session_id=update.message.chat_id)
   ```
5. **`log_command` (L183, L185)**:
   * 로그 부재 시:
     ```python
     msg = await update.message.reply_text("📂 에이전트 활동 로그가 아직 없습니다.")
     await log_chat_message(sender="bot", message_text=msg.text, session_id=update.message.chat_id)
     ```
   * 정상 로그 반환 시:
     ```python
     msg = await update.message.reply_text(log_text)
     await log_chat_message(sender="bot", message_text=msg.text, session_id=update.message.chat_id)
     ```
6. **`update_command` (L191, L204)**:
   * 중복 가동 대기 안내:
     ```python
     msg = await update.message.reply_text("🔄 현재 AI 비서 패키지가 다른 뉴스들을 열심히 분석하는 중입니다...")
     await log_chat_message(sender="bot", message_text=msg.text, session_id=update.message.chat_id)
     ```
   * 릴레이 완료 브리핑 및 승인 대기 카드:
     ```python
     msg_briefing = await update.message.reply_text(briefing_message, parse_mode="Markdown")
     await log_chat_message(sender="bot", message_text=msg_briefing.text, session_id=update.message.chat_id)
     # 승인 대기 카드 발송 지점:
     msg_card = await update.message.reply_text(text=..., reply_markup=reply_markup, parse_mode="Markdown")
     await log_chat_message(sender="bot", message_text=msg_card.text, session_id=update.message.chat_id)
     ```
7. **`button_callback_handler` (컨펌 버튼 승인/반려 피드백 전체 L273, L276, L279, L282, L288, L292, L296)**:
   * 텔레그램 컨펌 클릭에 의한 메시지 변경(`query.edit_message_text`) 완료 후, 반환되는 `Message` 객체의 실물 텍스트를 SQLite에 기록합니다:
     ```python
     # 예시: 승인 성공 지점
     msg = await query.edit_message_text(text=..., parse_mode="Markdown")
     # CallbackQuery에서는 query.message.chat_id 또는 query.message.chat.id를 직접 바인딩
     await log_chat_message(sender="bot", message_text=msg.text, session_id=query.message.chat_id)
     ```

---

## 5. 구현 검증 계획 (R1 개정)

### 1) 자동화 검증
- SQLite WAL 모드가 정상 활성화되어 동시 락 충돌 현상을 막을 수 있는지 확인하는 모의 스레드 인서트 테스트를 수행합니다.
- 텍스트가 `None`인 비텍스트형 텔레그램 메시지 구조를 객체로 목킹(Mocking)하여 `log_chat_message` 전송 시 SQLite 스키마 위반 예외 없이 정상 적재가 되는지 확인합니다.

### 2) 수동 검증 시나리오
- 텔레그램에 접속하여 `/bitcoin` 커맨드 또는 스티커/사진을 발송합니다.
- DB 브라우저 또는 CLI 터미널 스크립트(`sqlite3 _company/telegram_chat.db "SELECT * FROM telegram_chat_logs"`)를 가동하여, 사용자 및 봇의 메시지가 한국 표준시(KST) 기준으로 정확하게 적재되는지 대조합니다.
- 로컬 `_company/logs/chat_error.log` 파일의 무결성 및 기록 여부를 체크합니다.

---

## 6. 사용자 승인 대기

> [!IMPORTANT]
> - 본 **텔레그램 대화로그 SQLite 저장 기능 구현 계획서 (R1)**는 R0 검토 리포트의 기술적 피드백(비동기 차단 방지, 스키마 유연성, 전역 락 동시성 처리, 한국 시간대 바인딩, 콜백 로깅 누락 마이그레이션 등)을 완벽하게 수렴하여 개정된 고품질 설계서입니다.
> - 사용자님께서 본 설계를 최종적으로 검토해 주시고 **"승인"**, **"진행"** 또는 **"시작"**을 전송해주시는 시점에 즉각 실물 파이썬 파일 패치 수술을 안전하게 시작하도록 하겠습니다!
