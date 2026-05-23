# scraper.py (레거시 하위 호환성 확보를 위한 Thin Wrapper 래퍼)

import sys
from pathlib import Path
from agents.shared.config import (
    OLLAMA_API_URL, OLLAMA_MODEL, DEEPSEARCH_API_KEY, ECOS_API_KEY
)
from agents.chief_agent import ChiefAgent

# 윈도우 인코딩 설정 호환성 노출
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# 레거시 상수 호환성 보장
ENRICH_MODEL = OLLAMA_MODEL

def scrape_news() -> str:
    """
    [레거시 호환 Thin Wrapper]
    기존 텔레그램 봇이나 스케줄러가 scrape_news()를 호출하면, 
    새로운 agents 패키지의 총괄팀장 chief_agent를 통해 전체 릴레이 구동을 위임 실행합니다.
    """
    print("[*] [레거시 호환 Thin Wrapper] scraper.scrape_news() 호출됨 -> chief_agent.run_relay() 위임 실행 개시")
    agent = ChiefAgent()
    briefing = agent.run_relay()
    return briefing

if __name__ == "__main__":
    scrape_news()
