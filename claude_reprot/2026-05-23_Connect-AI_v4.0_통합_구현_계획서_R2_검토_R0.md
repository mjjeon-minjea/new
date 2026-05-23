# Connect-AI v4.0 통합 구현 계획서 (R2) 검토

**작성일**: 2026-05-23
**검토 대상**: `2026-05-23_plan_Connect-AI_v4.0_통합_구현_계획서_R2.md`
**검토 방법**: 실제 `agents/shared/config.py` 및 프로젝트 코드 직접 대조
**수정번호**: R0

---

## 종합 평가

R1 대비 대폭 개선됐다. 홍보 문구 제거, decisions.md I/O 구현, rag_mode.txt 명세, sessions/ 추가, 마이그레이션 전략, CEO goal.md 부재 분석 등 6개 주요 지적이 실질적으로 반영됐다.

그러나 코드를 실제 실행하면 **런타임 ImportError가 발생**한다. 이 문제 1개가 현재 구현 착수를 막는 블로커다. 나머지는 Minor 수준이다.

| 심각도 | 건수 |
|---|---|
| Major (런타임 블로커) | 1건 |
| Major (설계 결함) | 2건 |
| Minor (코드 품질 / 문서 오류) | 3건 |

---

## Major

### 문제 1 — `DECISIONS_PATH` 미정의: 런타임 ImportError 발생 (블로커)

Section 3 코드의 import 구문:

```python
from agents.shared.config import WIKI_DIR, DECISIONS_PATH
```

실제 `agents/shared/config.py`를 확인한 결과:

```python
# agents/shared/config.py (현재 파일)
VAULT_PATH = ROOT_DIR / vault_path_str
RAW_DIR    = VAULT_PATH / "raw"
WIKI_DIR   = VAULT_PATH / "wiki"          # ← 존재함
# DECISIONS_PATH 는 없음
```

`WIKI_DIR`은 존재하지만 `DECISIONS_PATH`는 정의되어 있지 않다. 이 상태로 `telegram_bot.py`를 가동하면 봇이 시작할 때 `ImportError: cannot import name 'DECISIONS_PATH'`가 발생하며 즉시 종료된다.

Section 6의 마이그레이션 전략에서 "config.py 내의 WIKI_DIR와 RAW_DIR 경로 상수를 매핑"만 언급하고 `DECISIONS_PATH` 추가는 명시하지 않았다.

**필요한 조치**: `agents/shared/config.py`에 아래 한 줄 추가가 명세되어야 한다.

```python
DECISIONS_PATH = ROOT_DIR / "_company" / "_shared" / "decisions.md"
```

---

### 문제 2 — `load_rag_context()` 내 하드코딩 상대경로: CWD 의존 취약점

Section 4의 `load_rag_context()` 함수:

```python
dec_path  = Path("_company/_shared/decisions.md")   # 상대경로
id_path   = Path("_company/_shared/identity.md")    # 상대경로
goal_path = Path("_company/_shared/goals.md")       # 상대경로
```

`config.py`의 `ROOT_DIR`은 `Path(os.getcwd()).resolve()`로 **프로세스 실행 위치 기준**으로 결정된다. 봇이 프로젝트 루트가 아닌 다른 경로에서 실행되면 (예: 스케줄러, systemd 서비스) 이 상대경로들은 잘못된 위치를 가리킨다.

`button_callback_handler`의 `draft_path`도 동일한 문제다:

```python
draft_path = Path(f"_company/approvals/pending/{wiki_name}_draft.md")  # 상대경로
```

**필요한 조치**: `config.py`의 `ROOT_DIR`을 기준으로 절대경로를 사용해야 한다.

```python
# Section 4 수정안
from agents.shared.config import ROOT_DIR

dec_path  = ROOT_DIR / "_company" / "_shared" / "decisions.md"
id_path   = ROOT_DIR / "_company" / "_shared" / "identity.md"
goal_path = ROOT_DIR / "_company" / "_shared" / "goals.md"

# Section 3 수정안
draft_path   = ROOT_DIR / "_company" / "approvals" / "pending" / f"{wiki_name}_draft.md"
official_path = Path(WIKI_DIR) / f"{wiki_name}.md"
```

---

### 문제 3 — `load_rag_context()` 호출 위치 미명세

Section 4에서 함수 구현 사양은 정의됐지만, 이 함수가 실제 파이프라인 어디서 호출되는지 명세가 없다.

- 어느 파일에 위치하는가? (신규 파일? 기존 `base_reporter.py`?)
- 반환된 컨텍스트 문자열은 어디에 주입되는가? (`WIKI_COMPOUND_SYSTEM_PROMPT_TEMPLATE`의 `{memory_context}` 슬롯인가?)
- `chief_agent.py`의 릴레이 진입점에서 호출하는가, 아니면 각 에이전트가 개별 호출하는가?

구현자가 코드를 어디에 붙여야 할지 알 수 없다. 함수 정의만으로는 파이프라인에 연결되지 않는다.

---

## Minor

### 문제 4 — `import re` 미사용

Section 3 `button_callback_handler` 상단:

```python
import re
```

함수 내부 어디에서도 `re` 모듈을 사용하지 않는다. 실행에는 문제없지만 코드 품질 기준 미달이다.

---

### 문제 5 — Section 8 검증 시나리오의 경로 오타

Section 8 수동 검증 시나리오 (279번째 줄):

> `_company/shared/decisions.md` 파일이 자동 업데이트되어...

코드와 폴더 명세 전체에서 `_company/_shared/decisions.md` (언더스코어 포함)로 일관되게 쓰고 있는데, 이 항목만 `_company/shared/` (언더스코어 없음)로 잘못 기재됐다. 검증 단계에서 틀린 경로를 확인하게 된다.

---

### 문제 6 — `reject` 분기에 파일 부재 시 피드백 없음

Section 3의 reject 처리:

```python
elif action == "reject":
    if draft_path.exists():
        try:
            draft_path.unlink()
            ...
        except Exception as e:
            ...
    # else 없음
```

이미 반려된 초안을 다시 반려하거나, 타임아웃 후 버튼을 누를 경우 파일이 없는 상태에서 `else` 분기가 없어 봇 메시지가 변경되지 않고 사용자는 아무 피드백을 받지 못한다. approve 분기에는 else 처리가 있는데 reject에는 없다. 일관성 문제다.

---

## R1 → R2 개선 확인 항목

아래 항목들은 이번 R2에서 정상적으로 반영됐다.

| R1 지적 사항 | R2 반영 여부 |
|---|---|
| 홍보 문구 및 "세계 최초" 소거 | 반영됨 |
| decisions.md 파일 I/O 코드 구현 | 반영됨 |
| rag_mode.txt 유효값 및 연동 명세 | 반영됨 |
| sessions/ 폴더 구조 추가 | 반영됨 |
| 하위 에이전트 파일 구조 명세 | 반영됨 |
| v3.0 → v4.0 마이그레이션 전략 | 반영됨 |
| bitcoin_reporter 공식 편입 | 반영됨 |
| CEO goal.md 부재 원인 분석 | 반영됨 |

---

## 구현 착수 전 필수 조치 요약

1. `agents/shared/config.py`에 `DECISIONS_PATH = ROOT_DIR / "_company" / "_shared" / "decisions.md"` 추가
2. `load_rag_context()` 및 `button_callback_handler` 내 상대경로를 `ROOT_DIR` 기반 절대경로로 교체
3. `load_rag_context()` 호출 위치 및 반환값 주입 위치를 파이프라인 코드 기준으로 명세
4. Section 8의 `_company/shared/` 오타를 `_company/_shared/`로 수정
5. `import re` 제거
6. `reject` 분기에 `else` 핸들러 추가
