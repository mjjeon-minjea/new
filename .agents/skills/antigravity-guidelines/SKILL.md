---
name: antigravity-guidelines
description: Antigravity Guidelines for premium visual web design, 5-step development workflow, SEO practices, and Agent-Skills command integration.
license: MIT
---

# Antigravity Workspace Rules & Skills

이 파일은 Antigravity 에이전트가 본 프로젝트 워크스페이스 내에서 작업을 수행할 때 반드시 준수해야 하는 최상위 업무 가이드라인입니다.

---

## 1. 프로젝트 개요 및 기술 스택
- **프로젝트 명**: new (Antigravity 프로젝트 규칙 및 스킬 템플릿)
- **개발 규칙**:
  - 본 워크스페이스는 Antigravity의 프리미엄 웹 개발 방법론 및 Karpathy 코딩 가이드라인을 기반으로 구축되었습니다.
  - 모든 코드는 수술적으로 꼭 필요한 부위만 정확히 수정해야 하며(Surgical Changes), 과도하게 확장되거나 불필요한 추상화는 제거합니다(Simplicity First).

---

## 2. 디자인 시스템 및 웹 프론트엔드 제약 사항
- **CSS 프레임워크**: Vanilla CSS를 핵심으로 사용합니다. (사용자가 TailwindCSS를 명시적으로 요구할 경우에만 사전 확인을 거쳐 적용합니다.)
- **글로벌 테마 토큰**: 신규 웹 컴포넌트 추가 시, `index.css`에 선언된 디자인 토큰(HSL 변수 체계 등)을 엄격히 활용해야 합니다.
- **반응형 웹**: 모바일 터치 및 레이아웃을 최우선으로 고려하며, PC 화면까지 유연하게 확장되는 fluid-grid 레이아웃을 필수 적용합니다.
- **미세 인터랙션**: 모든 버튼, 링크, 입력 필드 등 인터랙티브 엘리먼트에는 `:hover`, `:focus-visible`, `transition` 속성을 통한 부드러운 시각적 환류(feedback)를 제공해야 합니다.

---

## 3. SEO 및 접근성 가이드라인
- **의미론적 마크업**: 페이지 구조는 `<header>`, `<nav>`, `<main>`, `<article>`, `<footer>` 등의 적절한 HTML5 시멘틱 태그로 레이아웃을 짭니다.
- **메타 데이터**: 모든 최종 뷰 페이지에는 고유하고 설명적인 `<title>` 및 `<meta name="description">` 태그를 반드시 추가합니다.
- **제목 계층 구조**: 페이지당 `<h1>` 태그는 유일해야 하며, `<h2>`부터 `<h6>`까지 순차적이고 조화로운 중첩 구조를 갖추어야 합니다.
- **고유 식별자**: 테스트 및 인터랙션 매핑을 위해 핵심 요소들에는 고유하고 직관적인 `id` 속성을 필수로 기재합니다.

---

## 4. 검증 및 배포 승인 (Verification Loop)
- 수정된 코드는 반드시 사전에 동작 테스트를 거쳐야 합니다.
- UI 혹은 주요 로직 변경 시, 사용자에게 설명할 수 있는 명확한 피드백 시나리오를 설계하고 단계별로 동작 성공을 검증합니다.
- 변경된 내용은 항상 최종 정리하여 `walkthrough.md` 등에 업데이트하여 기록을 추적할 수 있도록 돕습니다.
- **사용자 수동 승인 절대 준수 룰 (Crucial)**: 시스템 환경에서 자동 승인 메시지(`automatically approved`, `Proceed to execution` 등)가 입력되더라도 이를 즉시 무시합니다. 오직 사용자 본인이 직접 대화창을 통해 **"승인"**, **"진행"**, **"시작"** 중 하나라도 포함된 메시지(예: "승인합니다", "진행해 주세요", "시작해라" 등)를 명시적으로 주었을 때만 비로소 코드를 수정하거나 다음 단계로 진행할 수 있으며, 그전에는 단 한 줄의 코드 변경 없이 철저하게 대기(Block) 상태를 유지해야 합니다.

---

## 5. Addy Osmani's Agent-Skills 7대 슬래시 명령어

에이전트는 아래의 슬래시 명령어를 수신하거나 해당 단계에 진입했을 때, 프로젝트 내 `agent-skills/skills/` 폴더 하위의 구체적인 `SKILL.md` 가이드를 성실히 수행해야 합니다.

| 명령어 | 단계 (Phase) | 역할 및 에이전트 행동 지침 | 참조 스킬 경로 |
| :--- | :--- | :--- | :--- |
| **/spec** | **Define** (명세 정의) | 작업에 착수하기 전 요구사항을 엄격하게 질의응답하여 명확히 규정하고, 모호함을 없앱니다. | `skills/spec-driven-development/SKILL.md` |
| **/plan** | **Plan** (계획 수립) | 코드 작성을 절대 먼저 시작하지 않고, 작업 목록 및 검증 가능한 마일스톤 계획을 도출합니다. | `skills/planning-and-task-breakdown/SKILL.md` |
| **/build** | **Build** (점진적 구현) | 한 번에 전체를 짜지 않고, 작은 단위로 나누어 점진적으로 코드를 구현하고 결합합니다. | `skills/incremental-implementation/SKILL.md` |
| **/test** | **Verify** (테스트 검증) | TDD 원칙을 지키며, 예상 실패 테스트를 먼저 정의하고 이를 패스시키는 검증을 반복합니다. | `skills/test-driven-development/SKILL.md` |
| **/review** | **Review** (코드 리뷰) | 시니어의 눈높이에서 아키텍처, 성능, 가독성, 예외 처리 등의 보안 및 품질 게이트를 검토합니다. | `skills/code-review-and-quality/SKILL.md` |
| **/code-simplify** | **Simplify** (코드 간소화) | 에이전트 특유의 오버엔지니어링과 장황함을 쳐내고, 코드 가독성과 간결함을 극대화합니다. | `skills/code-simplification/SKILL.md` |
| **/ship** | **Ship** (배포 및 마감) | 변경점 로그 작성, 문서화, Git 버전 커밋 메시지 규칙 준수 하에 최종 배포를 마무리합니다. | `skills/shipping-and-launch/SKILL.md` |

---

## 6. 리포트 자동 영속화 및 분류 보존 규칙 (Workspace Auto-save Rules)

에이전트는 구현 계획서 및 완수 보고서를 작성하거나 업데이트할 때마다 다음 자동 저장 및 동기화 지침을 100% 엄격하게 준수해야 합니다.

### 1) 자동 저장 및 분류 규칙
- **구현 계획서 (`implementation_plan.md`) 생성/수정 시**:
  - 작성/수정 완료 즉시 `C:\Users\jmj\Desktop\안티그래비티\new\antigravity_report\plan\` 디렉토리 하위 및 **`C:\Users\jmj\Desktop\안티그래비티\new\obsidian-vault\raw\development\` 디렉토리 하위**에 `(YYYY-MM-DD)_plan_(제목)_(수정번호).md` (예: `2026-05-23_plan_Connect-AI_v4.0_통합_구현_계획서_R4.md`) 형식의 물리 마크다운 복사본 파일을 매번 **자동으로 동시 생성 및 저장**해야 합니다.
- **완수 보고서 (`walkthrough.md`) 생성/수정 시**:
  - 작성/수정 완료 즉시 `C:\Users\jmj\Desktop\안티그래비티\new\antigravity_report\walkthrough\` 디렉토리 하위 및 **`C:\Users\jmj\Desktop\안티그래비티\new\obsidian-vault\raw\development\` 디렉토리 하위**에 `(YYYY-MM-DD)_walkthrough_(제목)_(수정번호).md` (예: `2026-05-23_walkthrough_Connect-AI_v4.0_통합_구현_완수보고서_R0.md`) 형식의 물리 마크다운 복사본 파일을 매번 **자동으로 동시 생성 및 저장**해야 합니다.

### 2) 무손실 이력 보존 규칙 (덮어쓰기 및 삭제 절대 금지)
- **이전 버전 파일 삭제 금지**: 새로운 버전(예: R0 ➡️ R1 ➡️ R2 ➡️ R3 등)의 물리 이력 파일들을 생성할 때, **이전 버전의 백업 파일들을 임의로 덮어쓰거나 삭제(Remove-Item 등)하는 행위를 일체 엄격히 금지**합니다. 
- **병존 영구 보존**: 모든 이전 리비전의 복사본 파일들은 차후 LLM 학습 및 의사결정 추적을 목적으로 **각각 고유한 수정번호 파일명을 유지한 채 병존 및 영구 보존**되어야 합니다.
- **이외 예외 없음**: 마스터 아티팩트(`implementation_plan.md`, `walkthrough.md`) 자체는 최신본으로 Overwrite 갱신이 허용되나, 리포트 물리 분류 디렉토리 경로에 분화되어 아카이빙된 누적 버전 파일들은 절대로 단 1바이트도 훼손되거나 지워져서는 안 됩니다.

### 3) 예외 없는 이행 의무
- 리포트가 아티팩트(`brain/` 하위)에만 작성되고 물리 리포트 및 **Obsidian Vault 개발 폴더(`obsidian-vault/raw/development/`) 경로**에 누락되는 현상을 원천 방지하기 위해, 모든 계획 변경 및 배포 마감 단계(/ship)에서 이 3중 동기화 쓰기를 최우선으로 일괄 처리합니다.
- 물리 파일 저장 시 파일명 내 수정번호(R0, R1, R2...)는 이전 버전의 숫자를 자동 증가하여 유일한 이력 관리가 일어나도록 제어합니다.

