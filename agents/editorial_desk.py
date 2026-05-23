# agents/editorial_desk.py
import time
from pathlib import Path
from typing import List, Optional
from agents.shared.protocols import AgentResult
from agents.shared.ollama_client import call_ollama

# ─── 페르소나 시스템 프롬프트 ───────────────────────────────────────────────────

_REDTEAM_SYSTEM = (
    "당신은 20년 경력의 냉혹한 팩트체커 레드팀 논설위원입니다. "
    "제출된 원고에서 논리적 인과관계 비약, 수치 불일치, 거시경제 내적 모순을 "
    "기자명별로 명확하게 구분하여 지적합니다. 칭찬은 일절 없으며, 구체적 수치와 "
    "논리로 근거를 제시합니다. 한국어로 답변합니다."
)

_CORRECTION_SYSTEM = (
    "당신은 레드팀의 지적을 전달받은 전문 경제 기자입니다. "
    "지적된 논리 오류와 수치 모순을 수정하고, 팩트를 보강하여 원고를 개선합니다. "
    "레드팀이 지적하지 않은 부분은 원문을 최대한 유지합니다. 한국어로 답변합니다."
)

_EDITOR_SYSTEM = (
    "당신은 최고급 금융경제 종합지의 편집장입니다. "
    "국내경제, 글로벌매크로, 비트코인 3개 분야의 수정 원고를 "
    "서론-본론(분야 간 인과 결합)-전망 구조의 하나의 유기적인 종합 사설로 "
    "편찬합니다. 각 분야가 서로 독립적으로 나열되지 않고 인과관계로 연결되도록 "
    "윤문합니다. 한국어로 작성합니다."
)

# ─── 헬퍼 ───────────────────────────────────────────────────────────────────────

def _read_reporter_files(rep_res: AgentResult, max_files: int = 3, chars_per_file: int = 2500) -> str:
    """
    AgentResult.files_created에서 최신 N개 파일을 읽어 합본 텍스트로 반환합니다.
    파일당 글자 수를 제한하여 Ollama 프롬프트가 과도하게 길어지는 것을 방지합니다.
    files_created가 비어 있으면 빈 문자열을 반환합니다 (리포터 수집 실패 케이스).
    """
    contents = []
    # 최신 파일 우선으로 취하기 위해 역순으로 슬라이싱
    target_files = rep_res.files_created[-max_files:]
    for f_path_str in target_files:
        try:
            text = Path(f_path_str).read_text(encoding="utf-8")
            contents.append(f"--- {Path(f_path_str).name} ---\n{text[:chars_per_file]}")
        except Exception as e:
            print(f"[!] [EditorialDesk] 리포터 파일 읽기 실패: {f_path_str} — {e}")
    return "\n\n".join(contents)


# ─── 메인 진입점 ────────────────────────────────────────────────────────────────

def run_editorial_board(
    reporter_results: List[AgentResult],
    financial_data: dict,
    session_dir: Path,
) -> Optional[AgentResult]:
    """
    [AI 합동 언론 데스크 3단계 파이프라인]
    1단계 — 레드팀 교차 감사: 3대 기자 원고 합본을 레드팀 페르소나로 비판
    2단계 — 기자단 수정:      각 기자 원고 + 레드팀 지적 → 2차 수정본 생성
    3단계 — 편집장 종합:      3개 수정본 → 하나의 종합 사설 칼럼

    반환: AgentResult (성공 시 payload["final_column"]에 최종 사설 저장)
          Ollama 완전 장애 시 None 반환 (chief_agent.py에서 None 체크 필수)
    """
    start_time = time.time()
    minutes_lines = [
        f"# AI 합동 언론 데스크 편집 회의록\n",
        f"**세션**: `{session_dir.name}`\n\n---\n\n",
    ]

    # ── 1단계: 각 리포터의 실제 파일 읽기 ──────────────────────────────────────
    print("[*] [EditorialDesk] 리포터 원고 파일 수집 중...")
    raw_texts: dict[str, str] = {}
    for rep_res in reporter_results:
        content = _read_reporter_files(rep_res)
        raw_texts[rep_res.agent_name] = content
        status = f"{len(content)}자 수집" if content else "원고 없음 (리포터 실패)"
        print(f"[*] [EditorialDesk]   └ {rep_res.agent_name}: {status}")

    # 모든 리포터가 실패한 경우 조기 종료
    if not any(raw_texts.values()):
        print("[!] [EditorialDesk] 모든 리포터의 파일이 비어 있어 편집 데스크 세션을 중단합니다.")
        return None

    # ── 2단계: 레드팀 교차 감사 ─────────────────────────────────────────────────
    print("[*] [EditorialDesk] 레드팀 교차 감사 개시...")
    all_raw_combined = "\n\n".join(
        [f"## [{name} 1차 원고]\n{text}" for name, text in raw_texts.items() if text]
    )
    redteam_prompt = (
        f"아래는 금융경제 3대 분야 기자들이 제출한 1차 취재 원고입니다.\n\n"
        f"{all_raw_combined}\n\n"
        "각 기자별로 다음 항목을 반드시 짚어 감사 지침을 발부하십시오:\n"
        "① 논리적 인과관계 비약 (예: A가 원인이라고 주장하나 B가 원인인 경우)\n"
        "② 수치 불일치 (예: 금리 인하 기대감과 금리 인상론의 동시 서술)\n"
        "③ 거시경제 내적 모순 (예: 달러 강세와 비트코인 상승을 동시에 호재로 기술)\n"
        "기자명을 명시하여 각각 구분하십시오."
    )

    redteam_critique = call_ollama(redteam_prompt, _REDTEAM_SYSTEM)

    if not redteam_critique:
        print("[!] [EditorialDesk] 레드팀 Ollama 호출 실패. 편집 데스크를 중단합니다.")
        return None

    minutes_lines.append(f"## 1단계: 레드팀 감사 지침\n\n{redteam_critique}\n\n---\n\n")
    print("[+] [EditorialDesk] 레드팀 감사 지침 발부 완료.")

    # ── 3단계: 기자단 수정 루프 ─────────────────────────────────────────────────
    corrected_texts: dict[str, str] = {}
    for rep_res in reporter_results:
        original = raw_texts.get(rep_res.agent_name, "")
        if not original:
            corrected_texts[rep_res.agent_name] = ""
            continue

        print(f"[*] [EditorialDesk] {rep_res.agent_name} 수정 원고 생성 중...")
        correction_prompt = (
            f"[레드팀 감사 지침 전문]\n{redteam_critique}\n\n"
            f"[{rep_res.agent_name} 1차 원고]\n{original}\n\n"
            "위 레드팀의 지적 사항 중 본인의 원고에 해당하는 부분을 수정하십시오. "
            "수치적 근거를 보완하고, 논리적 일관성을 회복하여 2차 수정 원고를 제출하십시오."
        )
        corrected = call_ollama(correction_prompt, _CORRECTION_SYSTEM)
        corrected_texts[rep_res.agent_name] = corrected or original  # Ollama 실패 시 원본 유지
        print(f"[+] [EditorialDesk]   └ {rep_res.agent_name} 수정 완료.")
        minutes_lines.append(
            f"## 2단계: {rep_res.agent_name} 수정 원고\n\n{corrected_texts[rep_res.agent_name]}\n\n---\n\n"
        )

    # ── 4단계: 편집장 최종 종합 사설 ────────────────────────────────────────────
    print("[*] [EditorialDesk] 편집장 최종 종합 사설 작성 중...")
    all_corrected = "\n\n".join(
        [f"## [{name} 최종 수정본]\n{text}" for name, text in corrected_texts.items() if text]
    )
    editor_prompt = (
        f"아래는 레드팀의 감사를 거쳐 수정된 3개 분야의 최종 원고입니다.\n\n"
        f"{all_corrected}\n\n"
        "서론-본론(분야 간 유기적 인과 결합)-전망 구조로 "
        "하나의 통합된 금융경제 종합 사설을 편찬하십시오. "
        "각 분야를 단순 나열하지 말고 상호 인과관계로 연결하십시오."
    )

    final_column = call_ollama(editor_prompt, _EDITOR_SYSTEM)

    if final_column:
        minutes_lines.append(f"## 3단계: 편집장 최종 종합 사설\n\n{final_column}\n")
        print("[+] [EditorialDesk] 편집장 최종 종합 사설 완성.")
    else:
        print("[!] [EditorialDesk] 편집장 Ollama 호출 실패. 수정 원고 합본으로 대체합니다.")
        final_column = all_corrected  # 폴백: 수정 원고 합본 반환

    # ── 5단계: 회의록 저장 ──────────────────────────────────────────────────────
    minutes_content = "".join(minutes_lines)
    files_created = []

    try:
        minutes_path = session_dir / "editorial_minutes.md"
        minutes_path.write_text(minutes_content, encoding="utf-8")
        files_created.append(str(minutes_path))
        print(f"[+] [EditorialDesk] 편집 회의록 저장 완료: {minutes_path.name}")
    except Exception as e:
        print(f"[!] [EditorialDesk] 회의록 저장 실패: {e}")

    elapsed = time.time() - start_time
    print(f"[+] [EditorialDesk] 전체 편집 데스크 세션 완료 (소요: {elapsed:.1f}초).")

    return AgentResult(
        agent_name="EditorialDesk",
        success=True,
        collected_count=len([t for t in corrected_texts.values() if t]),
        files_created=files_created,
        elapsed_seconds=elapsed,
        payload={"final_column": final_column},
    )
