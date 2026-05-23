import re
from datetime import datetime

def escape_markdown_for_telegram(text: str) -> str:
    """텔레그램 마크다운 구문 에러 방지를 위해 크로스링크 대괄호 제거 및 마크다운 기호 정제"""
    # 1. 옵시디언 크로스링크 이중 대괄호 제거: [[Bitcoin]] -> Bitcoin
    text = re.sub(r'\[\[(.*?)\]\]', r'\1', text)
    # 2. 볼드(*), 이탤릭(_), 백틱(`) 등 텔레그램 마크다운 충돌 기호 제거
    text = text.replace("*", "").replace("_", "").replace("`", "")
    return text

def clean_filename(filename: str) -> str:
    """윈도우 파일 시스템에서 허용되지 않는 특수문자 정제"""
    cleaned = re.sub(r'[\x00-\x1f\\/:*?"<>|]', '_', filename)
    # 공백 연속 제거 및 양끝 공백 제거
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned[:80]  # 파일명 길이 제한

def post_process_links(text: str) -> str:
    """단일 대괄호 [Keyword]를 옵시디언용 이중 대괄호 [[Keyword]]로 보정하고 주요 용어를 위키 링크로 후처리"""
    # 1. 기존의 잘못 생성된 [[ [Keyword] ]] 같은 삼중 괄호 보정
    text = re.sub(r'\[\[\s*\[(.*?)\]\s*\]\]', r'[[\1]]', text)
    
    # 2. [비트코인] 또는 [금리] 형태로 잡힌 단일 대괄호들을 이중 대괄호 위키 링크로 변환
    # 단, 외부 링크 형식인 [텍스트](http...) 형태는 제외해야 함
    text = re.sub(r'(?<!\!)(?<!\[)\[([^\]\n]+?)\](?!\])(?!\s*\()', r'[[\1]]', text)
    
    # 3. 주요 필수 연동 금융 지명 키워드들 강제 위키 링크화
    keywords = ["비트코인", "연준", "금리", "인플레이션", "미국 경제", "한국 경제", "FOMC", "환율", "삼성전자", "반도체"]
    for kw in keywords:
        # 단, 이미 [[kw]] 형태이거나 대괄호 안에 들어있지 않은 경우에만 치환
        # 복잡한 정규식보다는 간단히 경계 체크
        pattern = re.compile(rf'(?<!\[\[)(?<!\[){kw}(?!\]\])(?!\])', re.IGNORECASE)
        text = pattern.sub(f"[[{kw}]]", text)
        
    return text

def parse_rss_date(date_str: str) -> str:
    """RSS 및 API 날짜 포맷을 YYYY-MM-DD HH:MM:SS 로 일관되게 변환"""
    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S"
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    # 정규식으로 앞쪽 YYYY-MM-DD 부분만이라도 추출 시도
    date_match = re.match(r'^(\d{4}-\d{2}-\d{2})', date_str)
    if date_match:
        return f"{date_match.group(1)} 00:00:00"
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
