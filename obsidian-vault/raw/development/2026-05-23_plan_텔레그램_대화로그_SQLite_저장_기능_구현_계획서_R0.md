← [[Development_Hub|개발 마스터 대시보드]]

# 텔레그램 대화로그 SQLite 저장 기능 구현 계획서 (R0)

본 계획서는 사용자의 **"텔레그램 대화 로그 SQLite 저장 기능 탑재"** 요구사항에 의거하여, 가상 기업 OS 환경 내에 텔레그램 채팅 대화 로그를 실시간으로 영속화하여 적재하는 로컬 SQLite 데이터베이스 인프라 구축 및 연동 설계를 명세하는 단독 구현 계획서(R0)입니다.

불완전한 주관적 표현을 배제하고, 구체적인 SQLite 스키마 명세 및 봇 파일 삽입 코드를 정량적 팩트 중심으로 서술하였습니다.

---

## 1. 개요 및 설계 조치 명세 (R0 신설)

텔레그램 봇과 사용자가 주고받는 모든 대화 텍스트 데이터를 로컬 디바이스에 RDB 규격으로 안전하게 보관하기 위해 아래와 같이 설계 패키지를 보완하였습니다.

| 번호 | 요구 사항 | 기술 분석 및 Fact 대조 | R0 보완 설계 및 조치 사항 |
| :---: | :--- | :--- | :--- |
| **1** | **대화 로그 SQLite DB 구축** | 텔레그램 봇과의 상호작용(유저 입력 명령어/자연어, 봇 응답 메시지)이 파일 형태로만 기록되고 메신저 대화 자체는 유실되는 결함 해소 필요. | 가상 기업 OS 산하 격리 경로인 `_company/telegram_chat.db` 에 **로컬 SQLite 데이터베이스를 신설하고 자동 초기화 테이블 스키마를 구성**함. |
| **2** | **실시간 대화 로그 인터셉트 적재** | 유저 수신 지점 및 봇 송신 지점에서 데이터 경쟁 조건(Race Condition) 없이 원자적으로 SQLite 테이블에 적재하는 I/O 파이프라인 필요. | 텔레그램 봇 기동 시 SQLite 테이블 자동 생성을 보장하며, **수발신 핸들러 진입/완료 시점에 실시간으로 `INSERT`를 실행하는 공용 `log_chat_message` 유틸 코드를 명세**함. |
| **3** | **3중 자동 저장 룰 준수** | 워크스페이스 전역 규칙에 의거하여 본 계획서 역시 아티팩트 외에 2개 물리 경로에 중복 동시 영속화되어야 함. | 아티팩트 갱신과 동시에 **물리 리포트 계획서 경로(plan/) 및 Obsidian Vault 개발 문서 폴더(development/) 양쪽에 복사본 문서를 자동 동시 생성 적재**함. |

---

## 2. 텔레그램 대화 로그 SQLite 데이터베이스 설계

### 1) DB 물리 경로
- **`ROOT_DIR / "_company" / "telegram_chat.db"`**
- OS의 최고 신뢰 통제 계층 하위에 격리 개설하여 외부 접근을 제한합니다.

### 2) 테이블 명 및 스키마 명세 (`telegram_chat_logs`)
| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| :--- | :---: | :---: | :--- |
| **`id`** | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | 고유 식별 일련번호 |
| **`session_id`** | `TEXT` | `NOT NULL` | 텔레그램 사용자 고유 `chat_id` 또는 대화 세션 식별 |
| **`sender`** | `TEXT` | `NOT NULL` | 발신 주체 (`user` 또는 `bot`) |
| **`message_text`** | `TEXT` | `NOT NULL` | 송수신된 실제 채팅 대화 내용 전문 |
| **`created_at`** | `TEXT` | `NOT NULL` | 대화가 일어난 시각 (포맷: `YYYY-MM-DD HH:MM:SS`) |

---

## 3. SQLite 연동 및 텔레그램 봇 삽입 소스 코드 명세

`telegram_bot.py` 상단 및 핸들러 내에 탑재될 실제 파이썬 소스 코드 구조입니다.

### 1) SQLite DB 초기화 및 실시간 인서트 유틸리티 함수
```python
import sqlite3
from datetime import datetime
from agents.shared.config import ROOT_DIR

def init_chat_db():
    """telegram_chat.db 존재 여부를 확인하고 테이블이 없는 경우 자동 생성 보장"""
    db_path = ROOT_DIR / "_company" / "telegram_chat.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telegram_chat_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                sender TEXT NOT NULL, -- 'user' 또는 'bot'
                message_text TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
        print("[+] 텔레그램 로컬 SQLite 대화 데이터베이스 초기화 완료.")
    except Exception as e:
        print(f"[!] SQLite DB 초기화 중 치명적 오류 발생: {e}")

def log_chat_message(sender: str, message_text: str, session_id: str = "default"):
    """수발신된 대화 텍스트 전문을 원자적으로 SQLite 테이블에 실시간 Insert"""
    db_path = ROOT_DIR / "_company" / "telegram_chat.db"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO telegram_chat_logs (session_id, sender, message_text, created_at) "
            "VALUES (?, ?, ?, ?)",
            (str(session_id), sender, message_text, now_str)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[!] SQLite 대화 로그 저장 실패 (발신자: {sender}): {e}")
```

### 2) 핸들러 내 실시간 수발신 인터셉트 매핑
- **사용자 수신(User Input) 기록**:
  명령어 핸들러 및 대화 처리기(`text_message_handler`)의 최상단 진입 단계에서 메시지를 영속화합니다.
  ```python
  async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
      text = update.message.text.strip()
      # 유저 입력 메시지 SQLite 영속화
      log_chat_message(sender="user", message_text=text, session_id=update.message.chat_id)
      ...
  ```
- **봇 송신(Bot Output) 기록**:
  `reply_text` 또는 `send_message` API 발송 성공 직후 회신 텍스트 전문을 영속화합니다.
  ```python
  # 봇 메시지 전송 예시 헬퍼 함수
  async def reply_and_log(update: Update, text: str, parse_mode: str = None, reply_markup = None):
      msg = await update.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
      # 봇 응답 메시지 SQLite 영속화
      log_chat_message(sender="bot", message_text=text, session_id=update.message.chat_id)
      return msg
  ```

---

## 4. 구현 검증 계획

### 1) 자동화 검증
- SQLite DB 기동 시 테이블 `telegram_chat_logs`가 올바르게 인메모리/로컬 디바이스에 생성되는지 테스트 코드를 작성합니다.
- `log_chat_message()`를 멀티스레드 환경에서 순차 호출하여 쿼리 락(Lock) 충돌 없이 온전히 인서트가 완료되는지 안정성을 검증합니다.

### 2) 수동 검증 시나리오
- 텔레그램 봇에 `/start` 또는 자연어로 `"비트코인 요약해줘"`를 전송합니다.
- DB 브라우저 또는 CLI 스크립트(`sqlite3 _company/telegram_chat.db "SELECT * FROM telegram_chat_logs"`)를 가동하여, 송수신 텍스트 로그가 아래 예시와 같이 완벽히 영속 기록되었는지 직접 데이터를 점검합니다:
  ```text
  1 | 12345678 | user | 비트코인 요약해줘 | 2026-05-23 17:02:40
  2 | 12345678 | bot  | 🪙 *[Bitcoin] 가상자산 지식 누적 분석*... | 2026-05-23 17:02:42
  ```

---

## 5. 사용자 승인 대기

> [!IMPORTANT]
> - 본 **텔레그램 대화로그 SQLite 저장 기능 구현 계획서 (R0)**는 텔레그램 채팅 대화 기록을 로컬 SQLite 데이터베이스(`telegram_chat.db`)에 누적하는 연동 파이프라인 명세서입니다.
> - 사용자님께서 검토 후 **"승인"**, **"진행"** 또는 **"시작"** 등 명시적인 실행 의사를 전송해 주시면, 즉각 SQLite DB 초기화 코드 설계 및 `telegram_bot.py` 대화 수발신 인터셉터 개발에 착수하도록 하겠습니다.
