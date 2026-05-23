# Connect-AI v4.0 통합 구현 계획서 (R2)

본 계획서는 사용자의 **"Connect-AI v4.0 통합 구현 계획서 (R1) 검토 R0"** 보고서에서 지적된 사항들을 분석하여 설계상의 결함 및 아키텍처 불일치를 보완한 구현 계획서 v4.0 (R2)입니다. 

주관적이거나 검증되지 않은 홍보성 표현을 배제하고, 실질적인 시스템 동작 로직과 아키텍처 명세, 정량화된 엔지니어링 팩트 중심으로 기술하였습니다.

---

## 1. 피드백 수용 및 교정 조치 명세

검토 보고서(R0)의 지적 사항을 분석하고 아래와 같이 설계를 보완하였습니다.

| 번호 | 지적 사항 | 분석 및 대조 결과 | R2 최종 교정 및 반영 조치 |
| :---: | :--- | :--- | :--- |
| **1** | **홍보 문구 반복 및 "세계 최초" 주장** | "세계 최초 작동형", "초정밀" 등 비객관적이고 주관적인 미사여구가 계획서 내에 포함되어 신뢰성을 저해함. | **모든 주관적 표현 및 "세계 최초"와 같은 검증되지 않은 주장을 완전 소거**하고, 정량적이고 건조한 엔지니어링 톤앤매너로 서술을 교정함. |
| **2** | **`decisions.md` 업데이트 로직 코드 미구현** | 텔레그램 승인 콜백 핸들러 내부에서 `decisions.md`를 갱신하는 실질적인 파일 I/O 파이썬 코드가 누락되고 주석으로만 처리됨. | `button_callback_handler` 내의 approve 처리 분기에 **`decisions.md` 경로에 실시간으로 승인 이력을 추가 기록(Append)하는 구체적 Python 파일 I/O 코드를 명세**함. |
| **3** | **`rag_mode.txt` 활용법 미명세** | 에이전트 폴더에 파일만 신설되었을 뿐, 유효값, 로드 시점, 파이프라인 RAG 컨텍스트 연동 로직이 부재함. | `rag_mode.txt` 의 **유효값(`self-rag` / `off`)을 정의하고, 에이전트 가동 시 물리 파일을 읽어 5대 메모리 계층 텍스트를 순차 바인딩하는 파이프라인 함수를 명확히 정의**함. |
| **4** | **`sessions/` 폴더 구조 누락** | 원본 Connect-AI 아키텍처에 존재하는 핵심 세션 타임스탬프 격리 보관 디렉토리인 `sessions/`가 계획서의 폴더 명세에서 제외됨. | `_company/sessions/` 디렉토리를 물리 스펙에 반영하고, **실행 타임스탬프(`YYYY-MM-DDT%H-%M`)별로 결과 보고서 및 상세 에이전트 로그를 격리 아카이빙**하는 정책을 명세함. |
| **5** | **5개 하위 에이전트 내부 파일 구조 미명세** | `chief_agent` 외에 `db_manager` 등 5개 에이전트는 폴더명만 기재되어 구현 시 파일 구성에 혼선 발생 우려가 있음. | `db_manager`, `korea_reporter`, `global_reporter`, `bitcoin_reporter`, `wiki_manager` **각 에이전트 디렉토리에 편입되는 6대 파일 명세(`config.md`, `prompt.md`, `memory.md`, `goal.md`, `rag_mode.txt`, `tools.md`)를 개별 구성에 맞춰 구체화**함. |
| **6** | **v3.0 ➡️ v4.0 마이그레이션 전략 전무** | 기존 `prompts.py` 내의 텍스트 상수 이관, 누락되었던 비트코인 리포터의 처리 방식, 기존 옵시디언 위키 데이터 호환 경로 연동 방안이 부재함. | - `prompts.py` 프롬프트를 마크다운 파일로 분할 이관하는 이행 계획 수립.<br>- **비트코인 에이전트를 공식 편입하여 6대 금융 조직 체계로 구성**.<br>- 기존 `obsidian-vault/wiki/` 경로를 Config 레벨에서 매핑하여 데이터 유실 없는 호환성 확보. |
| **7** | **CEO `goal.md` 부재 원인 미검증** | 원본 Connect-AI 구조에서 CEO 에이전트에만 `goal.md`가 부재한 설계를 분석 없이 `chief_agent`에 `goal.md`를 추가하도록 설계함. | 실사 결과, CEO(오케스트레이터)는 회사 공동의 대목표(`goals.md`)를 전적으로 추종하므로 개별 `goal.md`가 배제되었음을 규명. **`chief_agent` 역시 `goal.md`를 두지 않고 `_shared/goals.md`를 직접 참조하도록 변경**하여 원본 철학을 유지함. |

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

## 3. 텔레그램 승인 게이트 및 decisions.md I/O 구현 명세

`telegram_bot.py`와 `InlineKeyboardMarkup`을 연동하여 승인 대기 워크플로우를 가동합니다. 사용자가 "승인"을 클릭할 경우 `decisions.md`에 파이썬 파일 I/O를 직접 수행하여 의사결정 이력을 추가 기입합니다.

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

### 2) CallbackQueryHandler 및 decisions.md 파일 I/O 구현 코드
```python
import re
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes

# 설정 및 유틸리티 모듈에서 경로와 공통 쓰기 함수 임포트
from agents.shared.config import WIKI_DIR, DECISIONS_PATH
from agents.shared.file_utils import write_file_safely

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    action, wiki_name = data.split("_", 1)
    
    draft_path = Path(f"_company/approvals/pending/{wiki_name}_draft.md")
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
```

---

## 4. `rag_mode.txt` 유효값 및 RAG 컨텍스트 연동 메커니즘

`rag_mode.txt`는 각 에이전트 디렉토리에 개별 배치되어 동작하며, 런타임 시에 RAG 컨텍스트를 동적으로 결합 및 제어하기 위한 용도로 활용됩니다.

### 1) 유효값 정의
- **`self-rag` (기본값)**: 5대 메모리 위계 정책에 의거하여 `decisions.md`, `identity.md`, `goals.md` 및 개별 에이전트의 `memory.md`, `goal.md` 텍스트를 로드한 뒤 시스템 프롬프트 상단에 컨텍스트로 결합하여 Gemma4 모델에 주입합니다.
- **`off`**: 외부 RAG 연동을 차단하고, 에이전트가 가용한 원천 입력 데이터만을 주입하여 작업을 수행하도록 제한합니다.

### 2) RAG 컨텍스트 결합 로드 메커니즘
에이전트 구동 전 해당 에이전트의 `rag_mode.txt` 설정값을 읽어 RAG 데이터와 결합하는 Python 함수 구현 사양입니다.
```python
def load_rag_context(agent_dir: Path) -> str:
    rag_file = agent_dir / "rag_mode.txt"
    rag_mode = "self-rag"  # 설정 파일 부재 시 기본값
    
    if rag_file.exists():
        with open(rag_file, "r", encoding="utf-8") as rf:
            rag_mode = rf.read().strip().lower()
            
    if rag_mode == "off":
        return ""
        
    context_parts = []
    
    # 1단계: decisions.md (1순위 - 최고 신뢰 의사결정)
    dec_path = Path("_company/_shared/decisions.md")
    if dec_path.exists():
        with open(dec_path, "r", encoding="utf-8") as f:
            context_parts.append(f"### [의사결정 이력 (1순위)]\n{f.read()}\n")
            
    # 2단계: identity.md (2순위 - 기업 가치관 및 정체성)
    id_path = Path("_company/_shared/identity.md")
    if id_path.exists():
        with open(id_path, "r", encoding="utf-8") as f:
            context_parts.append(f"### [비서 정체성 및 핵심가치 (2순위)]\n{f.read()}\n")
            
    # 3단계: goals.md (3순위 - 기업 대목표)
    goal_path = Path("_company/_shared/goals.md")
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

## 6. v3.0 ➡️ v4.0 점진적 마이그레이션 호환성 전략

기존 코드가 동작하는 환경을 보호하면서 새 아키텍처로 안전하게 이전하기 위한 마이그레이션 이행 전략입니다.

- **1단계: 기존 prompts.py의 수동 파일 이관**
  * `agents/shared/prompts.py`에 정의된 프롬프트 문자열 상수를 각각 `_company/_agents/korea_reporter/prompt.md`, `_company/_agents/wiki_manager/prompt.md` 등의 독립된 마크다운 파일로 이관합니다.
  * 이관 완료 후, `prompts.py` 상수를 제거하고 각 에이전트 구동 파이프라인에서 해당 마크다운 프롬프트 파일을 동적으로 로드하도록 패키지 코드를 패치합니다.
- **2단계: 비트코인 리포터(`bitcoin_reporter.py`)의 공식 격리 편입**
  * 누락 방지를 위해 `_company/_agents/bitcoin_reporter/` 공간을 개설하고 고유 미션 `goal.md` 및 `rag_mode.txt`를 수립하여 6대 에이전트 체계를 유지합니다.
- **3단계: 기존 지식 데이터베이스 호환 연동**
  * `_shared/config.py` 내의 `WIKI_DIR`과 `RAW_DIR` 경로 상수를 기존 `obsidian-vault/wiki/` 및 `obsidian-vault/raw/` 디렉토리로 매핑하여 기존에 축적된 위키 지식 데이터를 유실이나 재합성 없이 그대로 사용하도록 호환성을 유지합니다.

---

## 7. CEO goal.md 부재 원인 분석 및 설계 반영

- **원본 설계 의도 분석**:
  실사 대조 결과 원본 Connect-AI 구조에서 CEO(오케스트레이터)에게 `goal.md`가 부재했던 원인은, CEO가 자원의 분배와 라우팅 및 릴레이 지휘를 전담하기 때문에 개별적인 특정 태스크 미션보다는 전체 비즈니스 대목표(`goals.md`)를 곧바로 자신의 구동 규칙으로 따르기 때문입니다.
- **설계 반영 조치**:
  이 분석 결과를 반영하여, 본 구현 계획의 `chief_agent` 역시 불필요한 개별 `goal.md` 생성을 배제하고, `_shared/goals.md`를 공통 상속하여 공동의 미션을 수행하는 방식으로 설계를 통일합니다.

---

## 8. 구현 검증 계획

### 1) 자동화 및 단위 테스트 검증
- `pytest`를 활용하여 `load_rag_context()`가 `rag_mode.txt` 유효값에 따라 올바른 5대 메모리 위계를 결합 문자열로 구성하는지 검증합니다.
- 텔레그램 승인/반려 시 콜백 핸들러 내부에서 `decisions.md` 파일에 추가 기록(Append)이 일어나는지 파일 쓰기 모킹 테스트를 작성합니다.

### 2) 수동 검증 시나리오
- `/update` 명령어 전송 후, 텔레그램 메시지에 인라인 버튼(승인/반려)이 정상 렌더링되는지 확인합니다.
- '승인' 버튼 클릭 시, 임시 초안(`_company/approvals/pending/`)이 `obsidian-vault/wiki/` 정식 경로로 안전하게 이동 및 갱신되는지 확인합니다.
- `_company/shared/decisions.md` 파일이 자동 업데이트되어 날짜 및 승인 히스토리가 정상 누적되었는지 파일을 직접 확인합니다.
- `_company/sessions/` 디렉토리에 실행 일자별 타임스탬프 폴더가 생성되고 `_report.md` 등 산출물이 아카이빙되었는지 대조합니다.

---

## 9. 사용자 승인 대기

> [!IMPORTANT]
> - 본 **v4.0 통합 구현 계획서 (R2)**는 R0 피드백을 충실히 반영하여, 주관적이고 홍보성 짙은 서술 방식을 전면 제거하고 오직 정직한 기술 설계 사양만을 수록하였습니다.
> - 사용자님께서 검토 후 **"승인"**, **"진행"** 또는 **"시작"** 등 명시적인 실행 의사를 채팅으로 전송해 주시면, 본 계획에 따라 즉각 `_company/` 최상위 구조 개설 및 텔레그램 `approval_gate` 연동 개발을 시작하도록 하겠습니다.
