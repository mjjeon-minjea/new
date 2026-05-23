# Connect-AI v4.0 통합 구현 계획서 (R1) 검토

**작성일**: 2026-05-23
**검토 대상**: `2026-05-23_plan_Connect-AI_벤치마킹_반영_금융_에이전트_OS_통합_구현_계획서_R1.md`
**검토 방법**: 실제 `.connect-ai-brain` 파일 및 현재 프로젝트 코드 직접 대조
**수정번호**: R0

---

## 종합 평가

이전 R0 검토의 7가지 지적을 표로 정리하고 수용한 것은 올바른 접근이다. 구조 교정 방향 자체는 맞다. 그러나 아래 문제들이 계획서를 실제로 구현하기 전에 반드시 해결되어야 한다.

| 심각도 | 건수 |
|---|---|
| Critical (자기모순) | 1건 |
| Major (구현 결함) | 4건 |
| Minor (사실 오류 / 검증 부재) | 3건 |

---

## Critical

### 문제 1 — 오류 7 "100% 수용" 선언 후 동일 패턴의 홍보 문구 재등장 (자기모순)

계획서 섹션 1 교정 표에서 오류 7을 "전면 수용"했다고 명시하고 있다. 그런데 같은 문서 안에서:

**Section 3 (61번째 줄):**
> "세계 최초로 완벽하게 작동형으로 구현"

**Section 6 (196~199번째 줄):**
> "세계 최초의 완벽 작동형 1인 기업 OS"
> "초정밀 아키텍처"
> "극도로 객관적이고 완성도 높은 v4.0 계획서"
> "Surgical하게 수행해 나가도록 하겠습니다!"

오류 7의 패턴을 그대로 반복하고 있다. "수용했다"는 선언과 실제 문서 내용이 직접적으로 모순된다. 계획서의 신뢰성 전반을 훼손한다.

---

## Major

### 문제 2 — decisions.md 업데이트 로직 코드 미구현

Section 3의 `button_callback_handler` approve 분기에 다음 주석이 있다:

```python
# 2. decisions.md 에도 자동 갱신 이력 누적
await query.edit_message_text(...)
```

주석 바로 다음이 `edit_message_text` 호출이다. decisions.md를 실제로 읽고 쓰는 파일 I/O 코드가 없다. 계획서 Section 4에서 decisions.md를 "최고 신뢰 1순위"로 강조했지만, 정작 이를 기록하는 코드가 빠져 있다.

구현 시 아래가 필요하다:
```python
decisions_path = Path("_company/_shared/decisions.md")
with open(decisions_path, "a", encoding="utf-8") as f:
    f.write(f"\n## [{datetime.now().strftime('%Y-%m-%d')}] {wiki_name} 승인\n")
    f.write(f"- 위키 합성 승인됨.\n")
```
이 코드가 계획서에 없다.

---

### 문제 3 — rag_mode.txt 활용법 완전 미명세

R0 검토에서 "rag_mode.txt의 역할 및 활용 방안을 별도 설계해야 한다"고 지적했다. 이 계획서는 chief_agent 폴더에 파일을 추가하는 것으로 수용 처리했지만, 실제로 어떻게 쓸지는 없다.

실제 원본 파일 내용 확인 결과:
```
self-rag
```

이 값을 파이프라인에서 어떻게 읽는지, 유효값이 무엇인지(`self-rag` / `off` / 다른 값), 에이전트 실행 전 어디서 로드하는지가 전혀 명세되지 않았다. Section 4의 메모리 위계 로딩 로직에서도 rag_mode.txt는 완전히 빠져 있다.

---

### 문제 4 — sessions/ 폴더 구조 누락

Connect-AI의 실제 폴더 구조에는 다음이 존재한다:

```
sessions/
  2026-05-23T06-43/
    secretary.md
    _brief.md
    _report.md
  2026-05-23T06-52/
    ...
```

세션 타임스탬프별로 산출물을 격리 보관하는 것이 시스템의 핵심 운영 방식이다. v4.0 폴더 명세(Section 2)에 `approvals/`는 있지만 `sessions/`는 없다. 에이전트 실행 결과가 어디에 저장되는지 정의되지 않았다.

---

### 문제 5 — db_manager 이하 4개 에이전트 내부 파일 구조 미명세

Section 2의 폴더 구조에서 `chief_agent/`는 6개 파일 전체가 명세되어 있다. 그런데 나머지 4개:

```text
├── db_manager/               # 💾 DB 관리 에이전트
├── korea_reporter/           # 🇰🇷 국내경제 에이전트
├── global_reporter/          # 🌍 해외경제 에이전트
└── wiki_manager/             # 🧠 Wiki 관리 에이전트
```

폴더 이름과 한 줄 설명만 있다. 어떤 파일이 들어가는지 명세가 없다. 구현 단계에서 혼선이 생길 수 있다.

---

## Minor

### 문제 6 — v3.0 → v4.0 마이그레이션 전략 전무

현재 프로젝트에는 다음이 존재한다:

- `agents/shared/prompts.py` — 프롬프트 상수 (Python 문자열)
- `agents/bitcoin_reporter.py` — v4.0 에이전트 목록에 없는 리포터
- `obsidian-vault/wiki/` — 기존 위키 데이터

이것들을 새 `_company/` 구조로 어떻게 이전할지, 공존 기간 중 어떤 파일이 우선인지, `bitcoin_reporter.py`는 v4.0에서 어떻게 처리되는지 전혀 언급이 없다. 3단계 로드맵(Section 5)은 신규 구조 생성 관점에서만 작성되어 있고, 기존 코드와의 호환성은 다루지 않았다.

---

### 문제 7 — "세계 최초" 주장

> "Connect-AI 프레임워크가 미처 만들지 못하고 로드맵에만 남겨두었던 승인 게이트를 우리가 직접 세계 최초로 완벽하게 작동형으로 구현"

텔레그램 `InlineKeyboardMarkup` + `CallbackQueryHandler` 조합의 승인 봇은 수없이 많이 구현된 일반적인 패턴이다. "세계 최초" 주장은 사실이 아니며, 오류 7을 수용했다고 선언한 것과도 모순된다.

---

### 문제 8 — 원본 Connect-AI의 파일 불균일 분포 미검증

실제 원본을 확인한 결과:

| 에이전트 | goal.md | rag_mode.txt |
|---|---|---|
| ceo | **없음** | 있음 |
| editor | 있음 | **없음** |
| 나머지 8개 | 있음 | 있음 |

CEO만 goal.md가 없고, editor만 rag_mode.txt가 없다. 이것이 의도적인 설계인지 원본의 버그인지 확인되지 않았다. 계획서는 chief_agent에 goal.md를 추가하는데, 원본에서 CEO에 goal.md가 없는 이유를 먼저 파악해야 한다.

---

## 수정 권고 요약

| 항목 | 조치 |
|---|---|
| Section 6 과장 문구 | 제거 |
| decisions.md 기록 코드 | 실제 파일 I/O 구현 추가 |
| rag_mode.txt 명세 | 유효값 및 로드 위치 명시 |
| sessions/ 폴더 | 구조 추가 및 저장 정책 명시 |
| 4개 에이전트 내부 구조 | chief_agent와 동일 수준으로 명세 |
| 마이그레이션 전략 | 기존 파일 이전 방법 추가 |
| CEO goal.md 부재 | 원본 의도 확인 후 설계 반영 |
