import time
from pathlib import Path
from typing import Dict, Any, Optional

from agents.shared.protocols import AgentResult
from agents.shared.ollama_client import call_ollama

class RiskAssessor:
    """5선 금융시장 종합 변동성 및 크립토 리스크 계량 채점 평가 에이전트"""
    
    def __init__(self):
        self.agent_name = "RiskAssessor"
        
    def assess(self, financial_data: Optional[Dict[str, Any]], session_dir: Path) -> AgentResult:
        """
        0선 금융 지표와 변동성을 취합 분석하여 시장 전체의 위험도를 1등급(매우 안전)~10등급(위기 붕괴)으로 채점하고,
        'risk_assessment.md' 진단 보고서를 작성하여 반환합니다.
        """
        start_time = time.time()
        errors = []
        files_created = []
        assessment_content = ""
        
        # 지표 정보 포맷팅
        btc_krw = financial_data.get("btc_krw", 0.0) if financial_data else 0.0
        btc_krw_change = financial_data.get("btc_krw_change", 0.0) if financial_data else 0.0
        kimchi_premium = financial_data.get("kimchi_premium", 0.0) if financial_data else 0.0
        exchange_rate = financial_data.get("exchange_rate", 0.0) if financial_data else 0.0
        bok_rate = financial_data.get("bok_rate", 0.0) if financial_data else 0.0
        
        system_prompt = (
            "당신은 20년 금융감독기구 수석 감사관 경력의 날카롭고 빈틈없는 금융 리스크 채점관이자 자산 위기 관리자입니다. "
            "주어진 금융 지표(금리, 환율, 비트코인 가격, 김프 등)의 누적 변동성을 보수적 시선으로 평가하여, "
            "현재 자산 시장의 위험 등급을 1등급(극도로 안전)부터 10등급(위험 포화 상태/패닉 붕괴 수준) 중 하나로 채점하고 한국어로 서술합니다. "
            "낙관론을 일절 배제하고 손실 방어 관점의 리스크 취약점을 매섭고 직관적으로 지적하십시오."
        )
        
        user_prompt = (
            f"[실시간 종합 금융/크립토 지표]\n"
            f"- 한국 기준금리 (BOK Rate): {bok_rate:.2f}%\n"
            f"- 원/달러 환율 (USD/KRW): {exchange_rate:,.2f}원\n"
            f"- 비트코인 원화 시세 (Upbit): {btc_krw:,.0f}원 ({btc_krw_change:+.2f}%)\n"
            f"- 김치 프리미엄 (Premium): {kimchi_premium:+.2f}%\n\n"
            "위 지표들을 분석하여 현재 자산 시장의 종합 리스크 등급(1~10등급)을 결정해 주십시오. "
            "등급 결정의 근거(스프레드 과열, 괴리 변동성, 꼬리 리스크 등)와 취약 요인별 진단 내용을 마크다운 포맷으로 날카롭게 작성해 주십시오."
        )
        
        try:
            # LLM 호출
            assessment_content = call_ollama(user_prompt, system_prompt)
            if not assessment_content:
                raise ValueError("Ollama 모델로부터 응답을 받지 못했거나 빈 응답이 반환되었습니다.")
                
            # 파일 영속화 저장
            file_path = session_dir / "risk_assessment.md"
            file_path.write_text(assessment_content, encoding="utf-8")
            files_created.append(str(file_path))
            
        except Exception as e:
            err_msg = f"[{self.agent_name}] 리스크 계량 채점 실패: {e}"
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
            payload={"risk_assessment": assessment_content}
        )
