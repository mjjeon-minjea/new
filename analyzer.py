# analyzer.py (레거시 하위 호환성 확보를 위한 Thin Wrapper 래퍼)

import sys
from agents.shared.config import OLLAMA_API_URL, OLLAMA_MODEL
from agents.wiki_manager import WikiManager

# 윈도우 인코딩 설정 호환성 노출
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

def run_analysis() -> str:
    """
    [레거시 호환 Thin Wrapper]
    기존 시스템이 analyzer.run_analysis()를 호출하면,
    신규 WikiManager 에이전트를 구동하여 미처리 뉴스의 지식 합성(Compounding)을 수행합니다.
    """
    print("[*] [레거시 호환 Thin Wrapper] analyzer.run_analysis() 호출됨 -> wiki_manager.run_compounding() 위임 실행 개시")
    manager = WikiManager()
    
    # 0선 DB 데이터를 로드하여 연계하기 위해 config의 캐시를 로딩해 주입함
    from agents.shared.config import FINANCIAL_DATA_PATH
    import json
    financial_data = {}
    if FINANCIAL_DATA_PATH.exists():
        try:
            with open(FINANCIAL_DATA_PATH, "r", encoding="utf-8") as f:
                financial_data = json.load(f)
        except Exception:
            pass
            
    res = manager.run_compounding(financial_data)
    return f"위키 갱신 성공 여부: {res.success} | 갱신 파일 수: {res.collected_count}"

if __name__ == "__main__":
    run_analysis()
