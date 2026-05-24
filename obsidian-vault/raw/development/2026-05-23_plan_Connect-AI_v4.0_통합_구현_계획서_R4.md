← [[Development_Hub|개발 마스터 대시보드]]

# Connect-AI v4.0 통합 구현 계획서 (R4)

본 계획서는 사용자의 **"Connect-AI v4.0 통합 구현 계획서 (R3) 검토 R0"** 보고서에서 도출된 중간 수준의 구현 갭(설명 중심 명세에 대한 실제 코드 결여) 및 경미한 설계 정합성 지적(RAG 모듈 분리, 중복 래핑 제거)을 완전히 반영하여 보완한 최종 통합 구현 계획서 v4.0 (R4)입니다.

불완전한 추상적 설명을 모두 배제하고, 구현자가 즉시 소스 코드에 적용할 수 있는 구체적인 Python 소스 코드 명세와 정량적 팩트 중심으로 최종 교정하였습니다.

---

## 1. 피드백 수용 및 교정 조치 명세 (R4 최종 보완)

R3 검토 보고서(R0)의 지적 사항을 정밀 분석하고 아래와 같이 최종 설계를 보완하였습니다.

| 번호 | 지적 사항 | 원인 및 사실 대조 결과 | R4 최종 교정 및 반영 조치 |
| :---: | :--- | :--- | :--- |
| **1** | **`load_rag_context()` 삽입 코드 미제시 (갭 1)** | `wiki_manager.py` 내 RAG 로드 시점과 컨텍스트의 템플릿 슬롯 바인딩에 대한 설명은 존재하나 실제 구현 코드가 부재하여 구현 단계의 혼선 우려가 존재함. | `wiki_manager.py` 내의 **`run_compounding()` 진입 단계에서 RAG 컨텍스트를 로드하고 replace 치환을 적용하는 실질적인 Python 연동 코드를 수록**함. |
| **2** | **`sessions/` 디렉토리 생성 코드 미제시 (갭 2)** | `chief_agent.run_relay()` 내부에서 타임스탬프 세션 디렉토리를 개설하고 에이전트 산출물을 기록하는 물리적 코드가 누락됨. | `chief_agent.py` 내에서 **타임스탬프 세션 폴더를 생성하고, DB 메타(JSON) 및 최종 보고서(MD)를 격리 저장하는 영속화 구현 코드를 추가 명세**함. |
| **3** | **`prompt.md` 동적 로드 코드 미제시 (갭 3)** | 기존 `prompts.py` 상수를 제거하고 각 에이전트 폴더에 이관된 `prompt.md` 마크다운을 동적으로 읽어들이는 실물 코드가 결여됨. | 에이전트 구동 파이프라인에서 **`prompt.md`를 안전하게 로드하고, 부재 시 기존 상수를 Fallback으로 매핑하는 동적 리더 코드를 명세**함. |
| **4** | **`load_rag_context()` 배치 정합성 미흡 (경미 2)** | RAG 컨텍스트 조합은 프롬프트 빌더 영역에 가까우나, 파일 I/O 유틸리티 모듈인 `file_utils.py`에 강제 배치하여 모듈 정체성이 훼손됨. | `file_utils.py`에서 RAG 로더를 제외하고, **`agents/shared/rag_utils.py` 신설 모듈을 정의하여 RAG 연동 코드를 온전히 분리 격리**함. |
| **5** | **`Path(DECISIONS_PATH)` 이중 래핑 (경미 1)** | `config.py`에 정의된 `DECISIONS_PATH`는 이미 `Path` 객체이므로 `Path(DECISIONS_PATH)`로 다시 감싸는 이중 래핑이 존재함. | 불필요한 래핑을 소거하여 **`decisions_path = DECISIONS_PATH`로 코드를 직관적으로 교정**함. |

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

## 3. 텔레그램 승인 게이트 및 decisions.md I/O 구현 명세 (R4 보완)

`telegram_bot.py`와 `InlineKeyboardMarkup`을 연동하여 승인 대기 워크플로우를 가동합니다. 사용자가 "승인" 또는 "반려"를 클릭할 경우 처리하며, `ROOT_DIR` 절대경로와 `DECISIONS_PATH`를 바인딩하고 `Path` 이중 래핑을 소거하여 안전하게 작동하도록 합니다.

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

### 2) CallbackQueryHandler 및 decisions.md 파일 I/O 구현 코드 (이중 래핑 해제 및 reject else 완비)
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
                
                # 2. decisions.md 파일에 실시간 의사결정 이력 추가 기록 (Append) - 이중 래핑 소거
                decisions_path = DECISIONS_PATH
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
            # R4 반영: 이미 처리되어 대기 파일이 부재할 시 피드백 메시지 제공
            await query.edit_message_text(text="⚠️ 오류: 이미 처리되었거나 대기 중인 초안 파일을 찾을 수 없습니다.")
```

---

## 4. `rag_mode.txt` 유효값 및 RAG 컨텍스트 연동 메커니즘 (R4 보완)

`rag_mode.txt`는 각 에이전트 디렉토리에 개별 배치되어 동작하며, RAG 모듈을 `agents/shared/rag_utils.py`로 명확히 분리 신설하였습니다.

### 1) 유효값 정의
- **`self-rag` (기본값)**: 5대 메모리 위계 정책에 의거하여 `decisions.md`, `identity.md`, `goals.md` 및 개별 에이전트의 `memory.md`, `goal.md` 텍스트를 로드한 뒤 시스템 프롬프트 상단에 컨텍스트로 결합하여 Gemma4 모델에 주입합니다.
- **`off`**: 외부 RAG 연동을 차단하고, 에이전트가 가용한 원천 입력 데이터만을 주입하여 작업을 수행하도록 제한합니다.

### 2) 신설 모듈 `agents/shared/rag_utils.py` RAG 컨텍스트 결합 로드 코드 명세
```python
# [NEW] agents/shared/rag_utils.py (R4 전격 신설 분리)
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
    dec_path = DECISIONS_PATH
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

### 3) `wiki_manager.py`의 RAG 주입 및 `prompt.md` 동적 로드 실제 적용 코드 (갭 1 & 갭 3 완수)
`wiki_manager.py` 내의 `run_compounding()` 실행 진입 시점에 prompts.py 상수를 탈피하고, 마크다운 프롬프트를 동적 리드하여 `{rag_context}` 슬롯에 치환하는 파이썬 코드 명세입니다.
```python
# agents/wiki_manager.py (R4 전격 명세 코드)
from pathlib import Path
from agents.shared.config import ROOT_DIR, WIKI_DIR, RAW_DIR
from agents.shared.rag_utils import load_rag_context

def run_compounding(self):
    # 1. wiki_manager 에이전트 물리 격리 폴더 참조
    agent_dir = ROOT_DIR / "_company" / "_agents" / "wiki_manager"
    
    # 2. prompt.md 마크다운 프롬프트 동적 로드 (갭 3 해결)
    prompt_path = agent_dir / "prompt.md"
    if prompt_path.exists():
        system_prompt_template = prompt_path.read_text(encoding="utf-8")
    else:
        # Fallback 조치 (기존 constants 복사 활용)
        from agents.shared.prompts import WIKI_COMPOUND_SYSTEM_PROMPT_TEMPLATE
        system_prompt_template = WIKI_COMPOUND_SYSTEM_PROMPT_TEMPLATE
        
    # 3. RAG 컨텍스트 동적 호출 로드 (갭 1 해결)
    rag_context = load_rag_context(agent_dir)
    
    # 4. RAG 컨텍스트 슬롯 치환 및 주입
    system_prompt = system_prompt_template.replace("{rag_context}", rag_context)
    
    # 5. LLM 추론 바인딩
    # ... 이후 system_prompt를 사용해 Ollama Gemma4 컴파운딩 추론 기동 ...
```

---

## 5. `sessions/` 아카이빙 및 저장 정책 및 실제 구현 코드 (R4 보완 - 갭 2 완수)

파이프라인 가동 시 생성되는 실행 이력과 수치 지표 및 보고서를 격리 보관하기 위해 `sessions/` 구조를 개설하고 기록하는 `chief_agent.run_relay()` 내부의 물리 소스 코드 명세입니다.

```python
# agents/chief_agent.py (R4 세션 영속화 실물 코드 명세)
import json
from datetime import datetime
from pathlib import Path
from agents.shared.config import ROOT_DIR

def run_relay(self):
    # 1. 기동 시점의 실행 타임스탬프 생성 및 sessions 격리 디렉토리 생성 (갭 2 완치)
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M")
    session_dir = ROOT_DIR / "_company" / "sessions" / timestamp
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. 0선 DB 관리자 가동 및 수집 데이터 메타 세션 백업
    db_result = self.db_manager.collect_indicators()
    db_meta_path = session_dir / "db_manager.json"
    with open(db_meta_path, "w", encoding="utf-8") as f:
        json.dump(db_result, f, ensure_ascii=False, indent=2)
        
    # 3. 1선 ~ 4선 순차 릴레이 프로세스 가동
    # ... 에이전트 실행 릴레이 작동 ...
    
    # 4. 에이전트별 구동 상세 기록 파일 영속화 격리 백업
    chief_log_path = session_dir / "chief_agent.md"
    chief_log_path.write_text(self.gather_agent_stats(), encoding="utf-8")
    
    # 5. 최종 사용자에게 송출된 일일 브리핑 메시지 전문 격리 영속화
    final_brief = self.generate_final_brief()
    report_path = session_dir / "_report.md"
    report_path.write_text(final_brief, encoding="utf-8")
```

---

## 6. v3.0 ➡️ v4.0 점진적 마이그레이션 호환성 전략

기존 코드가 동작하는 환경을 보호하면서 새 아키텍처로 안전하게 이전하기 위한 마이그레이션 이행 전략입니다.

- **1단계: `agents/shared/config.py` 설정 보강**
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

## 8. 구현 검증 계획 (R4 보완)

### 1) 자동화 및 단위 테스트 검증
- `pytest`를 활용하여 `load_rag_context()`가 `rag_mode.txt` 유효값에 따라 올바른 5대 메모리 위계를 결합 문자열로 구성하는지 검증합니다.
- 텔레그램 승인/반려 시 콜백 핸들러 내부에서 `decisions.md` 파일에 추가 기록(Append)이 일어나는지 파일 쓰기 모킹 테스트를 작성합니다.

### 2) 수동 검증 시나리오
- `/update` 명령어 전송 후, 텔레그램 메시지에 인라인 버튼(승인/반려)이 정상 렌더링되는지 확인합니다.
- '승인' 버튼 클릭 시, 임시 초안(`_company/approvals/pending/`)이 `obsidian-vault/wiki/` 정식 경로로 안전하게 이동 및 갱신되는지 확인합니다.
- `_company/_shared/decisions.md` 파일이 자동 업데이트되어 날짜 및 승인 히스토리가 정상 누적되었는지 파일을 직접 확인합니다.
- '반려' 버튼 중복 클릭 또는 대기 파일 부재 시 "⚠️ 오류: 이미 처리되었거나 대기 중인 초안 파일을 찾을 수 없습니다." 문구가 정상 렌더링되는지 확인합니다.
- `_company/sessions/` 디렉토리에 실행 일자별 타임스탬프 폴더가 생성되고 `_report.md` 등 산출물이 아카이빙되었는지 대조합니다.

---

## 9. 사용자 승인 대기

> [!IMPORTANT]
> - 본 **v4.0 통합 구현 계획서 (R4)**는 R3 검토에서 지적된 3가지 중간 수준의 구현 갭(wiki_manager.py 내 RAG 주입, prompts.py 상수 탈피 및 prompt.md 동적 로드, chief_agent.py 내 sessions 타임스탬프 폴더 생성 및 JSON/MD 기록 자동화 로직)과 2가지 경미 조치 사항(agents/shared/rag_utils.py 신설로 RAG 로직의 설계 정합성 보강 및 decisions_path 이중 래핑 소거)을 **실제 Python 코드로 완벽하게 실체화**하여 보완한 무결점 최종 명세서입니다.
> - 사용자님께서 검토 후 **"승인"**, **"진행"** 또는 **"시작"** 등 명시적인 실행 의사를 채팅으로 전송해 주시면, 즉각 `_company/` 최상위 구조 개설 및 텔레그램 `approval_gate` 연동 개발에 들어가도록 하겠습니다.

## 🔗 연관 개발 문서 (Cross References)
- [[2026-05-23_walkthrough_Connect-AI_v4.0_통합_구현_완수보고서_R0]]
