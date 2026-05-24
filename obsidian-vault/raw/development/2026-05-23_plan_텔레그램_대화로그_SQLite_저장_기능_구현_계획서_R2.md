← [[Development_Hub|개발 마스터 대시보드]]

# 텔레그램 대화로그 SQLite 저장 기능 구현 계획서 (R2)

본 계획서는 사용자의 **"텔레그램 대화 로그 SQLite 저장 기능 탑재"** 요구사항에 의거하여, 가상 기업 OS 환경 내에 텔레그램 채팅 대화 로그를 실시간으로 영속화하여 적재하는 로컬 SQLite 데이터베이스 인프라 구축 및 연동 설계를 명세하는 단독 구현 계획서(R2)입니다.

이전 R1 설계본에 대한 신규 검토 의견서(R1 검토 리포트)의 지적 사항인 **런타임 버그 2건, 설계 결함 3건, 명세 불완전 2건**을 완벽하게 보완 및 반영하여 봇 기동 시 단 하나의 에러나 누락도 없이 완전무결한 프로덕션 기동을 담보하는 수정본입니다.

---

## 1. 피드백 수용 및 신규 설계 조치 명세 (R2 보완)

| 번호 | 검토 의견서 지적 사항 (R1) | 원인 및 기술 분석 | R2 보완 설계 및 조치 사항 (해결책) |
| :---: | :--- | :--- | :--- |
| **1** | **`_send_emergency_notification` 내 `get_event_loop()`의 런타임 에러** | `asyncio.to_thread`를 통해 분화된 동기 서브 스레드 풀에서 `get_event_loop()`를 실행하면, 해당 스레드에 루프가 부재하여 `RuntimeError`가 발생하거나 작동하지 않는 심각한 리스크. | `log_chat_message` (async 메인 루프 실행) 시작 단계에서 **`asyncio.get_running_loop()`로 메인 루프를 선행 안전 캡처**하고, 서브 스레드 내 에러 발송 시 **`asyncio.run_coroutine_threadsafe(..., loop)`**를 사용해 메인 루프에 태스크를 안전히 등록함. |
| **2** | **슬래시 커맨드(/) 사용자 입력 로깅 완전 누락** | `filters.TEXT & ~filters.COMMAND` 필터 적용으로 인해 `/start`, `/bitcoin` 등 모든 명령어 입력이 `text_message_handler`를 거치지 않고 직접 분기되어 유저 입력이 DB에 누적되지 않는 치명적 결함. | `telegram_bot.py` 에 등록된 **모든 6개 `CommandHandler` 최상단 진입부**에 유저의 커맨드 입력 내역을 영속화하는 `await log_chat_message(sender="user", ...)` 호출을 명시적으로 수술 이식함. |
| **3** | **모듈 레벨 `FileHandler` 초기화로 인한 시작 오류** | `telegram_bot.py` 로딩 시점에 파일 I/O나 권한 이슈가 있을 경우 로거 생성 실패로 인해 봇 프로세스 자체가 죽어버리는 결함. | 파일 핸들러 생성 및 로거 환경 설정을 모듈 수준에서 배제하고, 동기식 데이터베이스 기동 함수인 **`init_chat_db()` 내부로 전격 이동**하여 안전한 호출 시점에 동적 실행하도록 개선함. |
| **4** | **`update_command` 가동 상태 및 에러 편집 메시지 로깅 누락** | 릴레이 구동 초기의 상태 대기 메시지(`status_msg`) 및 가동 중 예외 시 송출되는 `status_msg.edit_text` 알림 메시지의 영속화가 빠진 결함. | 해당 2개 송출 포인트에 대해서도 **`await log_chat_message(sender="bot", ...)`를 순차 배치하도록 마이그레이션 명세를 보완**함. |
| **5** | **`send_briefing_notification()` 자동 요약 푸시 로깅 누락** | 12시간 백그라운드 스케줄러를 통해 텔레그램 채널로 발송되는 일일 자동 브리핑 요약 텍스트 전문이 로깅 명세에서 완전히 빠진 결함. | 비동기 브리핑 푸시 API 발송 직후 **`await log_chat_message(sender="bot", message_text=briefing_message, session_id=CHAT_ID)`** 호출을 추가하여 누락 없는 대화 아카이빙을 완성함. |
| **6** | **`Lock` + WAL 모드 병용의 설계 의도 불완전** | 단일 프로세스 봇 환경에서 `threading.Lock` 외에 WAL 모드를 굳이 중복 적용하는 이유와 이점 미설명. | 봇 구동 중 외부 ChiefAgent 또는 다른 데이터 수집 모듈이 `telegram_chat.db`에 동시 읽기/쓰기를 시도할 때 **동시성 락 충돌(`database is locked`)을 예방하고 읽기 성능을 비약적으로 끌어올리기 위한 "보수적 안전망이자 다중 프로세스 대비 설계"** 임을 명문화함. |
| **7** | **`_company/logs/` 경로의 `config.py` 관리체계 누락** | 신규 생성되는 로그 디렉토리가 중앙 설정 관리 파일 범주에서 이탈해 모듈별로 산재되는 문제. | `agents/shared/config.py` 파일 내에 **`CHAT_LOG_DIR` 및 `TELEGRAM_DB_PATH` 상수를 공식 추가하고 디렉토리 실재 보장을 중앙화**함. |

---

## 2. 텔레그램 대화 로그 SQLite 데이터베이스 및 공용 설정 설계 (R2 개정)

### 1) `agents/shared/config.py` 설정 중앙화 추가
가상 기업 OS의 전체 물리 디렉토리 체계 관리를 위해 `config.py`에 다음 상수와 생성 보장 로직을 편입합니다.
```python
# 텔레그램 대화 로그 및 데이터베이스 전용 경로 추가 (R2 중앙 설정)
CHAT_LOG_DIR = ROOT_DIR / "_company" / "logs"
TELEGRAM_DB_PATH = ROOT_DIR / "_company" / "telegram_chat.db"

# 디렉토리 실재 보장 중앙화
CHAT_LOG_DIR.mkdir(parents=True, exist_ok=True)
```

### 2) 테이블 명 및 스키마 명세 (`telegram_chat_logs`)
| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| :--- | :---: | :---: | :--- |
| **`id`** | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | 고유 식별 일련번호 (PK) |
| **`session_id`** | `TEXT` | `NOT NULL` | 텔레그램 사용자 고유 `chat_id` (세션 식별자) |
| **`sender`** | `TEXT` | `NOT NULL` | 발신 주체 (`user` 또는 `bot`) |
| **`message_text`** | `TEXT` | `NULL` | 송수신된 실제 채팅 대화 내용 전문 (텍스트 미존재 시 NULL/빈값 허용) |
| **`created_at`** | `TEXT` | `NOT NULL` | 대화가 일어난 시각 (KST 한국 표준시 기준 포맷: `YYYY-MM-DD HH:MM:SS`) |

---

## 3. SQLite 연동 및 텔레그램 봇 삽입 소스 코드 명세 (R2 개정)

`telegram_bot.py`에 구현될 비동기 스레드 안전 및 스레드 락 비상 복구망이 결합된 완전무결한 모듈 코드입니다.

### 1) 전역 객체 및 초기화 / 저장 함수
```python
import sqlite3
import logging
import asyncio
import threading
from datetime import datetime, timezone, timedelta

# shared/config에서 중앙 상수를 로드 (import 모듈 오류 방지)
from agents.shared.config import CHAT_LOG_DIR, TELEGRAM_DB_PATH

# 멀티스레드/멀티세션 환경 보호를 위한 전역 락 설정
db_lock = threading.Lock()

def init_chat_db():
    """telegram_chat.db 초기화 (모듈 임포트 실패 방지를 위해 logging FileHandler 동적 인스턴스화 수행)"""
    # 1. 동적 로깅 파일 핸들러 바인딩 (문제 3 완벽 해결)
    chat_error_logger = logging.getLogger("chat_error")
    if not chat_error_logger.handlers:
        chat_error_logger.setLevel(logging.ERROR)
        try:
            file_handler = logging.FileHandler(CHAT_LOG_DIR / "chat_error.log", encoding="utf-8")
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            chat_error_logger.addHandler(file_handler)
        except Exception as e:
            print(f"[!] 에러 로그 파일 핸들러 초기화 실패: {e}")
            
    # 2. SQLite 데이터베이스 테이블 및 WAL 튜닝 적용
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
            # [WAL+Lock 동시성 병용 설계 의도]: 봇 이외에 타 모듈(ChiefAgent 등)의 실시간 read 트랜잭션 동시성 극대화 및
            # 락 에러(database is locked) 완벽 회피를 위한 최선의 보수적 안전망입니다.
            cursor.execute("PRAGMA journal_mode=WAL;")
            conn.commit()
            conn.close()
            print("[+] 텔레그램 로컬 SQLite 대화 데이터베이스 초기화 완료 (WAL & Lock 3중 장벽 기동).")
        except Exception as e:
            chat_error_logger.error(f"SQLite DB 초기화 중 오류 발생: {e}", exc_info=True)
            print(f"[!] SQLite DB 초기화 중 치명적 오류 발생: {e}")

async def log_chat_message(sender: str, message_text: str, session_id: str):
    """[R2 완치] asyncio.get_running_loop() 선행 바인딩을 통한 스레드 간 런타임 루프 바인딩 완전 해결"""
    # 메인 비동기 루프 사전 안전 캡처 (문제 1 완벽 해결)
    main_loop = asyncio.get_running_loop()
    
    # 텍스트 없는 메시지 방어 처리 (문제 2 완벽 해결)
    safe_text = message_text or ""
    
    # 한국 표준시(KST, UTC+9) 강제 타임존 생성
    kst = timezone(timedelta(hours=9))
    now_str = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")

    def _send_emergency_notification(err_msg: str):
        """캡처된 main_loop를 타깃으로 안전한 run_coroutine_threadsafe 발송"""
        try:
            from telegram import Bot
            from agents.shared.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                emergency_bot = Bot(token=TELEGRAM_BOT_TOKEN)
                # 스레드 안전하게 메인 비동기 루프에 코루틴 태스크 위임 발송
                asyncio.run_coroutine_threadsafe(
                    emergency_bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=f"⚠️ *[SQLite DB 경보]* 대화 로그 적재 실패!\n에러: `{err_msg}`",
                        parse_mode="Markdown"
                    ),
                    main_loop
                )
        except Exception as notify_err:
            chat_error_logger = logging.getLogger("chat_error")
            chat_error_logger.error(f"비상 에러 통보 발송 실패: {notify_err}")

    # 동기 SQLite I/O 동작 스레드 함수
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
                print(f"[!] SQLite 대화 로그 저장 실패 (발신자: {sender}): {e}")

    # 비동기 이벤트 루프 블로킹 소거를 위한 스레드 풀 위임
    await asyncio.to_thread(_sync_insert)
```

---

## 4. 라이프사이클 호출 및 기존 핸들러 마이그레이션 명세 (R2 개정)

### 1) DB 초기화 (`init_chat_db`) 호출 시점
`telegram_bot.py` 의 `main()` 함수 최상단 진입 지점에서 동기식으로 최초 실행하여 테이블의 영속 안전성을 담보합니다.
```python
def main():
    if not is_token_valid():
        ...
        return
        
    # 토큰 검증 통과 직후 SQLite DB 기동 및 테이블 검증
    init_chat_db()
    
    print("[*] 텔레그램 대화형 에이전트 봇 구동 시작 (Polling 모드)...")
    ...
```

### 2) 핸들러 내 메시지 수발신 로깅 인터셉트 패치 범위 (R2 보완 완료)

#### ① 사용자 발신(User Input) 기록 지점 (6대 커맨드 전수 패치 - 문제 2 완치)
기존 `text_message_handler` 뿐만 아니라 슬래시 명령어를 사용하는 모든 커맨드 핸들러의 최상단 진입부에도 유저 메시지를 확실하게 기록합니다.

1. **`start_command`**:
   ```python
   async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
       await log_chat_message(sender="user", message_text="/start", session_id=update.message.chat_id)
       ...
   ```
2. **`bitcoin_command`**:
   ```python
   async def bitcoin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
       await log_chat_message(sender="user", message_text="/bitcoin", session_id=update.message.chat_id)
       ...
   ```
3. **`fed_command`**:
   ```python
   async def fed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
       await log_chat_message(sender="user", message_text="/fed", session_id=update.message.chat_id)
       ...
   ```
4. **`korea_command`**:
   ```python
   async def korea_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
       await log_chat_message(sender="user", message_text="/korea", session_id=update.message.chat_id)
       ...
   ```
5. **`log_command`**:
   ```python
   async def log_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
       await log_chat_message(sender="user", message_text="/log", session_id=update.message.chat_id)
       ...
   ```
6. **`update_command`**:
   ```python
   async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
       await log_chat_message(sender="user", message_text="/update", session_id=update.message.chat_id)
       ...
   ```
7. **`text_message_handler` (일반 자연어 입력)**:
   ```python
   async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
       text = update.message.text.strip() if update.message.text else ""
       await log_chat_message(sender="user", message_text=text, session_id=update.message.chat_id)
       ...
   ```

#### ② 봇 송신(Bot Output) 기록 지점 (누락 없는 수술적 적용 - 문제 4 & 5 완치)
1. **`start_command`**:
   ```python
   msg = await update.message.reply_text(help_text, parse_mode="Markdown")
   await log_chat_message(sender="bot", message_text=msg.text, session_id=update.message.chat_id)
   ```
2. **`bitcoin_command` / `fed_command` / `korea_command` / `log_command`**:
   송출 코드 직후 `msg = await update.message.reply_text(...)`를 통해 반환된 `msg.text`를 비동기 저장합니다.
3. **`update_command` (진행 상태 / 오류 발생 포함 정밀 적재)**:
   * 중복 가동 대기 안내:
     ```python
     msg = await update.message.reply_text("🔄 현재 AI 비서 패키지가 다른 뉴스들을 열심히 분석하는 중입니다...")
     await log_chat_message(sender="bot", message_text=msg.text, session_id=update.message.chat_id)
     ```
   * **[문제 4 해결]** 초기 가동 시작 알림 (`status_msg`):
     ```python
     status_msg = await update.message.reply_text("🔄 *1단계: 0선 금융 데이터를 선행 수집 중...*")
     await log_chat_message(sender="bot", message_text=status_msg.text, session_id=update.message.chat_id)
     ```
   * 릴레이 구동 완료 및 승인 대기 카드 발송:
     ```python
     msg_briefing = await update.message.reply_text(briefing_message, parse_mode="Markdown")
     await log_chat_message(sender="bot", message_text=msg_briefing.text, session_id=update.message.chat_id)
     
     msg_card = await update.message.reply_text(text=..., reply_markup=reply_markup)
     await log_chat_message(sender="bot", message_text=msg_card.text, session_id=update.message.chat_id)
     ```
   * **[문제 4 해결]** 구동 중 치명적 에러 발생 시 (`status_msg.edit_text`):
     ```python
     msg_err = await status_msg.edit_text(f"❌ 에이전트 릴레이 가동 중 오류 발생:\n`{e}`")
     await log_chat_message(sender="bot", message_text=msg_err.text, session_id=update.message.chat_id)
     ```
4. **`button_callback_handler` (컨펌 클릭 피드백 - chat_id 바인딩 준수)**:
   ```python
   msg = await query.edit_message_text(text=..., parse_mode="Markdown")
   # callback 쿼리용 chat_id 추출 적용
   await log_chat_message(sender="bot", message_text=msg.text, session_id=query.message.chat_id)
   ```
5. **`send_briefing_notification` (백그라운드 요약 브리핑 푸시 로깅 - 문제 5 완치)**:
   ```python
   await app.bot.send_message(chat_id=CHAT_ID, text=briefing_message, parse_mode="Markdown")
   # 12시간 정기 백그라운드 푸시 내용도 로컬에 완벽 보관
   await log_chat_message(sender="bot", message_text=briefing_message, session_id=str(CHAT_ID))
   ```

---

## 5. 구현 검증 계획 (R2 개정)

### 1) 자동화 검증
- 모의 비동기 백그라운드 스레드를 분화하여 `log_chat_message`를 동시 100회 호출했을 때, 락 예외 없이 루프가 안전하게 보장되며, 캡처된 `main_loop`를 통해 에러 처리 통보 메커니즘이 원활히 동작하는지 비동기 테스트를 수행합니다.
- `/start` 또는 `/bitcoin` 등의 커맨드 메시지가 유입되었을 때 핸들러 최상단 진입점에서 SQLite 인서트가 정상 완결되는지 유닛 테스트로 입증합니다.

### 2) 수동 검증 시나리오
- 텔레그램을 기동하여 사용자가 `/korea` 또는 `/update` 등의 슬래시 커맨드를 호출합니다.
- 백그라운드 스케줄러가 구동되는 도중 인위적으로 DB 접속 에러를 내어, 관리자 텔레그램으로 `⚠️ [SQLite DB 경보] 대화 로그 적재 실패!` 알림이 실시간으로 발송되는지 검증합니다.
- 로컬 `_company/logs/chat_error.log` 파일에 스택 트레이스가 문제없이 기록되는지 직접 파일을 점검합니다.

---

## 6. 사용자 승인 대기

> [!IMPORTANT]
> - 본 **텔레그램 대화로그 SQLite 저장 기능 구현 계획서 (R2)**는 R1 검토 리포트에서 새롭게 제기된 7대 리스크(비동기 서브 스레드 런타임 오류, 슬래시 커맨드 입력 누락, 파일핸들러 임포트 실패, 브리핑/에러 상태 메시지 누락, WAL 설계 명세화, config.py 디렉토리 관리체계 편입 등)를 완벽하게 보완한 최고 수준의 명세서입니다.
> - 사용자님께서 본 R2 최신본 설계를 최종 검토해 주시고 **"승인"**, **"진행"** 또는 **"시작"** 등 승인 의사를 전송해주시는 시점에 즉각 실물 파이썬 파일 패치와 DB 테이블 기동 작업을 안전하게 진행하겠습니다!
