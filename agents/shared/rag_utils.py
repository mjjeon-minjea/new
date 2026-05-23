# agents/shared/rag_utils.py
from pathlib import Path
from agents.shared.config import ROOT_DIR, DECISIONS_PATH

def load_rag_context(agent_dir: Path) -> str:
    """
    R4 설계 규칙에 따라 RAG 모드를 읽고, 5대 메모리 위계 순차 RAG 텍스트를 로드/결합하여 반환합니다.
    """
    rag_file = agent_dir / "rag_mode.txt"
    rag_mode = "self-rag"  # 설정 파일 부재 시 기본값
    
    if rag_file.exists():
        with open(rag_file, "r", encoding="utf-8") as rf:
            rag_mode = rf.read().strip().lower()
            
    if rag_mode == "off":
        return ""
        
    context_parts = []
    
    # 1단계: decisions.md (1순위 - 최고 신뢰 의사결정)
    dec_path = DECISIONS_PATH
    if dec_path.exists():
        with open(dec_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                context_parts.append(f"### [의사결정 이력 (1순위)]\n{content}\n")
            
    # 2단계: identity.md (2순위 - 기업 가치관 및 정체성)
    id_path = ROOT_DIR / "_company" / "_shared" / "identity.md"
    if id_path.exists():
        with open(id_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                context_parts.append(f"### [비서 정체성 및 핵심가치 (2순위)]\n{content}\n")
            
    # 3단계: goals.md (3순위 - 기업 대목표)
    goal_path = ROOT_DIR / "_company" / "_shared" / "goals.md"
    if goal_path.exists():
        with open(goal_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                context_parts.append(f"### [공동의 대목표 (3순위)]\n{content}\n")
            
    # 4단계: 에이전트 개별 memory.md / goal.md (4순위 - 에이전트 격리 메모리 및 업무 미션)
    agent_mem = agent_dir / "memory.md"
    if agent_mem.exists():
        with open(agent_mem, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                context_parts.append(f"### [에이전트 고유 실행 기억 (4순위)]\n{content}\n")
            
    agent_goal = agent_dir / "goal.md"
    if agent_goal.exists():
        with open(agent_goal, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                context_parts.append(f"### [에이전트 개별 전담 임무 (4순위)]\n{content}\n")
            
    return "\n".join(context_parts)
