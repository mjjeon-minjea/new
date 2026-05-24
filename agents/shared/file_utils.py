import re
from pathlib import Path
from agents.shared.config import NEWS_DIR

def write_file_safely(file_path: Path, content: str):
    """
    원자적(Atomic) 안전 쓰기 메커니즘.
    쓰기 도중 크래시 발생 시 데이터 손상을 원천 예방하기 위해
    기존 원본의 백업(.bak) 복사본을 생성하고 쓰기 성공 시에만 삭제합니다.
    """
    bak_path = file_path.with_suffix(file_path.suffix + ".bak")
    
    # 1. 기존 파일이 존재하면 백업 복사본 생성
    if file_path.exists():
        try:
            if bak_path.exists():
                bak_path.unlink()
            file_path.rename(bak_path)
        except Exception as e:
            print(f"[!] 백업본 파일 생성 실패 ({file_path.name}): {e}")
            
    # 2. 새 파일 작성
    try:
        # 부모 디렉토리 실재 보장
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        # 3. 작성 성공 시 백업본 영구 삭제
        if bak_path.exists():
            bak_path.unlink()
    except Exception as e:
        print(f"[!] 파일 쓰기 중 오류 발생! 원본 백원을 복원합니다. 에러: {e}")
        if bak_path.exists():
            if file_path.exists():
                file_path.unlink()
            bak_path.rename(file_path)
        raise e

def get_existing_urls() -> set:
    """이미 Ingestion 완료되어 raw/ 폴더 아래 저장된 기사들의 URL 목록을 추출해 중복 수집을 원천 방지"""
    existing_urls = set()
    if not NEWS_DIR.exists():
        return existing_urls
        
    url_pattern = re.compile(r'^url:\s*["\']?(.*?)["\']?\s*$', re.MULTILINE)
    
    for file in NEWS_DIR.glob("*.md"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
                # 앞쪽 YAML Frontmatter 영역만 파싱
                match = url_pattern.search(content)
                if match:
                    existing_urls.add(match.group(1).strip())
        except Exception as e:
            print(f"[!] 파일 {file.name} 읽기 및 URL 중복 검사 파싱 오류: {e}")
            
    return existing_urls
