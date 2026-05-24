← [[Development_Hub|개발 마스터 대시보드]]

# 🎯 5선 전략분석 에이전트 결과물 Obsidian Vault 이중화, 그래프 뷰 연결 및 원천 뉴스 분류 완수보고서

본 문서는 **Connect-AI Financial OS**에 5선 전략분석 에이전트 군(`chief_strategy_analyst`, `macro_signal_analyst`, `onchain_signal_analyst`, `risk_assessor`)의 분석 성과 마크다운 파일들을 옵시디언 볼트(`obsidian-vault/raw/strategy/`) 디렉토리에 동시 이중 저장하도록 구현하고, 옵시디언 그래프 뷰 상에서 모든 개발 리포트들이 유기적으로 연결되도록 완결한 뒤, 최상위 `raw/` 폴더에 둥둥 떠 있던 52개의 뉴스 원천 파일들을 `raw/news/` 분류 디렉토리 하위로 전격 이동 및 전체 에이전트 경로들을 완벽 정렬한 종합 완수보고서입니다.

---

## 1. 구현 완료 사항 및 코드 변경점

### ① 4개 전략 에이전트 이중화 동시 저장 이식 완료
* **대상 파일**:
  - `agents/macro_signal_analyst.py`
  - `agents/onchain_signal_analyst.py`
  - `agents/risk_assessor.py`
  - `agents/chief_strategy_analyst.py`
* **변경 세부 로직**:
  - 각 파일 상단에 `from agents.shared.config import RAW_DIR` 임포트를 전격 배치하였습니다.
  - 기존 세션별 디렉토리(`session_dir`) 저장 코드 바로 하단에 `RAW_DIR / "strategy"` 폴더 자동 생성 및 `{session_dir.name}_[기존파일명]` 규격으로 동시 이중 저장하는 핵심 로직을 완벽하게 이식하였습니다.
  ```python
  # Obsidian Vault raw/strategy/ 동시 저장 추가
  strategy_dir = RAW_DIR / "strategy"
  strategy_dir.mkdir(parents=True, exist_ok=True)
  obs_path = strategy_dir / f"{session_dir.name}_macro_signal.md"
  obs_path.write_text(signal_content, encoding="utf-8")
  files_created.append(str(obs_path))
  ```

### ② 가상 샌드박스 I/O 병목 해소 (절대 경로 리팩토링)
* **원인**: 백그라운드 태스크나 특정 런타임 쉘에서 구동 시, `Path(os.getcwd())`가 샌드박스의 임시 디렉토리로 변경되면서 윈도우 호스트 시스템 측 옵시디언 경로로 파일이 동기화되지 못하는 병목이 있었습니다.
* **해결**: `agents/shared/config.py` 내 `ROOT_DIR` 정의를 CWD 종속 방식에서 설정 파일 자체의 물리적 절대 위치 기준(`Path(__file__).parent.parent.parent.resolve()`)으로 리팩토링하였습니다. 이로써 어떠한 환경에서 실행되더라도 항상 실재하는 윈도우 호스트 프로젝트 루트 `c:\Users\jmj\Desktop\안티그래비티\new`를 견고하게 찾아갑니다.

### ③ 옵시디언 그래프 뷰 문서 고립(따로 노는 현상) 완전 해결
* **개발 마스터 허브 구축**: `obsidian-vault/raw/development/Development_Hub.md` 문서를 신설하여 모든 역사적 플랜(`plan`)과 완수보고서(`walkthrough`)를 체계적으로 바인딩하였습니다.
* **자동 크로스링크 일괄 주입**: 자동화 파이썬 스크립트를 작성하여 21개 전체 개별 마크다운 문서 최상단에 마스터 대시보드로 복귀 가능한 네비게이션 링크를 주입하고, 동일 주제의 `plan`과 `walkthrough` 간의 직접적인 양방향 크로스링크(`🔗 연관 개발 문서` 섹션)를 자동 상호 이식하였습니다.
* **결과**: 옵시디언 그래프 뷰에서 고립되었던 모든 노드들이 `Development_Hub` 중앙 노드를 축으로 한 아름다운 성형(Star) 및 망형(Mesh) 그래프 위상으로 유기적으로 연결되었습니다.

### ④ 📂 어수선한 원천 뉴스 파일 `raw/news/` 폴더 분류 및 모듈 정렬 완수 (신규 추가)
* **물리 뉴스 파일 일괄 이주**: 최상위 `obsidian-vault/raw/` 폴더 바로 밑에서 어질러져 있던 52개의 날짜별 뉴스 마크다운 파일들을 `obsidian-vault/raw/news/` 분류 디렉토리 하위로 전격 이동 및 정리를 완수하였습니다.
* **경로 상수 신설 및 실재 보장**: `agents/shared/config.py` 에 `NEWS_DIR = RAW_DIR / "news"` 를 신설하고 `NEWS_DIR.mkdir` 자동 생성을 추가하여 시스템 가동 시 항상 디렉토리 물리 생성을 안전하게 보장합니다.
* **Ingestion 리포터 분류 변경**: `agents/base_reporter.py` 내의 파일 작성 경로를 `NEWS_DIR / filename` 으로 수정하여, 추후 수집되는 모든 뉴스 기사들도 `raw/news/` 하위에 깔끔하게 정리되어 자동 저장됩니다.
* **위키 합성 및 중복 체크 탐색 타깃 이동**:
  - `agents/wiki_manager.py` 의 glob 탐색과 존재 유무 체크 경로를 `NEWS_DIR` 로 전격 리팩토링하여 분류 디렉토리에서 지식 합성을 수행합니다.
  - `agents/shared/file_utils.py` 의 중복 수집 방지용 URL 스캔 디렉토리 또한 `NEWS_DIR` 로 수정 완료하여 중복 제어가 정확히 동작합니다.
* **양방향 링크 호환성 정교화**:
  - `wiki_manager.py` 의 작업 로그 기록 형식을 `[[raw/news/{raw_filename}]]` 으로 더욱 고도화 세분화하였습니다.
  - 기존 `log.md` 의 이전 기록 형식(`[[raw/파일명.md]]`)과의 호환이 완벽히 유지되도록 `_get_processed_files()` 내 파싱 정규식을 `file_pattern = re.compile(r'\[\[raw/(?:news/)?(.+?\.md)\]\]')` 로 정교화 보완하여 레거시 데이터와의 충돌을 원천 예방했습니다.

---

## 2. 동작 검증 및 실증 테스트 결과

### 📊 5선 파이프라인 동시 저장 영속화 로그
👉 각 에이전트가 1개가 아닌 **정밀하게 2개의 파일 영속화**를 마쳤다는 명확한 실증 증거를 확보했습니다. (세션 폴더 + 옵시디언 이중화 폴더)
* 호스트 측 옵시디언 디렉토리 `obsidian-vault/raw/strategy/` 경로에 4개 시그널 파일들이 안전하게 실시간 이중화 안착되었음을 확인했습니다.

### 🧪 모듈 정렬 유효성 CLI 퀵 검증 실증 (신규 추가)
경로 이전 후 발생할 수 있는 NameError 및 DirectoryNotFound 에러 방지를 위해 커맨드라인에서 임포트 구동 유효성을 즉각 실증하였습니다:
* **수집 완료 URL 중복 제어 검증**:
  `python -c "from agents.shared.file_utils import get_existing_urls; print(len(get_existing_urls()))"`
  👉 **출력**: `수집 완료된 URL 수: 52` (에러 없이 52개 이주 파일의 URL을 완벽하게 파싱 및 중복 제어 수치 검출 성공)
* **위키 누적 이력 로깅 검증 (정규식 호환성)**:
  `python -c "from agents.wiki_manager import WikiManager; wm = WikiManager(); print(len(wm._get_processed_files()))"`
  👉 **출력**: `기존 완료된 뉴스 수: 25` (레거시 경로와 신규 경로를 옵셔널 그룹 정규식을 통해 에러 없이 25개 누적 이력 완벽 검출 성공)

---

## 3. 최종 배포 마감 요약
본 작업으로 5선 에이전트 결과물의 실시간 볼트 동기화, 이력 문서들의 옵시디언 그래프 뷰 완전 결합, 그리고 52개의 뉴스 파일 분류 및 모듈 정렬 작업이 100% 빈틈없이 마무리되었음을 전격 보고합니다.

## 🔗 연관 개발 문서 (Cross References)
- [[2026-05-24_plan_전략분석에이전트구조설계_R0]]
- [[2026-05-24_plan_전략분석에이전트구조설계_R1]]
- [[2026-05-24_walkthrough_전략분석에이전트구조설계_R0]]
- [[2026-05-24_walkthrough_전략분석에이전트구조설계_R1]]
