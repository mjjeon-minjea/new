import glob
import re
from pathlib import Path

raw_dir = Path("obsidian-vault/raw")
all_files = list(raw_dir.glob("*.md"))

print(f"[*] 총 {len(all_files)}개의 원시 뉴스 기사 파일 보정 작업을 시작합니다...")

keywords_to_link = {
    "비트코인": "Bitcoin",
    "Bitcoin": "Bitcoin",
    "BTC": "Bitcoin",
    "연준": "US-Fed",
    "미국 연방준비제도": "US-Fed",
    "Federal Reserve": "US-Fed",
    "US-Fed": "US-Fed",
    "FOMC": "US-Fed",
    "기준금리": "US-Fed",
    "한국 경제": "Korea-Economy",
    "Korea-Economy": "Korea-Economy",
    "Polymarket": "Polymarket",
    "폴리마켓": "Polymarket",
    "Kalshi": "Kalshi",
    "칼시": "Kalshi",
    "SEC": "US-Fed"
}

success_count = 0
for f in all_files:
    try:
        with open(f, "r", encoding="utf-8") as file:
            text = file.read()
            
        # 1. 단일 대괄호를 이중 대괄호로 치환
        text = re.sub(r'(?<!\[)\[([a-zA-Z가-힣0-9\s\-\.\_]+)\](?!\])', r'[[\1]]', text)
        
        # 2. 주요 핵심 용어가 대괄호 바깥에 있는 경우 이중 대괄호 링크 강제 주입
        for kw, target in keywords_to_link.items():
            pattern = re.compile(rf'(?<!\[){re.escape(kw)}(?!\])')
            text = pattern.sub(f"[[{target}]]", text)
            
        # 3. 불필요하게 겹친 대괄호 정리 및 이중화 무결성 유지 (예: [[[[US-Fed]]]] 등 방지)
        text = re.sub(r'\[{3,}', '[[', text)
        text = re.sub(r'\]{3,}', ']]', text)
        
        with open(f, "w", encoding="utf-8") as file:
            file.write(text)
        success_count += 1
    except Exception as e:
        print(f"[!] 파일 {f.name} 보정 중 오류 발생: {e}")

print(f"[★ 성공] 총 {success_count}개 파일의 이중 대괄호 위키링크 보정 완수!")
