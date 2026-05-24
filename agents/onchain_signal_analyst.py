import time
from pathlib import Path
from typing import Dict, Any, Optional

from agents.shared.protocols import AgentResult
from agents.shared.ollama_client import call_ollama
from agents.shared.config import RAW_DIR

class OnchainSignalAnalyst:
    """5선 크립토/비트코인 온체인 신호 분석가 에이전트"""
    
    def __init__(self):
        self.agent_name = "OnchainSignalAnalyst"
        
    def analyze(self, financial_data: Optional[Dict[str, Any]], session_dir: Path) -> AgentResult:
        """
        0선 금융/크립토 지표 데이터를 수신하여 비트코인 온체인 수급 및 네트워크 지표를 심층 분석하고,
        'onchain_signal.md' 초안 보고서를 작성하여 반환합니다.
        """
        start_time = time.time()
        errors = []
        files_created = []
        signal_content = ""
        
        # 지표 정보 포맷팅
        btc_krw = financial_data.get("btc_krw", 0.0) if financial_data else 0.0
        btc_krw_change = financial_data.get("btc_krw_change", 0.0) if financial_data else 0.0
        btc_usd = financial_data.get("btc_usd", 0.0) if financial_data else 0.0
        kimchi_premium = financial_data.get("kimchi_premium", 0.0) if financial_data else 0.0
        
        system_prompt = (
            "당신은 글로벌 탑 티어 가상자산 헤지펀드의 수석 온체인 퀀트 분석가이자 신호 분석가입니다. "
            "주어진 비트코인 지표와 김치 프리미엄 변동성을 분석하여 단기/중기 온체인 수급 시그널 및 네트워크 강건성 지표를 한국어로 도출합니다. "
            "추측성 가십을 철저히 차단하고 오직 데이터가 지시하는 네트워크 징후만을 수학적이고 객관적으로 해부하십시오."
        )
        
        user_prompt = (
            f"[실시간 온체인/크립토 주요 지표]\n"
            f"- 비트코인 원화 시세 (Upbit): {btc_krw:,.0f}원 ({btc_krw_change:+.2f}%)\n"
            f"- 비트코인 달러 시세 (Binance): {btc_usd:,.2f} USD\n"
            f"- 김치 프리미엄 (Premium): {kimchi_premium:+.2f}%\n\n"
            "위 지표들을 분석하여 비트코인 네트워크 해시레이트의 강건성, 채굴자 지출 수준, 대형 지갑 주소의 유출입 징후 등을 간접 추정하고, "
            "김치 프리미엄 변동성이 지시하는 대내외 수급 괴리 분석 결과를 마크다운 포맷으로 간결하고 직관적이게 작성해 주십시오."
        )
        
        try:
            # LLM 호출
            signal_content = call_ollama(user_prompt, system_prompt)
            if not signal_content:
                raise ValueError("Ollama 모델로부터 응답을 받지 못했거나 빈 응답이 반환되었습니다.")
                
            # 파일 영속화 저장
            file_path = session_dir / "onchain_signal.md"
            file_path.write_text(signal_content, encoding="utf-8")
            files_created.append(str(file_path))
            
            # Obsidian Vault raw/strategy/ 동시 저장 추가
            strategy_dir = RAW_DIR / "strategy"
            strategy_dir.mkdir(parents=True, exist_ok=True)
            obs_path = strategy_dir / f"{session_dir.name}_onchain_signal.md"
            obs_path.write_text(signal_content, encoding="utf-8")
            files_created.append(str(obs_path))
            
        except Exception as e:
            err_msg = f"[{self.agent_name}] 온체인 신호 분석 실패: {e}"
            print(f"    [!] {err_msg}")
            errors.append(err_msg)
            
        elapsed = time.time() - start_time
        
        return AgentResult(
            agent_name=self.agent_name,
            success=len(errors) == 0,
            collected_count=len(files_created),
            files_created=files_created,
            elapsed_seconds=elapsed,
            errors=errors,
            payload={"onchain_signal": signal_content}
        )
