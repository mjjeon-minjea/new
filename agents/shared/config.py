import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 1. 윈도우 환경 콘솔 출력 인코딩 에러 방지 (중복 제거 및 일원화)
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# 2. .env 로드
load_dotenv()

# 3. 경로 정의 및 디렉토리 자동 생성
ROOT_DIR = Path(__file__).parent.parent.parent.resolve()

# Obsidian Vault 관련 경로 설정
vault_path_str = os.getenv("OBSIDIAN_VAULT_PATH", "obsidian-vault")
VAULT_PATH = ROOT_DIR / vault_path_str
RAW_DIR = VAULT_PATH / "raw"
WIKI_DIR = VAULT_PATH / "wiki"

# 가상 기업 OS 격리 디렉토리 경로 추가 (R4 최종 설계 반영)
DECISIONS_PATH = ROOT_DIR / "_company" / "_shared" / "decisions.md"
APPROVALS_PENDING_DIR = ROOT_DIR / "_company" / "approvals" / "pending"
APPROVALS_APPROVED_DIR = ROOT_DIR / "_company" / "approvals" / "approved"
SESSIONS_DIR = ROOT_DIR / "_company" / "sessions"
CHAT_LOG_DIR = ROOT_DIR / "_company" / "logs"
TELEGRAM_DB_PATH = ROOT_DIR / "_company" / "telegram_chat.db"

# 디렉토리 실재 보장
RAW_DIR.mkdir(parents=True, exist_ok=True)
WIKI_DIR.mkdir(parents=True, exist_ok=True)
APPROVALS_PENDING_DIR.mkdir(parents=True, exist_ok=True)
APPROVALS_APPROVED_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
CHAT_LOG_DIR.mkdir(parents=True, exist_ok=True)

# 실시간 금융 지표 캐시 경로 (중앙 관리)
FINANCIAL_DATA_PATH = ROOT_DIR / "financial_data.json"

# 4. API 설정 상수
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e4b")

DEEPSEARCH_API_KEY = os.getenv("DEEPSEARCH_API_KEY", "DEMO_API_KEY")
DEEPSEARCH_API_URL = "https://api-v2.deepsearch.com"
ECOS_API_KEY = os.getenv("ECOS_API_KEY", "sample_key")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
