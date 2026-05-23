from typing import Dict, Any
from agents.base_reporter import BaseReporter

class BitcoinReporter(BaseReporter):
    """비트코인 정보 수집 및 리포터 에이전트 (초경량 설정 객체)"""
    
    def __init__(self):
        config = {
            "agent_name": "BitcoinReporter",
            "category": "bitcoin",
            "deepsearch_endpoint": "/v1/global-articles",
            "deepsearch_keyword": "Bitcoin OR BTC OR Crypt",
            "rss_urls": [
                {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/"},
                {"name": "CoinTelegraph", "url": "https://cointelegraph.com/rss"},
                {"name": "Decrypt", "url": "https://decrypt.co/feed"},
                {"name": "Blockworks", "url": "https://blockworks.co/feed"}
            ],
            "special_prompts": "크립토 온체인 동향(고래 이동, 채굴 해시레이트 등) 및 주요 규제(SEC 동향 등)를 당일 실시간 시세 변동률 및 김치프리미엄 지표와 연계하여 가상자산 시장 분석을 풍성하게 기술하십시오."
        }
        super().__init__(config)

    def _should_enrich(self, article: Dict[str, Any]) -> bool:
        """
        비트코인 뉴스는 해외 매체(영문) 위주로 구성되어 있으므로,
        본문 길이와 상관없이 항상 AI Enrichment(한글 번역 및 특화 분석)를 적용하도록 True로 오버라이드합니다.
        """
        return True
