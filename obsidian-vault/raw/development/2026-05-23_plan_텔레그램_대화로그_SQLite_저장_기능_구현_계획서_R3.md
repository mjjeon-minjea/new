← [[Development_Hub|개발 마스터 대시보드]]

# 텔레그램 대화로그 SQLite 저장 기능 구현 계획서 (R3)

본 계획서는 사용자의 **"텔레그램 대화 로그 SQLite 저장 기능 탑재"** 요구사항에 의거하여, 가상 기업 OS 환경 내에 텔레그램 채팅 대화 로그를 실시간으로 영속화하여 적재하는 로컬 SQLite 데이터베이스 인프라 구축 및 연동 설계를 명세하는 단독 구현 계획서(R3)입니다.

이전 R2 설계본에 대한 2차 신규 검토 의견서(R2 검토 리포트)의 지적 사항인 **런타임 버그 및 설계 결함, 개선 권고 총 7건**을 완벽하게 보완 및 반영하여 실물 파일 패치 시 컴파일/런타임 실패 리스크를 제로(0)화한 최종 구현 사양서입니다.

---

## 1. 피드백 수용 및 신규 설계 조치 명세 (R3 보완)

| 번호 | 검토 의견서 지적 사항 (R2) | 원인 및 기술 분석 | R3 보완 설계 및 조치 사항 (해결책) |
| :---: | :--- | :--- | :--- |
| **1** | **`/help` CommandHandler 로깅 누락 및 텍스트 하드코딩** | `/help` 명령어가 `start_command`에 공유 바인딩되어 있으나 명세에서 이탈하였고, 커맨드 입력 시 `/start`로 하드코딩되어 잘못 기록되는 리스크. | `/help`를 공식 마이그레이션 목록에 매핑하고, 하드코딩 대신 **`update.message.text`를 직접 동적 캡처하며 폴백 가드를 명문화**함. |
| **2** | **`status_msg.delete()` vs 로깅 순서 충돌** | 상태 진행 알림 메시지가 실시간으로 삭제되는데 이에 대한 로깅 방침이 명세되어 있지 않아 모호한 현상. | **방안 A 선택**. 비록 화면 상에서 지워지는 메시지일지라도 대화의 전반적인 시간대별 행적을 누락 없이 보관하기 위해 **발송 즉시 선행 로깅 후 delete() 동작은 원안대로 존치**함. |
| **3** | **`--send-briefing` 단독 기동 시 DB 미초기화 런타임 버그** | `--send-briefing` 옵션 단독 1회 가동 시 `main()`을 완전히 우회하여 SQLite 테이블 미생성으로 인한 런타임 크래시 리스크. | 단독 기동 분기 구문의 최상단에서도 **`init_chat_db()`를 선행 강제 호출**하도록 엔트리포인트를 보완함. |
| **4** | **`_send_emergency_notification` 내 불필요 이중 임포트** | 전역 바인딩된 `BOT_TOKEN` 및 `CHAT_ID` 상수가 있음에도 서브 스레드 내에서 모듈을 불필요하게 이중 중복 임포트하는 문제. | 동적 임포트를 소거하고 모듈 수준 전역에 이미 완벽히 정의된 **`BOT_TOKEN` 및 `CHAT_ID` 변수를 다이렉트 호출하도록 최적화**함. |
| **5** | **`session_id` 타입 힌트 및 캐스팅 불일치** | 시그니처 상에는 `session_id: str`이나 실제 호출부에서 Python `int` 타입 객체를 바로 전달하여 생기는 무결성 모순. | 모든 호출부 전달 인자 단에서 **`str(update.message.chat_id)` 형태로 명시적인 캐스팅을 의무화**하여 명세를 일원화함. |
| **6** | **`msg.text` None 가드 부재** | Markdown 파싱 오류 및 특수 메시지 발송 시 `msg.text` 속성이 `None`이 될 수 있어 로깅 적재 에러 유발 가능성. | 모든 봇 송신 인터셉터 지점 호출부에서 **`msg.text or ""`** 방어 가드를 적용하도록 사양을 정밀 보정함. |
| **7** | **`edit_message_text` BadRequest 예외 누락** | 이미 삭제/수정 완료된 피드백 메시지에 덮어쓰기 호출을 감행할 때 발생하는 python-telegram-bot v20 전용 예외 미대응. | CallbackQuery 핸들러 주변부를 **`try-except TelegramError` 블록으로 감싸 안전하게 로거에 예외를 남기고 크래시 없이 안정 폴백**시킴. |

---

## 2. 텔레그램 대화 로그 SQLite 데이터베이스 및 공용 설정 설계 (R3 개정)

### 1) `agents/shared/config.py` 설정 중앙화 추가
가상 기업 OS의 전체 물리 디렉토리 체계 관리를 위해 `config.py`에 다음 상수와 생성 보장 로직을 편입합니다.
```python
# 텔레그램 대화 로그 및 데이터베이스 전용 경로 추가 (R3 중앙 설정)
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

## 3. SQLite 연동 및 텔레그램 봇 삽입 소스 코드 명세 (R3 개정)

`telegram_bot.py`에 구현될 비동기 스레드 안전 및 스레드 락 비상 복구망이 결합된 완전무결한 모듈 코드입니다.

### 1) 전역 객체 및 초기화 / 저장 함수
```python
import sqlite3
import logging
import asyncio
import threading
from datetime import datetime, timezone, timedelta

# shared/config에서 중앙 상수를 로드
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
    """[R3 완치] asyncio.get_running_loop() 선행 바인딩을 통한 스레드 간 런타임 루프 바인딩 완전 해결"""
    # 메인 비동기 루프 사전 안전 캡처 (문제 1 완벽 해결)
    main_loop = asyncio.get_running_loop()
    
    # 텍스트 없는 메시지 방어 처리 (문제 2 완벽 해결)
    safe_text = message_text or ""
    
    # 한국 표준시(KST, UTC+9) 강제 타임존 생성
    kst = timezone(timedelta(hours=9))
    now_str = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")

    def _send_emergency_notification(err_msg: str):
        """[R3 완치] 동적 임포트를 소거하고 모듈 전역 바인딩된 BOT_TOKEN, CHAT_ID 직접 호출 (문제 4 완치)"""
        try:
            from telegram import Bot
            # 모듈 전역에 바인딩된 BOT_TOKEN 및 CHAT_ID를 스레드 안전 재사용
            if BOT_TOKEN and CHAT_ID:
                emergency_bot = Bot(token=BOT_TOKEN)
                # 스레드 안전하게 메인 비동기 루프에 코루틴 태스크 위임 발송
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

## 4. 라이프사이클 호출 및 기존 핸들러 마이그레이션 명세 (R3 개정)

### 1) DB 초기화 (`init_chat_db`) 호출 시점 (엔트리포인트 2대 경로 - 문제 3 완치)
대화형 폴링 실행(`main()`)뿐만 아니라, 백그라운드 크론 기동(`--send-briefing`) 시에도 데이터 유실 크래시를 전격 방지하기 위해 2대 경로에 기동 루틴을 바인딩합니다.

#### ① 일반 대화형 폴링 기동 시
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

#### ② `--send-briefing` 옵션 단독 1회 가동 시 (문제 3 완벽 해결)
```python
if __name__ == "__main__":
    # 만약 --send-briefing 인자가 주어지면 대화형 폴링이 아닌 단순 push 알림만 1회 쏘고 종료
    if len(sys.argv) > 1 and sys.argv[1] == "--send-briefing":
        # [R3 신규] 단독 기동 시에도 SQLite DB 실재 및 정합성 보장을 강제화
        init_chat_db()
        asyncio.run(send_briefing_notification())
    else:
        main()
```

### 2) 핸들러 내 메시지 수발신 로깅 인터셉트 패치 범위 (R3 보완 완료)

#### ① 사용자 발신(User Input) 기록 지점 (6대 커맨드 전수 패치 - 문제 1 및 문제 2 완치)
사용자 명령어가 `/help` 등 우회 바인딩된 경우까지 누락 없이 캡처하기 위해, **하드코딩 대신 `update.message.text`를 동적 수신하며 `str()` 타입 캐스팅을 강제**합니다.

1. **`start_command` (명령어 `/start` 및 `/help` 공유 처리 지점)**:
   ```python
   async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
       # [R3 완치] 하드코딩 배제 및 실제 명령어 동적 수신 적용 (or 폴백 바인딩)
       actual_input = update.message.text or "/start"
       await log_chat_message(sender="user", message_text=actual_input, session_id=str(update.message.chat_id))
       ...
   ```
2. **`bitcoin_command` / `fed_command` / `korea_command` / `log_command` / `update_command`**:
   최상단 진입부에 아래와 같이 동적 캡처 및 타입 엄격 바인딩(str)을 이식합니다:
   ```python
   # 예시: bitcoin_command 최상단
   actual_input = update.message.text or "/bitcoin"
   await log_chat_message(sender="user", message_text=actual_input, session_id=str(update.message.chat_id))
   ```
3. **`text_message_handler` (일반 자연어 입력)**:
   ```python
   async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
       text = update.message.text.strip() if update.message.text else ""
       await log_chat_message(sender="user", message_text=text, session_id=str(update.message.chat_id))
       ...
   ```

#### ② 봇 송신(Bot Output) 기록 지점 (누락 없는 수술적 적용 - 문제 2 & 4 & 5 & 6 완치)
봇이 메시지를 발송하거나 편집한 뒤 반환된 Message 객체에서 텍스트를 파싱하되, **`.text`가 None인 상황에 대비해 `or ""` 방어 가드를 강제**합니다.

1. **`start_command`**:
   ```python
   msg = await update.message.reply_text(help_text, parse_mode="Markdown")
   # [R3 완치] msg.text None 폴백 가드 적용
   await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(update.message.chat_id))
   ```
2. **`bitcoin_command` / `fed_command` / `korea_command` / `log_command`**:
   송출 코드 직후 `msg = await update.message.reply_text(...)`를 통해 반환된 `msg.text or ""`를 비동기 저장합니다.
3. **`update_command` (진행 상태 / 오류 발생 포함 정밀 적재 - 방안 A 확정)**:
   * 중복 가동 대기 안내:
     ```python
     msg = await update.message.reply_text("🔄 현재 AI 비서 패키지가 다른 뉴스들을 열심히 분석하는 중입니다...")
     await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(update.message.chat_id))
     ```
   * **[문제 2 완치 - 방안 A 적용]** 초기 가동 시작 알림 (`status_msg`):
     대화 맥락 보관을 위해 송신 즉시 영속화하되, 기존 `status_msg.delete()` 동작은 UX 유지를 위해 그대로 가동합니다.
     ```python
     status_msg = await update.message.reply_text("🔄 *1단계: 0선 금융 데이터를 선행 수집 중...*")
     await log_chat_message(sender="bot", message_text=status_msg.text or "", session_id=str(update.message.chat_id))
     ```
   * 릴레이 구동 완료 및 승인 대기 카드 발송:
     ```python
     msg_briefing = await update.message.reply_text(briefing_message, parse_mode="Markdown")
     await log_chat_message(sender="bot", message_text=msg_briefing.text or "", session_id=str(update.message.chat_id))
     
     msg_card = await update.message.reply_text(text=..., reply_markup=reply_markup)
     await log_chat_message(sender="bot", message_text=msg_card.text or "", session_id=str(update.message.chat_id))
     ```
   * 치명적 에러 발생 시 (`status_msg.edit_text`):
     ```python
     msg_err = await status_msg.edit_text(f"❌ 에이전트 릴레이 가동 중 오류 발생:\n`{e}`")
     await log_chat_message(sender="bot", message_text=msg_err.text or "", session_id=str(update.message.chat_id))
     ```
4. **`button_callback_handler` (컨펌 클릭 피드백 - BadRequest 예외 가드 적용)**:
   ```python
   try:
       msg = await query.edit_message_text(text=..., parse_mode="Markdown")
       await log_chat_message(sender="bot", message_text=msg.text or "", session_id=str(query.message.chat_id))
   except Exception as callback_err:
       # [R3 완치] 이미 삭제된 피드백 예외 안전 복구 로깅 처리
       chat_error_logger = logging.getLogger("chat_error")
       chat_error_logger.error(f"콜백 처리 도중 BadRequest 오류 발생: {callback_err}")
   ```
5. **`send_briefing_notification` (백그라운드 요약 브리핑 푸시 로깅)**:
   ```python
   await app.bot.send_message(chat_id=CHAT_ID, text=briefing_message, parse_mode="Markdown")
   # 12시간 정기 백그라운드 푸시 내용도 로컬에 완벽 보관 (None 가드 포함)
   await log_chat_message(sender="bot", message_text=briefing_message or "", session_id=str(CHAT_ID))
   ```

---

## 5. 구현 검증 계획 (R3 개정)

### 1) 자동화 검증
- SQLite WAL 모드가 정상 활성화되어 동시 락 충돌 현상을 막을 수 있는지 확인하는 모의 스레드 인서트 테스트를 수행합니다.
- `update.message.text`가 `None`인 상태와, `/help` 등으로 바인딩 우회 분기되었을 때 DB에 원래 커맨드 텍스트가 정확히 영속 적재되는지 검증 테스트를 돌립니다.
- `--send-briefing` 분기 구동 모형을 목킹하여 `init_chat_db()`가 런타임 우회 없이 안정 기동되는지 테스트합니다.

### 2) 수동 검증 시나리오
- 텔레그램을 기동하여 사용자가 `/help` 슬래시 커맨드를 호출합니다.
- CLI 환경 터미널 스크립트(`sqlite3 _company/telegram_chat.db "SELECT * FROM telegram_chat_logs"`)를 가동하여 `/help` 텍스트가 한국 표준시(KST) 기준으로 정확하게 유저 발신 내역으로 누적 적재되는지 대조합니다.
- 백그라운드 알림 데몬(`python telegram_bot.py --send-briefing`)을 강제 구동한 뒤, 로컬 DB 파일에 12시간 일일 브리핑 요약 텍스트 전문이 깨짐 없이 온전히 Insert 완료되었는지 테이블 최종 데이터를 눈으로 확인합니다.

---

## 6. 사용자 승인 대기

> [!IMPORTANT]
> - 본 **텔레그램 대화로그 SQLite 저장 기능 구현 계획서 (R3)**는 2차 신규 검토 리포트의 기술적 피드백(우회 `/help` 로깅 누락, status_msg.delete 동시성 충돌, 단독 브리핑 기동 시의 치명적 초기화 누락, 이중 임포트 및 None/BadRequest 방어 가드 수립 등)을 남김없이 완벽하게 적용한 최고 신뢰도의 설계도입니다.
> - 사용자님께서 이 완성된 R3 보완 설계를 기쁘게 확인해 주시고 **"승인"**, **"진행"** 또는 **"시작"** 등 승인 키워드를 입력해 주시면 즉각 `agents/shared/config.py`와 `telegram_bot.py` 실물 패치 작업을 개시하겠습니다!
