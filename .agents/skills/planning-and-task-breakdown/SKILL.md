---
name: planning-and-task-breakdown
description: Breaks work into ordered tasks. Use when you have a spec or clear requirements and need to break work into implementable tasks. Use when a task feels too large to start, when you need to estimate scope, or when parallel work is possible.
---

# Planning and Task Breakdown

## Overview

Decompose work into small, verifiable tasks with explicit acceptance criteria. Good task breakdown is the difference between an agent that completes work reliably and one that produces a tangled mess. Every task should be small enough to implement, test, and verify in a single focused session.

## When to Use

- You have a spec and need to break it into implementable units
- A task feels too large or vague to start
- Work needs to be parallelized across multiple agents or sessions
- You need to communicate scope to a human
- The implementation order isn't obvious

**When NOT to use:** Single-file changes with obvious scope, or when the spec already contains well-defined tasks.

## The Planning Process

### Step 0: Pre-Planning Code Audit (기존 파일 수정 시 필수)

패치 대상 파일이 이미 존재하는 경우, 계획서 작성 전 반드시 아래를 완료해야 합니다.
**이 단계를 건너뛰면 계획서를 작성할 수 없습니다.**

- **대상 파일 전체 읽기**: 수정할 함수 전체, 기존 try-except 위치, 다중 분기(if/elif/else), 반환값 처리 패턴을 직접 확인
- **실행 경로 전수 목록화**: `main()`, `--옵션`, 스케줄러, 백그라운드 태스크 등 모든 엔트리포인트를 빠짐없이 나열
- **수정 함수별 기존 코드 인용**: 계획서 내 각 패치 지점에 수정 전 실물 코드 전체를 Before로 인용하고, 수정 후 코드를 After로 명세
- **미결 리스크 사전 인지**: 확신하지 못하는 부분을 미리 파악하여 Known Unknowns 섹션에 기재

### Step 1: Enter Plan Mode

Before writing any code, operate in read-only mode:

- Read the spec and relevant codebase sections
- Identify existing patterns and conventions
- Map dependencies between components
- Note risks and unknowns

**Do NOT write code during planning.** The output is a plan document, not implementation.

### Step 2: Identify the Dependency Graph

Map what depends on what:

```
Database schema
    │
    ├── API models/types
    │       │
    │       ├── API endpoints
    │       │       │
    │       │       └── Frontend API client
    │       │               │
    │       │               └── UI components
    │       │
    │       └── Validation logic
    │
    └── Seed data / migrations
```

Implementation order follows the dependency graph bottom-up: build foundations first.

### Step 3: Slice Vertically

Instead of building all the database, then all the API, then all the UI — build one complete feature path at a time:

**Bad (horizontal slicing):**
```
Task 1: Build entire database schema
Task 2: Build all API endpoints
Task 3: Build all UI components
Task 4: Connect everything
```

**Good (vertical slicing):**
```
Task 1: User can create an account (schema + API + UI for registration)
Task 2: User can log in (auth schema + API + UI for login)
Task 3: User can create a task (task schema + API + UI for creation)
Task 4: User can view task list (query + API + UI for list view)
```

Each vertical slice delivers working, testable functionality.

### Step 4: Write Tasks

Each task follows this structure:

```markdown
## Task [N]: [Short descriptive title]

**Description:** One paragraph explaining what this task accomplishes.

**Acceptance criteria:**
- [ ] [Specific, testable condition]
- [ ] [Specific, testable condition]

**Verification:**
- [ ] Tests pass: `npm test -- --grep "feature-name"`
- [ ] Build succeeds: `npm run build`
- [ ] Manual check: [description of what to verify]

**Dependencies:** [Task numbers this depends on, or "None"]

**Files likely touched:**
- `src/path/to/file.ts`
- `tests/path/to/test.ts`

**Estimated scope:** [Small: 1-2 files | Medium: 3-5 files | Large: 5+ files]

**Code Before/After (기존 파일 수정 시 필수):**
수정 대상 함수는 반드시 실물 코드 전체를 인용하여 Before/After 형태로 명세합니다.
"이렇게 하면 됩니다" / "여기에 추가합니다" 수준의 추상적 명세는 금지합니다.

```python
# Before (실물 코드 전체 인용)
def target_function():
    ...

# After (패치 완료 후 전체 코드)
def target_function():
    ...
```
```

### Step 5: Order and Checkpoint

Arrange tasks so that:

1. Dependencies are satisfied (build foundation first)
2. Each task leaves the system in a working state
3. Verification checkpoints occur after every 2-3 tasks
4. High-risk tasks are early (fail fast)

Add explicit checkpoints:

```markdown
## Checkpoint: After Tasks 1-3
- [ ] All tests pass
- [ ] Application builds without errors
- [ ] Core user flow works end-to-end
- [ ] Review with human before proceeding
```

## Task Sizing Guidelines

| Size | Files | Scope | Example |
|------|-------|-------|---------|
| **XS** | 1 | Single function or config change | Add a validation rule |
| **S** | 1-2 | One component or endpoint | Add a new API endpoint |
| **M** | 3-5 | One feature slice | User registration flow |
| **L** | 5-8 | Multi-component feature | Search with filtering and pagination |
| **XL** | 8+ | **Too large — break it down further** | — |

If a task is L or larger, it should be broken into smaller tasks. An agent performs best on S and M tasks.

**When to break a task down further:**
- It would take more than one focused session (roughly 2+ hours of agent work)
- You cannot describe the acceptance criteria in 3 or fewer bullet points
- It touches two or more independent subsystems (e.g., auth and billing)
- You find yourself writing "and" in the task title (a sign it is two tasks)

## Plan Document Template

```markdown
# Implementation Plan: [Feature/Project Name]

## Overview
[One paragraph summary of what we're building]

## Architecture Decisions
- [Key decision 1 and rationale]
- [Key decision 2 and rationale]

## Task List

### Phase 1: Foundation
- [ ] Task 1: ...
- [ ] Task 2: ...

### Checkpoint: Foundation
- [ ] Tests pass, builds clean

### Phase 2: Core Features
- [ ] Task 3: ...
- [ ] Task 4: ...

### Checkpoint: Core Features
- [ ] End-to-end flow works

### Phase 3: Polish
- [ ] Task 5: ...
- [ ] Task 6: ...

### Checkpoint: Complete
- [ ] All acceptance criteria met
- [ ] Ready for review

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| [Risk] | [High/Med/Low] | [Strategy] |

## Known Unknowns (작성 필수 — 비워두기 금지)
계획 작성 시점에 확신하지 못하는 부분을 솔직하게 기재합니다.
"없음"으로 처리하는 것은 허용되지 않습니다. 확신이 100%인 계획은 존재하지 않습니다.

- [ ] [이 부분의 기존 코드 구조를 완전히 파악했는가?]
- [ ] [모든 실행 경로를 빠짐없이 점검했는가?]
- [ ] [수정 후 영향받는 다른 모듈이 없는가?]

## Open Questions
- [Question needing human input]
```

## Parallelization Opportunities

When multiple agents or sessions are available:

- **Safe to parallelize:** Independent feature slices, tests for already-implemented features, documentation
- **Must be sequential:** Database migrations, shared state changes, dependency chains
- **Needs coordination:** Features that share an API contract (define the contract first, then parallelize)

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll figure it out as I go" | That's how you end up with a tangled mess and rework. 10 minutes of planning saves hours. |
| "The tasks are obvious" | Write them down anyway. Explicit tasks surface hidden dependencies and forgotten edge cases. |
| "Planning is overhead" | Planning is the task. Implementation without a plan is just typing. |
| "I can hold it all in my head" | Context windows are finite. Written plans survive session boundaries and compaction. |

## Red Flags

- Starting implementation without a written task list
- Tasks that say "implement the feature" without acceptance criteria
- No verification steps in the plan
- All tasks are XL-sized
- No checkpoints between tasks
- Dependency order isn't considered
- **기존 파일 수정인데 대상 파일을 읽지 않고 계획서를 작성함** → 실물 코드와 충돌하는 명세가 반드시 발생
- **"완전무결", "제로화", "남김없이 완벽", "단 하나의 에러도 없이"** 등의 자기완성도 선언 표현 사용 → 검증 없는 과장이며 다음 리뷰에서 반드시 지적됨
- **복잡한 함수에 "이렇게 추가하면 됩니다" 수준의 추상적 명세** → 구현자가 직접 판단해야 하는 모호함을 만들어 구현 오류의 원인이 됨
- **Known Unknowns 섹션이 비어 있거나 "없음"으로 처리됨** → 계획의 완성도를 과장하는 신호

## Verification

Before starting implementation, confirm:

- [ ] Every task has acceptance criteria
- [ ] Every task has a verification step
- [ ] Task dependencies are identified and ordered correctly
- [ ] No task touches more than ~5 files
- [ ] Checkpoints exist between major phases
- [ ] The human has reviewed and approved the plan
- [ ] **(기존 파일 수정 시)** 모든 패치 대상 파일을 직접 읽었는가
- [ ] **(기존 파일 수정 시)** 수정할 모든 함수에 Before/After 코드 스니펫이 있는가
- [ ] **(기존 파일 수정 시)** 모든 실행 엔트리포인트를 점검했는가
- [ ] Known Unknowns 섹션이 작성되어 있는가 ("없음" 불허)
- [ ] "완전무결" 계열 자기완성도 선언 표현을 제거했는가
