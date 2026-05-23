from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class AgentResult:
    """에이전트 실행 및 릴레이 소통 프로토콜 정의 객체"""
    agent_name: str                                  # 에이전트 식별명
    success: bool                                    # 실행 완료 성공 여부
    collected_count: int = 0                          # 수집/처리된 아이템 개수
    files_created: List[str] = field(default_factory=list)  # 갱신/생성된 파일 경로 리스트
    errors: List[str] = field(default_factory=list)          # 발생한 에러/경고 목록
    elapsed_seconds: float = 0.0                      # 단계 실행 소요 초
    payload: Dict[str, Any] = field(default_factory=dict)   # 인메모리 반환/공급용 딕셔너리
