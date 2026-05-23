# Obsidian LLM Wiki Schema & Guidelines

이 문서는 Karpathy LLM Wiki 방식을 준수하여 본 지식 저장소(Obsidian Vault)를 유지 관리하는 에이전트(LLM)용 지침서이자 스키마 규칙입니다. 에이전트는 기사 분석 및 위키 업데이트 시 이 규칙을 엄격히 준수해야 합니다.

---

## 1. 저장소 구조 (Directory Structure)
- `raw/`: 수집된 원본 뉴스 기사들이 마크다운 형식으로 적재되는 불변(Immutable) 레이어입니다.
  - 파일명 형식: `[YYYY-MM-DD]_[기사제목].md`
  - YAML Frontmatter: 기사의 원본 링크(`url`), 언론사(`source`), 카테고리(`category`), 게시일(`published_at`)이 포함됩니다.
- `wiki/`: LLM에 의해 지속적으로 작성, 수정 및 점진적으로 누적(Compounding)되는 지식 레이어입니다.
  - `SCHEMA.md`: 본 규칙서 (정적 파일)
  - `index.md`: 카테고리별 위키 페이지 카탈로그 및 색인
  - `log.md`: append-only 형식의 시간 순서 작업 로그
  - `[주제/엔티티].md`: 각 주제어(예: `Bitcoin.md`, `US-Fed.md`, `Korea-Economy.md`)별 지식 누적 문서

---

## 2. 위키 업데이트 & 지식 누적 규칙 (Compounding Rules)
1. **단순 요약 금지**: 기사 하나당 요약 파일 하나를 새로 만드는 RAG 방식이 아닙니다. 새로운 정보가 수집되면, 기존의 위키 주제 문서(예: `Bitcoin.md`)에 내용을 **덧붙이고 수정하여 점진적으로 지식을 쌓아 올립니다.**
2. **크로스 레퍼런스(Cross-Reference) 연결**: 본문 작성 시 관련이 있거나 새로이 다루어진 엔티티는 대괄호 두 개(`[[주제명]]`)를 감싸서 옵시디언 링크를 만들어 줍니다. (예: `[[US-Fed]]의 금리 인상이 [[Bitcoin]] 시장에 미친 영향...`)
3. **모순 및 변화 지점(Contradictions) 탐지**: 기존 위키 페이지에 기록된 정보와 새로운 뉴스의 정보가 서로 모순되거나 주장이 달라졌다면, 기존 정보를 무작정 지우는 대신 **"지식의 변화 흐름"**으로 정리하여 기록합니다.
   - 예: "2026-05-10: 연준 금리 인하 가능성 제기 -> 2026-05-22: 연준 매파적 입장 고수로 금리 동결 유력"
4. **YAML Frontmatter 작성 규칙**:
   - 모든 위키 페이지 상단에 YAML Frontmatter를 포함하여 Dataview 플러그인에서 원활히 다룰 수 있도록 구성합니다.
   - 필수 필드: `type` (wiki), `tags` (주제 관련 태그), `last_updated` (최종 갱신 일자), `sources_count` (참조된 raw 기사 개수)

---

## 3. 특수 파일 관리 서식

### index.md (콘텐츠 카탈로그)
* 매번 위키 페이지가 생성되거나 업데이트될 때 카테고리별 색인 맵을 갱신합니다.
* 형식 예시:
  ```markdown
  # LLM Wiki Index
  
  ## 🪙 디지털 자산 및 비트코인
  - [[Bitcoin]] - 비트코인 시세 흐름, 반감기 및 온체인 지표 종합 요약.
  
  ## 🌍 글로벌 경제
  - [[US-Fed]] - 미국 연방준비제도 금리 결정, FOMC 성명서 분석 및 인플레이션 전망.
  ```

### log.md (Chronological Log)
* 작업이 일어날 때마다 최하단에 한 줄씩 이벤트를 append-only로 추가합니다.
* 형식 예시:
  ```markdown
  # Chronological Activity Log
  
  ## [2026-05-23 05:10] ingest | [[raw/[2026-05-23]_비트코인_10만달러_돌파.md]] 수집 및 [[Bitcoin]] 위키 페이지 갱신
  ```
