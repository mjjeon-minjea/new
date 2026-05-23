from agents.base_reporter import BaseReporter

class GlobalReporter(BaseReporter):
    """해외 내지 글로벌 경제 정보 수집 및 리포터 에이전트 (초경량 설정 객체)"""
    
    def __init__(self):
        config = {
            "agent_name": "GlobalReporter",
            "category": "global",
            "deepsearch_endpoint": "/v1/global-articles",
            "deepsearch_keyword": "Federal Reserve OR FOMC OR 'Interest Rate'",
            "rss_urls": [
                {"name": "Google News Global", "url": "https://news.google.com/rss/search?q=%EC%84%B8%EA%B3%84%EA%B2%BD%EC%A0%9C&hl=ko&gl=KR&ceid=KR:ko"}
            ],
            "special_prompts": "미국 연방준비제도(연준)의 긴축/완화 정책 결정(금리 인상/인하)이나 주요 연사들의 매파적/비둘기파적 발언이 글로벌 달러 자산 및 채권 시장에 주는 거시 경제 효과를 전문성 있게 정리하십시오."
        }
        super().__init__(config)
