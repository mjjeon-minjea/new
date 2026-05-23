import time
from pathlib import Path
from typing import Dict, Any, Optional

from agents.shared.protocols import AgentResult
from agents.shared.ollama_client import call_ollama

class MacroSignalAnalyst:
    """5선 글로벌 거시 신호 분석가 에이전트"""
    
    def __init__(self):
        self.agent_name = "MacroSignalAnalyst"
        
    def analyze(self, financial_data: Optional[Dict[str, Any]], session_dir: Path) -> AgentResult:
        """
        0선 금융 지표 데이터를 수신하여 금리/환율 거시 시그널을 심층 분석하고,
        'macro_signal.md' 초안 보고서를 작성하여 반환합니다.
        """
        start_time = time.time()
        errors = []
        files_created = []
        signal_content = ""
        
        # 지표 정보 포맷팅
        bok_rate = financial_data.get("bok_rate", 0.0) if financial_data else 0.0
        exchange_rate = financial_data.get("exchange_rate", 0.0) if financial_data else 0.0
        
        system_prompt = (
            "당신은 글로벌 1위 투자은행의 수석 매크로 이코노미스트이자 거시 신호 분석가입니다. "
            "주어진 금융 지표(기준금리, 환율 등)와 변동성을 분석하여 단기/중기 거시 금융 리스크 시그널을 한국어로 도출합니다. "
            "객관적인 통계에 기반하여 감정을 배제하고 논리적으로 서술하십시오."
        )
        
        user_prompt = (
            f"[실시간 금융 주요 지표]\n"
            f"- 한국 기준금리 (BOK Rate): {bok_rate:.2f}%\n"
            f"- 원/달러 환율 (USD/KRW): {exchange_rate:,.2f}원\n\n"
            "위 지표들을 분석하여 거시경제 관점에서 포착되는 긍정적/부정적 시그널을 해부하고, "
            "종합 거시 리스크에 대한 간결하고 임팩트 있는 금융 진단을 마크다운 포맷으로 작성해 주십시오."
        )
        
        try:
            # LLM 호출
            signal_content = call_ollama(user_prompt, system_prompt)
            if not signal_content:
                raise ValueError("Ollama 모델로부터 응답을 받지 못했거나 빈 응답이 반환되었습니다.")
                
            # 파일 영속화 저장
            file_path = session_dir / "macro_signal.md"
            file_path.write_text(signal_content, encoding="utf-8")
            files_created.append(str(file_path))
            
        except Exception as e:
            err_msg = f"[{self.agent_name}] 거시 신호 분석 실패: {e}"
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
            payload={"macro_signal": signal_content}
        )
