import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from agents.shared.protocols import AgentResult
from agents.shared.ollama_client import call_ollama
from agents.shared.config import RAW_DIR

class ChiefStrategyAnalyst:
    """5선 수석 전략 분석 및 종합 투자 전략서 기안 총괄 에이전트"""
    
    def __init__(self):
        self.agent_name = "ChiefStrategyAnalyst"
        
    def generate_strategy(
        self, 
        strategy_results: List[AgentResult], 
        financial_data: Optional[Dict[str, Any]], 
        session_dir: Path
    ) -> AgentResult:
        """
        하위 3개 에이전트(거시경제, 온체인, 리스크)의 전략 시그널 분석 결과물들을 취합/융합하여
        '서론 - 리스크 진단 - 종합 투자 전략 - 결론' 구조의 완성형 마스터 투자 전략 칼럼을 편찬하고,
        'strategy_column.md' 최종 기안서 파일로 세션에 저장합니다.
        """
        start_time = time.time()
        errors = []
        files_created = []
        strategy_column = ""
        
        # 하위 분석 결과 원고 추출
        macro_text = ""
        onchain_text = ""
        risk_text = ""
        
        for res in strategy_results:
            if res.agent_name == "MacroSignalAnalyst" and res.success:
                macro_text = res.payload.get("macro_signal", "")
            elif res.agent_name == "OnchainSignalAnalyst" and res.success:
                onchain_text = res.payload.get("onchain_signal", "")
            elif res.agent_name == "RiskAssessor" and res.success:
                risk_text = res.payload.get("risk_assessment", "")
                
        # 수집된 정량 기초 수치
        bok_rate = financial_data.get("bok_rate", 0.0) if financial_data else 0.0
        exchange_rate = financial_data.get("exchange_rate", 0.0) if financial_data else 0.0
        btc_krw = financial_data.get("btc_krw", 0.0) if financial_data else 0.0
        kimchi_premium = financial_data.get("kimchi_premium", 0.0) if financial_data else 0.0
        
        system_prompt = (
            "당신은 글로벌 최상위 금융투자은행(IB)의 자산 투자 최상위 전략 총괄이자 수석 전략 분석가입니다. "
            "하위 분석 부서가 작성한 3가지 핵심 원고(거시경제 시그널, 크립토 온체인 신호, 계량적 리스크 종합 진단)를 완벽히 이해하고, "
            "이들을 유기적으로 결합하여 품격 있고 논리정연한 완성형 마스터 투자 전략 기안서(Strategy Column)를 한국어로 기안합니다. "
            "반드시 '서론 - 리스크 진단 - 종합 투자 전략 - 결론'의 4단계 대분류 구조를 엄격히 지켜 윤문하십시오."
        )
        
        user_prompt = (
            f"[실시간 주요 정량 금융 지표]\n"
            f"- 기준금리: {bok_rate:.2f}% | 환율: {exchange_rate:,.2f}원\n"
            f"- 비트코인: {btc_krw:,.0f}원 | 김치 프리미엄: {kimchi_premium:+.2f}%\n\n"
            f"[하위 부서별 시그널/분석 원고]\n"
            f"1. 거시경제 신호 분석 원고:\n{macro_text}\n\n"
            f"2. 크립토 온체인 수급 신호 원고:\n{onchain_text}\n\n"
            f"3. 종합 위기/리스크 계량 진단 원고:\n{risk_text}\n\n"
            "위의 지표들과 개별 분석 원고를 활용하여, 각 파트가 서로 유기적인 인과관계로 엮인 하나의 통합된 금융경제 투자 전략 칼럼을 편찬해 주십시오. "
            "각 지표들의 독립적 나열을 엄격히 배제하고, 전체적인 인과관계가 흘러가도록 윤문하여 마크다운으로 최종 작성해 주십시오."
        )
        
        try:
            # LLM 호출
            strategy_column = call_ollama(user_prompt, system_prompt)
            if not strategy_column:
                raise ValueError("Ollama 모델로부터 응답을 받지 못했거나 빈 응답이 반환되었습니다.")
                
            # 파일 영속화 저장
            file_path = session_dir / "strategy_column.md"
            file_path.write_text(strategy_column, encoding="utf-8")
            files_created.append(str(file_path))
            
            # Obsidian Vault raw/strategy/ 동시 저장 추가
            strategy_dir = RAW_DIR / "strategy"
            strategy_dir.mkdir(parents=True, exist_ok=True)
            obs_path = strategy_dir / f"{session_dir.name}_strategy_column.md"
            obs_path.write_text(strategy_column, encoding="utf-8")
            files_created.append(str(obs_path))
            
        except Exception as e:
            err_msg = f"[{self.agent_name}] 최종 종합 투자 전략 도출 실패: {e}"
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
            payload={"strategy_column": strategy_column}
        )
