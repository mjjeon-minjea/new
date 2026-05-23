from agents.base_reporter import BaseReporter

class KoreaReporter(BaseReporter):
    """국내 경제 정보 수집 및 리포터 에이전트 (초경량 설정 객체)"""
    
    def __init__(self):
        config = {
            "agent_name": "KoreaReporter",
            "category": "korea",
            "deepsearch_endpoint": "/v1/articles",
            "deepsearch_keyword": "삼성전자 OR '한국 경제 금리' OR 반도체",
            "rss_urls": [
                {"name": "Google News Korea", "url": "https://news.google.com/rss/search?q=%ED%95%9C%EA%B5%AD%EA%B2%BD%EC%A0%9C+%EA%B8%88%EB%A6%AC&hl=ko&gl=KR&ceid=KR:ko"},
                {"name": "조선일보 경제", "url": "https://www.chosun.com/arc/outboundfeeds/rss/category/economy/?outputType=xml"},
                {"name": "동아일보 경제", "url": "https://rss.donga.com/economy.xml"},
                {"name": "SBS 경제뉴스", "url": "https://news.sbs.co.kr/news/ReplayRss.do?section=02"}
            ],
            "special_prompts": "국내 거시경제 및 핵심 반도체 제조업(삼성전자 등) 동향이 국내 금리 정책이나 환율에 미치는 영향을 고가독성의 금융 분석으로 정리하십시오."
        }
        super().__init__(config)
