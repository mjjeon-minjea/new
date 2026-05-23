# Connect-AI v4.0 통합 구현 계획서 (R3) 검토

**작성일**: 2026-05-23
**검토 대상**: `2026-05-23_plan_Connect-AI_v4.0_통합_구현_계획서_R3.md`
**검토 방법**: 실제 `wiki_manager.py`, `file_utils.py`, `config.py` 코드 직접 대조
**수정번호**: R0

---

## 종합 평가

R3는 이전 검토들의 모든 블로커를 해소했다. `DECISIONS_PATH` ImportError, 상대경로 취약점, `load_rag_context()` 호출 위치 미명세, `reject` else 핸들러 누락, `import re` 미사용 — 5개 지적이 모두 코드 수준에서 반영됐다.

**현 상태: 구현 착수 가능.** 다만 아래 3개 지점은 계획서가 "코드 없이 설명만" 있어서 실제 구현 시 구현자가 스스로 판단해야 한다. 블로커는 아니지만 완성도 차이다.

| 심각도 | 건수 | 비고 |
|---|---|---|
| 블로커 | 0건 | R2 대비 해소 완료 |
| 중간 (구현 갭) | 3건 | 설명은 있으나 코드 없음 |
| 경미 | 2건 | 코드 품질 / 설계 정합성 |

---

## 중간 — 구현 갭 (코드 없는 설명)

### 갭 1 — `wiki_manager.py`에 `load_rag_context()` 삽입 코드 미제시

Section 4.3에서 "wiki_manager.py의 `run()` 혹은 `process_compounding()` 진입 단계에 호출한다"고 설명했지만, 실제 수정 코드가 없다.

실제 `wiki_manager.py`의 진입점을 확인하면 `run_compounding()` 메서드가 존재하며, 현재 import 구조는 다음과 같다:

```python
# 현재 wiki_manager.py (7~13번째 줄)
from agents.shared.config import WIKI_DIR, RAW_DIR, OLLAMA_MODEL
from agents.shared.prompts import (
    WIKI_COMPOUND_SYSTEM_PROMPT_TEMPLATE, ...
)
```

`load_rag_context()`를 어느 줄 이후에 호출하고, 반환값을 어느 변수에 담아 어느 템플릿 슬롯에 바인딩하는지 코드로 제시되지 않았다. 구현자가 직접 판단해야 한다.

---

### 갭 2 — `sessions/` 디렉토리 생성 코드 미제시

Section 5는 R2와 동일하게 글머리표 설명으로만 구성되어 있다. `chief_agent.run_relay()` 어디에서 타임스탬프를 생성하고 디렉토리를 만들며 각 에이전트 결과를 어떻게 파일로 쓰는지 코드가 없다.

구현에 필요한 최소 코드 형태:
```python
timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M")
session_dir = ROOT_DIR / "_company" / "sessions" / timestamp
session_dir.mkdir(parents=True, exist_ok=True)
```
이 수준의 코드가 `chief_agent.py` 어느 위치에 들어가는지 명세가 필요하다.

---

### 갭 3 — `prompt.md` 동적 로드 코드 미제시

Section 6 Step 2는 "prompts.py 상수를 `prompt.md`로 이관하고 동적으로 로드하도록 패치한다"고 명시했지만, 로드 코드가 없다.

현재 `wiki_manager.py`는 `from agents.shared.prompts import WIKI_COMPOUND_SYSTEM_PROMPT_TEMPLATE`으로 Python 상수를 직접 참조한다. 이것을 파일 로드 방식으로 교체하는 코드 — 최소한 아래 형태라도 — 제시가 필요하다:

```python
prompt_path = ROOT_DIR / "_company" / "_agents" / "wiki_manager" / "prompt.md"
system_prompt = prompt_path.read_text(encoding="utf-8")
```

이 교체 방식이 명세 없으면 기존 `prompts.py` import를 언제 제거해야 하는지, 어디서 로드해야 하는지 구현자가 추정으로 작업하게 된다.

---

## 경미

### 경미 1 — `Path(DECISIONS_PATH)` 이중 래핑

Section 3 코드 140번째 줄:
```python
decisions_path = Path(DECISIONS_PATH)
```

`config.py`에 추가될 `DECISIONS_PATH`는 `ROOT_DIR / "_company" / "_shared" / "decisions.md"` 즉 이미 `Path` 객체다. `Path(Path(...))` 이중 래핑은 무해하지만 불필요하다. `decisions_path = DECISIONS_PATH`로 충분하다.

---

### 경미 2 — `load_rag_context()`를 `file_utils.py`에 배치하는 것은 설계 정합성 미흡

Section 4.3:
> `load_rag_context()`는 공통 모듈인 `agents/shared/file_utils.py` 내에 함수로 배치

`file_utils.py`의 실제 내용은 `write_file_safely()`와 `get_existing_urls()`로, 파일 I/O 유틸리티 모듈이다. `load_rag_context()`는 RAG 컨텍스트를 조합하는 프롬프트 빌더 함수이므로 `file_utils.py`가 아닌 별도 모듈(예: `agents/shared/rag_utils.py`)에 두는 것이 맞다. 지금 배치대로 가면 `file_utils.py`의 역할이 모호해진다.

---

## R2 → R3 개선 확인 항목

| R2 지적 사항 | R3 반영 여부 |
|---|---|
| `DECISIONS_PATH` 미정의 (ImportError) | 반영됨 |
| `load_rag_context()` 상대경로 → `ROOT_DIR` 절대경로 | 반영됨 |
| `load_rag_context()` 호출 위치 설명 추가 | 부분 반영 (설명은 있으나 코드 없음 → 갭 1) |
| `reject` 분기 else 핸들러 추가 | 반영됨 |
| `import re` 제거 | 반영됨 |
| Section 8 경로 오타 수정 | 반영됨 |

---

## 결론

R3는 구현 착수에 충분한 수준이다. 남은 3개 갭은 블로커가 아니라 "코드를 직접 짜야 하는 부분"이다. R1·R2처럼 실행 자체가 안 되는 문제가 아니다.

구현 순서를 제안하면:

1. `config.py`에 `DECISIONS_PATH` 추가 (한 줄)
2. `_company/` 폴더 구조 생성
3. `load_rag_context()` 함수를 `rag_utils.py`로 신설하여 배치
4. `wiki_manager.py`의 `run_compounding()` 진입부에 RAG 로드 삽입
5. 텔레그램 봇에 `button_callback_handler` 등록
6. `sessions/` 생성 로직을 `chief_agent.py`에 추가
