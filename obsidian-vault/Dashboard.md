# 📊 로컬 AI 에이전트 LLM Wiki 종합 대시보드

> [!NOTE]
> 본 대시보드는 로컬 뉴스 수집기(`scraper.py`)와 AI 분석기(`analyzer.py`)가 실시간으로 수집하고 누적 요약(Compounding)한 로컬 지식들을 한눈에 조망할 수 있는 허브(Hub) 공간입니다.

---

## 🪙 핵심 지식 위키 현황 (Compounding Wiki Pages)

옵시디언의 **Dataview** 플러그인을 활용하여 실시간으로 업데이트되는 위키 지식들의 현황입니다.
*(아래 표는 Dataview 플러그인이 활성화되어 있을 때 동적으로 렌더링됩니다)*

```dataview
TABLE last_updated AS "**최종 업데이트**", sources_count AS "**누적 분석 기사 수**", tags AS "**연관 태그**"
FROM "wiki"
WHERE type = "wiki"
SORT last_updated DESC
```

---

## 📥 최근 수집된 불변 원시 뉴스 (Immutable Raw Sources)

에이전트가 RSS 및 구글 뉴스로부터 실시간으로 긁어온 원시 기사 목록입니다.

```dataview
TABLE source AS "**언론사**", category AS "**분류**", published_at AS "**게시 시간**"
FROM "raw"
SORT file.ctime DESC
LIMIT 10
```

---

## 📋 에이전트 실시간 활동 로그 (Activity Timeline)

최근 로컬 AI 에이전트가 수행한 수집 및 위키 문서 갱신 타임라인입니다.

```dataview
LIST FROM "wiki"
WHERE file.name = "log"
```

---

## 💡 대시보드 뷰 정상 렌더링을 위한 가이드

본 종합 대시보드와 동적 테이블 표가 옵시디언 내에서 완벽하게 표시되도록 아래 플러그인을 활성화해 주세요:

1. **Dataview 플러그인 설치**:
   - 옵시디언 **설정(Settings) ⚙️** -> **커뮤니티 플러그인(Community Plugins)**으로 이동합니다.
   - 커뮤니티 플러그인 활성화를 켠 뒤, **탐색(Browse)** 버튼을 누릅니다.
   - 검색창에 `Dataview`를 입력하고 설치 및 활성화(Enable)합니다.
   - Dataview 설정 화면에서 `Enable JavaScript Queries` 및 `Enable Inline Queries`가 활성화되어 있는지 확인합니다.
2. **그래프 뷰(Graph View) 연동**:
   - 좌측 사이드바의 **그래프 뷰 열기(Open Graph View)** 아이콘을 클릭합니다.
   - `obsidian-vault/raw/` 기사들과 `obsidian-vault/wiki/` 지식 간에 연결된 촘촘한 **연관 지식 네트워크**를 시각적으로 확인하실 수 있습니다. AI 에이전트가 기사를 분석할 때마다 링크가 확장되며 컴파운딩되는 역동적인 그래프가 완성됩니다.
3. **Marp 슬라이드 변환 (Marp)**:
   - 각 위키 페이지를 기반으로 프리젠테이션 슬라이드를 생성하려면, 옵시디언의 `Marp` 플러그인을 활성화하고 위키 본문을 마크다운 슬라이드로 바로 변환하여 활용하세요.
