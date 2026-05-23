import json
import time
import requests
from datetime import datetime
from typing import Dict, Any

from agents.shared.config import FINANCIAL_DATA_PATH, ECOS_API_KEY
from agents.shared.protocols import AgentResult
from agents.shared.file_utils import write_file_safely

class DBManager:
    """DB 관리자 에이전트: 0선 선행 금융 데이터 수집 및 원자적 영속화 담당"""
    
    def __init__(self):
        self.agent_name = "DBManager"
        
    def collect(self) -> AgentResult:
        """
        [0선 실행 메서드] 실시간 계량 지표(Upbit, Binance, ECOS, Fallback 환율)를 수집하여
        원자적으로 캐싱하고 인메모리 데이터 딕셔너리를 payload로 공급합니다.
        """
        start_time = time.time()
        errors = []
        
        print("\n" + "="*55)
        print(f"[*] [{self.agent_name}] 0선: 실시간 금융 및 크립토 주요 지표 수집 가동...")
        print("="*55)
        
        # 1. 업비트 BTC/KRW 조회
        btc_krw, btc_krw_change = 0.0, 0.0
        try:
            btc_krw, btc_krw_change = self._fetch_upbit_btc()
        except Exception as e:
            err = f"Upbit 수집 실패: {e}"
            print(f"    [!] {err}")
            errors.append(err)
            
        # 2. 바이낸스 BTC/USDT 조회
        btc_usd = 0.0
        try:
            btc_usd = self._fetch_binance_btc()
        except Exception as e:
            err = f"Binance 수집 실패: {e}"
            print(f"    [!] {err}")
            errors.append(err)
            
        # 3. 한국은행 ECOS 환율 및 기준금리 조회
        exchange_rate = 0.0
        try:
            exchange_rate = self._fetch_ecos_data(ECOS_API_KEY, "036Y001", "0000001", 0.0)
            if exchange_rate <= 0.0:
                print("    [*] ECOS 환율 조회 실패 또는 API 키 누락. Fallback 오픈 환율 API로 전환합니다...")
                exchange_rate = self._fetch_fallback_exchange_rate()
        except Exception as e:
            err = f"ECOS 환율 수집 실패: {e}"
            print(f"    [!] {err}")
            errors.append(err)
            exchange_rate = self._fetch_fallback_exchange_rate()
            
        bok_rate = 3.50
        try:
            bok_rate = self._fetch_ecos_data(ECOS_API_KEY, "098Y001", "0101000", 3.50)
        except Exception as e:
            err = f"ECOS 기준금리 수집 실패: {e}"
            print(f"    [!] {err}")
            errors.append(err)
            
        # 4. 김치 프리미엄 연산
        kimchi_premium = 0.0
        if btc_usd > 0.0 and exchange_rate > 0.0 and btc_krw > 0.0:
            converted_krw = btc_usd * exchange_rate
            kimchi_premium = ((btc_krw - converted_krw) / converted_krw) * 100
            
        financial_data = {
            "btc_krw": btc_krw,
            "btc_krw_change": round(btc_krw_change, 2),
            "btc_usd": btc_usd,
            "exchange_rate": round(exchange_rate, 2),
            "bok_rate": round(bok_rate, 2),
            "kimchi_premium": round(kimchi_premium, 2),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 5. 원자적 안전 캐시 영속화 (경쟁 조건 방지)
        try:
            json_str = json.dumps(financial_data, ensure_ascii=False, indent=2)
            write_file_safely(FINANCIAL_DATA_PATH, json_str)
            print(f"\n[+] 금융 데이터 원자적 캐싱 성공 ({FINANCIAL_DATA_PATH.name}) -> {financial_data}")
        except Exception as e:
            err = f"금융 데이터 JSON 안전 캐시 쓰기 오류: {e}"
            print(f"    [!] {err}")
            errors.append(err)
            
        elapsed = time.time() - start_time
        return AgentResult(
            agent_name=self.agent_name,
            success=len(errors) < 3,  # 완전 붕괴(치명적 API 에러 3개 이상)가 아니면 릴레이 진행 허용
            collected_count=6,
            files_created=[str(FINANCIAL_DATA_PATH)],
            errors=errors,
            elapsed_seconds=elapsed,
            payload=financial_data
        )

    def _fetch_upbit_btc(self) -> tuple:
        """업비트 API 연동 BTC 원화 시세 및 변동률 조회"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC", headers=headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            if data and len(data) > 0:
                trade_price = float(data[0].get("trade_price", 0))
                change_rate = float(data[0].get("signed_change_rate", 0)) * 100
                print(f"    [+] Upbit 성공: {trade_price:,.0f}원 ({change_rate:+.2f}%)")
                return trade_price, change_rate
        return 0.0, 0.0

    def _fetch_binance_btc(self) -> float:
        """바이낸스 API 연동 BTC 달러 시세 조회"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", headers=headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            price = float(data.get("price", 0))
            print(f"    [+] Binance 성공: ${price:,.2f}")
            return price
        return 0.0

    def _fetch_ecos_data(self, api_key: str, table_code: str, item_code: str, default_val: float) -> float:
        """한국은행 ECOS API를 통한 실 최신 통계 조회"""
        if not api_key or api_key == "sample_key":
            return default_val
        try:
            from datetime import timedelta
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=15)).strftime("%Y%m%d")
            url = f"http://ecos.bok.or.kr/api/StatisticSearch/{api_key}/json/kr/1/15/{table_code}/DD/{start_date}/{end_date}/{item_code}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            res = requests.get(url, headers=headers, timeout=8)
            if res.status_code == 200:
                data = res.json()
                if "StatisticSearch" in data and "row" in data["StatisticSearch"]:
                    rows = data["StatisticSearch"]["row"]
                    if rows:
                        latest_row = rows[-1]
                        val = float(latest_row["DATA_VALUE"])
                        print(f"    [+] ECOS 성공 ({table_code}): {val}")
                        return val
        except Exception:
            pass
        return default_val

    def _fetch_fallback_exchange_rate(self) -> float:
        """환율 조회 이중 Fallback API 작동"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            res = requests.get("https://open.er-api.com/v6/latest/USD", headers=headers, timeout=8)
            if res.status_code == 200:
                data = res.json()
                rate = float(data.get("rates", {}).get("KRW", 1350.0))
                print(f"    [+] Fallback 환율 성공: {rate:,.2f}원")
                return rate
        except Exception:
            pass
        return 1350.0
