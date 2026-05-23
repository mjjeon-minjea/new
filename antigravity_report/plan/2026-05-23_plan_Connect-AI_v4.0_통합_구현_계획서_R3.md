# Connect-AI v4.0 통합 구현 계획서 (R3)

본 계획서는 사용자의 **"Connect-AI v4.0 통합 구현 계획서 (R2) 검토 R0"** 보고서에서 지적된 런타임 블로커(ImportError) 및 코드 설계상의 설계 결함, 마이너 경로 오타 등을 전적으로 보완하여 완성한 구현 계획서 v4.0 (R3)입니다. 

주관적인 형용사를 배제하고 런타임 오류 가능성이 없는 엄밀한 코드 명세와 팩트 중심으로 기술하였습니다.

---

## 1. 피드백 수용 및 교정 조치 명세 (R3 보완)

R2 검토 보고서(R0)의 지적 사항을 분석하고 아래와 같이 설계를 즉각 보완하였습니다.

| 번호 | 지적 사항 | 원인 및 사실 대조 결과 | R3 최종 교정 및 반영 조치 |
| :---: | :--- | :--- | :--- |
| **1** | **`DECISIONS_PATH` 미정의 (ImportError 블로커)** | 텔레그램 봇에서 `DECISIONS_PATH`를 임포트하여 사용하지만, 정작 `agents/shared/config.py`에 해당 상수가 미정의되어 봇 실행 즉시 ImportError가 발생함. | `agents/shared/config.py` 이행 계획에 **`DECISIONS_PATH = ROOT_DIR / "_company" / "_shared" / "decisions.md"` 선언을 명시적으로 편입**함. |
| **2** | **`load_rag_context()` 내 하드코딩 상대경로** | decisions.md, identity.md 등의 경로를 하드코딩된 상대경로(`Path("_company/...")`)로 구성하여 CWD(작업 디렉토리) 실행 위치에 따라 경로를 잃는 결함 존재. | RAG 로더 및 콜백 핸들러 내부의 모든 상대경로를 **`ROOT_DIR` 기반 절대경로(`ROOT_DIR / "_company" / ...`)로 일괄 변경**하여 안정성을 보장함. |
| **3** | **`load_rag_context()` 호출 위치 미명세** | RAG 텍스트 합성용 유틸리티 함수만 정의되고, 실제 파이프라인(예: `wiki_manager.py`)에서 어떤 프롬프트 템플릿의 슬롯에 주입되는지 정의되지 않음. | `wiki_manager.py` 실행 시점에 **해당 함수를 호출하고, 반환된 RAG 컨텍스트를 시스템 프롬프트 템플릿 하단의 `{rag_context}` 슬롯에 동적 바인딩하는 연동 흐름을 정밀 명세**함. |
| **4** | **`reject` 분기 파일 부재 시 피드백 부재** | `button_callback_handler` 내 approve 분기에는 `else` 처리가 있으나 reject 분기에는 대기 파일 부재 시 `else` 피드백 메시지가 생략되어 작동 일관성이 결여됨. | reject 분기에도 `else` 핸들러를 추가하여, 대기 초안 파일이 존재하지 않는 경우 **"⚠️ 오류: 대기 중인 초안 파일을 찾을 수 없습니다."를 텔레그램 창에 정상 피드백하도록 보완**함. |
| **5** | **불필요한 `import re` 포함** | 텔레그램 콜백 핸들러 코드에서 사용하지 않는 `re` 모듈을 import하여 잔여 코드가 낭비됨. | `button_callback_handler` 명세 코드 상단에서 **`import re` 구문을 완전 제거**함. |
| **6** | **Section 8 검증 시나리오 오타** | 수동 검증 항목 279번째 줄에 `_company/shared/decisions.md`로 기재되어 언더스코어(`_shared`) 누락 오타 발생. | 경로를 `_company/_shared/decisions.md`로 **정상 교정**함. |

---

## 2. 가상 기업 OS v4.0 디렉토리 및 물리 구조 명세

시스템 디렉토리 구분을 위한 언더스코어 네이밍 prefix 규격과 세션 격리 아카이브(`sessions/`)를 반영한 최종 폴더 명세입니다.

```text
c:\Users\jmj\Desktop\안티그래비티\new/
├── _company/                         [1인 기업 OS 최상위 격리 공간]
│   ├── _shared/                      [공유 서비스 계층]
│   │   ├── _system.md                # 1인 기업 OS 전체 협업 규격 및 의사결정 프로세스 정의
│   │   ├── identity.md               # 금융 에이전트의 정체성 및 가치관 명세
│   │   ├── goals.md                  # 회사 공동의 대목표 (금융 정보의 정밀 요약 제공 등)
│   │   ├── decisions.md              # 승인 완료된 최고 신뢰 의사결정 로그 (Append-only)
│   │   └── active.json               # 활성화 상태 및 시스템 상태 플래그
│   │
│   ├── _agents/                      [개별 격리 에이전트 공간]
│   │   ├── chief_agent/              # 🧭 총괄 에이전트 (오케스트레이터)
│   │   │   ├── config.md             # 에이전트별 구동 설정
│   │   │   ├── prompt.md             # 오케스트레이션 페르소나 지침 (자연어 편집 가능)
│   │   │   ├── memory.md             # 실행 히스토리 및 피드백 로그 (Append-only)
│   │   │   ├── rag_mode.txt          # RAG 구동 방식 선언 (self-rag / off)
│   │   │   └── tools.md              # 가용 도구 정의 (AUTONOMY_LEVEL: 2 - 승인 대기 필수)
│   │   │   # * 원본 CEO의 설계 철학을 반영하여 chief_agent에는 goal.md를 추가하지 않고 goals.md를 상속합니다.
│   │   │
│   │   ├── db_manager/               # 💾 DB 관리 에이전트 (0선)
│   │   │   ├── config.md, prompt.md, memory.md, tools.md, rag_mode.txt
│   │   │   └── goal.md               # DB 관리 및 정량 지표 연산 자동화 고유 미션
│   │   │
│   │   ├── korea_reporter/           # 🇰🇷 국내경제 에이전트 (1선)
│   │   │   ├── config.md, prompt.md, memory.md, tools.md, rag_mode.txt
│   │   │   └── goal.md               # 국내 거시경제 및 금융 지표 수집/요약 고유 미션
│   │   │
│   │   ├── global_reporter/          # 🌍 해외경제 에이전트 (2선)
│   │   │   ├── config.md, prompt.md, memory.md, tools.md, rag_mode.txt
│   │   │   └── goal.md               # 해외 지표 및 미국 증시/환율 모니터링 고유 미션
│   │   │
│   │   ├── bitcoin_reporter/         # 🪙 비트코인 에이전트 (3선)
│   │   │   ├── config.md, prompt.md, memory.md, tools.md, rag_mode.txt
│   │   │   └── goal.md               # 비트코인 및 크립토 시장 동향/온체인 분석 고유 미션
│   │   │
│   │   └── wiki_manager/             # 🧠 Wiki 관리 에이전트 (4선)
│   │       ├── config.md, prompt.md, memory.md, tools.md, rag_mode.txt
│   │       └── goal.md               # 수집된 정보들을 기존 위키 지식과 컴파운딩 병합하는 고유 미션
│   │
│   ├── approvals/                    [ Level 2 Draft 모드 시 승인 대기 대기실 ]
│   │   ├── pending/                  # 위키 합성 초안 마크다운 대기실 (*_draft.md)
│   │   └── approved/                 # 승인 완료된 초안 보관소
│   │
│   ├── sessions/                     [ 세션 타임스탬프별 실행 산출물 보관소 ]
│   │   └── <YYYY-MM-DDT%H-%M>/       # 예: 2026-05-23T15-13
│   │       ├── _report.md            # 해당 세션의 최종 텔레그램 브리핑 전문
│   │       ├── chief_agent.md        # 총괄 에이전트 실행 오케스트레이션 기록
│   │       ├── db_manager.json       # 수집된 원천 계량 수치 원본 데이터
│   │       └── wiki_manager.md       # 위키 병합 대상 뉴스 목록 및 의사결정 기록
│   │
│   └── company_state.json            # 기업 운영 종합 상태 데이터
```

---

## 3. 텔레그램 승인 게이트 및 decisions.md I/O 구현 명세 (R3 보완)

`telegram_bot.py`와 `InlineKeyboardMarkup`을 연동하여 승인 대기 워크플로우를 가동합니다. 사용자가 "승인" 또는 "반려"를 클릭할 경우 처리하며, `ROOT_DIR` 절대경로와 `DECISIONS_PATH`를 바인딩하여 런타임 오류 없이 작동하도록 합니다.

### 1) Inline Keyboard 승인 요청 메시지 렌더링
```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

keyboard = [
    [
        InlineKeyboardButton("🟢 승인 및 위키 병합", callback_data=f"approve_{wiki_name}"),
        InlineKeyboardButton("🔴 반려 및 삭제 파기", callback_data=f"reject_{wiki_name}")
    ]
]
reply_markup = InlineKeyboardMarkup(keyboard)
await context.bot.send_message(
    chat_id=CHAT_ID,
    text=f"⚖️ *[금융 위키 합성 승인 대기]*\n\n"
         f"대상 위키: `[[{wiki_name}]]`\n"
         f"수집된 정보와 당일 지표가 반영된 위키 초안이 대기 중입니다. 하단의 버튼을 통해 처리해 주십시오.",
    reply_markup=reply_markup,
    parse_mode="Markdown"
)
```

### 2) CallbackQueryHandler 및 decisions.md 파일 I/O 구현 코드 (re 미임포트 및 reject else 예외 처리 완료)
```python
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes

# 설정 및 유틸리티 모듈에서 경로 상수를 절대경로로 임포트
from agents.shared.config import WIKI_DIR, DECISIONS_PATH, ROOT_DIR
from agents.shared.file_utils import write_file_safely

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    action, wiki_name = data.split("_", 1)
    
    # 런타임 실행 경로(CWD) 영향 방지를 위한 ROOT_DIR 기반 절대경로 바인딩
    draft_path = ROOT_DIR / "_company" / "approvals" / "pending" / f"{wiki_name}_draft.md"
    official_path = Path(WIKI_DIR) / f"{wiki_name}.md"
    
    if action == "approve":
        if draft_path.exists():
            try:
                # 1. 초안 마크다운 파일을 공식 마스터 위키 경로에 안전하게 저장
                with open(draft_path, "r", encoding="utf-8") as df:
                    content = df.read()
                write_file_safely(official_path, content)
                draft_path.unlink()  # 대기실의 초안 삭제
                
                # 2. decisions.md 파일에 실시간 의사결정 이력 추가 기록 (Append)
                decisions_path = Path(DECISIONS_PATH)
                decisions_path.parent.mkdir(parents=True, exist_ok=True)
                
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                decision_entry = f"\n## [{now_str}] {wiki_name} 지식 컴파운딩 승인\n" \
                                 f"- [[{wiki_name}]] 위키 초안이 사용자의 수동 승인을 받아 공식 지식베이스에 통합 갱신되었습니다.\n"
                                 
                with open(decisions_path, "a", encoding="utf-8") as f:
                    f.write(decision_entry)
                
                await query.edit_message_text(
                    text=f"✅ *[[{wiki_name}]] 승인 완료*\n"
                         f"공식 위키 병합 완료 및 `decisions.md` 기록이 업데이트되었습니다.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                await query.edit_message_text(text=f"❌ 승인 처리 중 파일 I/O 오류 발생: {e}")
        else:
            await query.edit_message_text(text="⚠️ 오류: 대기 중인 초안 파일을 찾을 수 없습니다.")
            
    elif action == "reject":
        if draft_path.exists():
            try:
                draft_path.unlink()
                await query.edit_message_text(
                    text=f"❌ *[[{wiki_name}]] 반려 완료*\n"
                         f"작성된 초안 마크다운이 대기실에서 삭제 파기되었습니다.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                await query.edit_message_text(text=f"❌ 파일 삭제 중 오류 발생: {e}")
        else:
            # R3 반영: 이미 처리되어 대기 파일이 부재할 시 피드백 메시지 제공
            await query.edit_message_text(text="⚠️ 오류: 이미 처리되었거나 대기 중인 초안 파일을 찾을 수 없습니다.")
```

---

## 4. `rag_mode.txt` 유효값 및 RAG 컨텍스트 연동 메커니즘 (R3 보완)

`rag_mode.txt`는 각 에이전트 디렉토리에 개별 배치되어 동작하며, 런타임 시에 RAG 컨텍스트를 동적으로 결합 및 제어하기 위한 용도로 활용됩니다.

### 1) 유효값 정의
- **`self-rag` (기본값)**: 5대 메모리 위계 정책에 의거하여 `decisions.md`, `identity.md`, `goals.md` 및 개별 에이전트의 `memory.md`, `goal.md` 텍스트를 로드한 뒤 시스템 프롬프트 상단에 컨텍스트로 결합하여 Gemma4 모델에 주입합니다.
- **`off`**: 외부 RAG 연동을 차단하고, 에이전트가 가용한 원천 입력 데이터만을 주입하여 작업을 수행하도록 제한합니다.

### 2) RAG 컨텍스트 결합 로드 절대경로 명세
```python
from pathlib import Path
from agents.shared.config import ROOT_DIR, DECISIONS_PATH

def load_rag_context(agent_dir: Path) -> str:
    rag_file = agent_dir / "rag_mode.txt"
    rag_mode = "self-rag"  # 설정 파일 부재 시 기본값
    
    if rag_file.exists():
        with open(rag_file, "r", encoding="utf-8") as rf:
            rag_mode = rf.read().strip().lower()
            
    if rag_mode == "off":
        return ""
        
    context_parts = []
    
    # 1단계: decisions.md (1순위 - 최고 신뢰 의사결정) - ROOT_DIR 절대경로 참조
    dec_path = Path(DECISIONS_PATH)
    if dec_path.exists():
        with open(dec_path, "r", encoding="utf-8") as f:
            context_parts.append(f"### [의사결정 이력 (1순위)]\n{f.read()}\n")
            
    # 2단계: identity.md (2순위 - 기업 가치관 및 정체성) - ROOT_DIR 절대경로 참조
    id_path = ROOT_DIR / "_company" / "_shared" / "identity.md"
    if id_path.exists():
        with open(id_path, "r", encoding="utf-8") as f:
            context_parts.append(f"### [비서 정체성 및 핵심가치 (2순위)]\n{f.read()}\n")
            
    # 3단계: goals.md (3순위 - 기업 대목표) - ROOT_DIR 절대경로 참조
    goal_path = ROOT_DIR / "_company" / "_shared" / "goals.md"
    if goal_path.exists():
        with open(goal_path, "r", encoding="utf-8") as f:
            context_parts.append(f"### [공동의 대목표 (3순위)]\n{f.read()}\n")
            
    # 4단계: 에이전트 개별 memory.md / goal.md (4순위 - 에이전트 격리 메모리 및 업무 미션)
    agent_mem = agent_dir / "memory.md"
    if agent_mem.exists():
        with open(agent_mem, "r", encoding="utf-8") as f:
            context_parts.append(f"### [에이전트 고유 실행 기억 (4순위)]\n{f.read()}\n")
            
    agent_goal = agent_dir / "goal.md"
    if agent_goal.exists():
        with open(agent_goal, "r", encoding="utf-8") as f:
            context_parts.append(f"### [에이전트 개별 전담 임무 (4순위)]\n{f.read()}\n")
            
    return "\n".join(context_parts)
```

### 3) RAG 컨텍스트 파이프라인 주입 흐름 상세 정의
- **위치 및 로드 시점**: 
  - `load_rag_context()`는 공통 모듈인 `agents/shared/file_utils.py` 내에 함수로 배치되어 관리됩니다.
  - 에이전트 파이프라인(`agents/wiki_manager.py` 등)의 핵심 합성 루프가 구동되는 시점(예: `run()` 혹은 `process_compounding()`의 진입 단계)에 호출됩니다.
- **주입 대상 및 주입 방식**:
  - `wiki_manager` 에이전트의 물리 폴더 경로(예: `ROOT_DIR / "_company" / "_agents" / "wiki_manager"`)를 인수로 전달하여 `load_rag_context()`를 실행합니다.
  - 반환받은 RAG 컨텍스트 텍스트 문자열을 합성 추론용 프롬프트 템플릿(기존 `prompts.py`에서 `_company/_agents/wiki_manager/prompt.md` 마크다운으로 분할 이관된 템플릿)의 하단 또는 `{rag_context}` 동적 주입부(Slot)에 그대로 바인딩합니다.
  - 이를 통해 LLM(Gemma4) 추론 모델에 공동 가치관과 의사결정 히스토리가 자동으로 시스템 프롬프트 컨텍스트로 이식되어 융합 작성이 진행됩니다.

---

## 5. `sessions/` 아카이빙 및 저장 정책

파이프라인 가동 시 생성되는 실행 이력과 수치 지표 및 보고서를 격리 보관하기 위해 `sessions/` 구조를 적극 운영합니다.

- **프로세스**:
  1. `chief_agent.run_relay()` 호출 시점의 타임스탬프(`timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M")`)를 생성합니다.
  2. 세션 디렉토리 `_company/sessions/{timestamp}/`를 자동 생성합니다.
  3. `db_manager`가 수집한 모든 정량 금융 지표 데이터를 `db_manager.json`에 구조적 형태로 보관합니다.
  4. 각 에이전트들의 실행 이력, LLM 프롬프트 로그, 응답 통계 등은 에이전트명에 해당되는 마크다운(예: `chief_agent.md`, `wiki_manager.md`)에 보관합니다.
  5. 최종적으로 사용자에게 브리핑된 텔레그램 카드 전문은 `_report.md` 파일로 저장하여 아카이빙합니다.

---

## 6. v3.0 ➡️ v4.0 점진적 마이그레이션 호환성 전략 (R3 보완)

기존 코드가 동작하는 환경을 보호하면서 새 아키텍처로 안전하게 이전하기 위한 마이그레이션 이행 전략입니다.

- **1단계: `agents/shared/config.py` 설정 보강 (R3 핵심)**
  * 기존 `config.py` 내의 `WIKI_DIR`과 `RAW_DIR` 상수를 기존 `obsidian-vault/wiki/` 및 `obsidian-vault/raw/` 디렉토리로 투명하게 유지합니다.
  * `config.py` 최상단에 **`DECISIONS_PATH = ROOT_DIR / "_company" / "_shared" / "decisions.md"` 상수를 신설 선언**하여 봇 기동 시 런타임 ImportError 오류를 원천 차단합니다.
- **2단계: 기존 prompts.py의 수동 파일 이관**
  * `agents/shared/prompts.py`에 정의된 프롬프트 문자열 상수를 각각 `_company/_agents/korea_reporter/prompt.md`, `_company/_agents/wiki_manager/prompt.md` 등의 독립된 마크다운 파일로 이관합니다.
  * 이관 완료 후, `prompts.py` 상수를 제거하고 각 에이전트 구동 파이프라인에서 해당 마크다운 프롬프트 파일을 동적으로 로드하도록 패키지 코드를 패치합니다.
- **3단계: 비트코인 리포터(`bitcoin_reporter.py`)의 공식 격리 편입**
  * 누락 방지를 위해 `_company/_agents/bitcoin_reporter/` 공간을 개설하고 고유 미션 `goal.md` 및 `rag_mode.txt`를 수립하여 6대 에이전트 체계를 유지합니다.

---

## 7. CEO goal.md 부재 원인 분석 및 설계 반영

- **원본 설계 의도 분석**:
  실사 대조 결과 원본 Connect-AI 구조에서 CEO(오케스트레이터)에게 `goal.md`가 부재했던 원인은, CEO가 자원의 분배와 라우팅 및 릴레이 지휘를 전담하기 때문에 개별적인 특정 태스크 미션보다는 전체 비즈니스 대목표(`goals.md`)를 곧바로 자신의 구동 규칙으로 따르기 때문입니다.
- **설계 반영 조치**:
  이 분석 결과를 반영하여, 본 구현 계획의 `chief_agent` 역시 불필요한 개별 `goal.md` 생성을 배제하고, `_shared/goals.md`를 공통 상속하여 공동의 미션을 수행하는 방식으로 설계를 통일합니다.

---

## 8. 구현 검증 계획 (R3 보완)

### 1) 자동화 및 단위 테스트 검증
- `pytest`를 활용하여 `load_rag_context()`가 `rag_mode.txt` 유효값에 따라 올바른 5대 메모리 위계를 결합 문자열로 구성하는지 검증합니다.
- 텔레그램 승인/반려 시 콜백 핸들러 내부에서 `decisions.md` 파일에 추가 기록(Append)이 일어나는지 파일 쓰기 모킹 테스트를 작성합니다.

### 2) 수동 검증 시나리오
- `/update` 명령어 전송 후, 텔레그램 메시지에 인라인 버튼(승인/반려)이 정상 렌더링되는지 확인합니다.
- '승인' 버튼 클릭 시, 임시 초안(`_company/approvals/pending/`)이 `obsidian-vault/wiki/` 정식 경로로 안전하게 이동 및 갱신되는지 확인합니다.
- `_company/_shared/decisions.md` 파일이 자동 업데이트되어 날짜 및 승인 히스토리가 정상 누적되었는지 파일을 직접 확인합니다. (오타 경로 교정 완료)
- '반려' 버튼 중복 클릭 또는 대기 파일 부재 시 "⚠️ 오류: 이미 처리되었거나 대기 중인 초안 파일을 찾을 수 없습니다." 문구가 정상 렌더링되는지 확인합니다.
- `_company/sessions/` 디렉토리에 실행 일자별 타임스탬프 폴더가 생성되고 `_report.md` 등 산출물이 아카이빙되었는지 대조합니다.

---

## 9. 사용자 승인 대기

> [!IMPORTANT]
> - 본 **v4.0 통합 구현 계획서 (R3)**는 R2 검토의 모든 결함(ImportError 블로커, 상대경로 결함, load_rag_context() 결합/주입 상세 정의 누락, reject 분기 else 핸들러 누락 등)을 전격 해결하고 완벽하게 치유하여 작성한 최종 문서입니다.
> - 사용자님께서 검토 후 **"승인"**, **"진행"** 또는 **"시작"** 등 명시적인 실행 의사를 채팅으로 전송해 주시면, 즉각 `_company/` 최상위 구조 개설 및 텔레그램 `approval_gate` 연동 개발에 들어가도록 하겠습니다.
