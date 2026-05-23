import os
import sys
import re
import json
from datetime import datetime
from pathlib import Path
import requests
from dotenv import load_dotenv

# 윈도우 환경 콘솔 출력 인코딩 에러 방지
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# .env 로드
load_dotenv()

# 경로 설정
vault_path_str = os.getenv("OBSIDIAN_VAULT_PATH", "obsidian-vault")
vault_path = Path(vault_path_str).resolve()
raw_dir = vault_path / "raw"
wiki_dir = vault_path / "wiki"

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e4b")

# AI 호출 시 속도를 위해 gemma2:2b 가 있는지 먼저 확인하고 있다면 우선 적용, 없으면 설정된 고성능 gemma4:e4b 사용
ENRICH_MODEL = OLLAMA_MODEL

def check_and_select_model():
    """로컬 Ollama API 서버 연결성 체크 및 Enrichment에 사용할 최적의 모델 선정"""
    global ENRICH_MODEL
    try:
        response = requests.get(f"{OLLAMA_API_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models_data = response.json()
            available_models = [m["name"] for m in models_data.get("models", [])]
            print(f"[*] 로컬 Ollama 가용한 모델 목록: {available_models}")
            
            # gemma2:2b 계열이 있다면 속도를 위해 마이그레이션 및 수집 보정용으로 최우선 선정
            gemma2_models = [m for m in available_models if "gemma2" in m]
            if gemma2_models:
                ENRICH_MODEL = gemma2_models[0]
                print(f"[*] 속도 최적화를 위해 경량 AI 모델 '{ENRICH_MODEL}'을 Enrichment 엔진으로 자동 선정합니다.")
            else:
                # 사용자가 지정한 모델명이 태그 목록에 존재하는지 확인
                if OLLAMA_MODEL in available_models:
                    ENRICH_MODEL = OLLAMA_MODEL
                else:
                    matching = [m for m in available_models if m.startswith(OLLAMA_MODEL)]
                    if matching:
                        ENRICH_MODEL = matching[0]
                    elif available_models:
                        ENRICH_MODEL = available_models[0]
                print(f"[*] 설정된 기본 모델 '{ENRICH_MODEL}'을 Enrichment 엔진으로 선정합니다.")
            return True
        return False
    except Exception as e:
        print(f"[!] Ollama 연결 실패: {e}")
        return False

def call_ollama_json(prompt: str, system_prompt: str = "") -> dict:
    """Ollama API를 통해 JSON 형식으로 응답받아 파싱 후 딕셔너리로 반환"""
    url = f"{OLLAMA_API_URL}/api/generate"
    payload = {
        "model": ENRICH_MODEL,
        "prompt": prompt,
        "system": system_prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.3,
            "top_p": 0.9,
            "num_predict": 2048
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=90)
        if response.status_code == 200:
            res_json = response.json()
            response_text = res_json.get("response", "").strip()
            # JSON 파싱 시도
            return json.loads(response_text)
        else:
            print(f"  [!] Ollama API 에러: HTTP {response.status_code}")
            return {}
    except Exception as e:
        print(f"  [!] Ollama JSON 호출 예외 발생: {e}")
        return {}

def post_process_links(text: str) -> str:
    """단일 대괄호 [Keyword]를 옵시디언용 이중 대괄호 [[Keyword]]로 보정하고 주요 용어를 위키 링크로 후처리"""
    # 1. 단일 대괄호 [Keyword]를 [[Keyword]]로 보정 (이미 [[...]]인 것은 제외)
    text = re.sub(r'(?<!\[)\[([a-zA-Z가-힣0-9\s\-\.\_]+)\](?!\])', r'[[\1]]', text)
    
    # 2. 주요 핵심 용어가 대괄호 바깥에 있는 경우 이중 대괄호 링크 강제 주입
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
    
    for kw, target in keywords_to_link.items():
        # 대괄호 [[...]] 로 감싸여 있지 않은 용어만 찾아서 [[target]]으로 치환
        pattern = re.compile(rf'(?<!\[){re.escape(kw)}(?!\])')
        text = pattern.sub(f"[[{target}]]", text)
        
    # 3. 불필요하게 겹친 대괄호 정리 및 이중화 무결성 유지 (예: [[[[US-Fed]]]] 등 방지)
    text = re.sub(r'\[{3,}', '[[', text)
    text = re.sub(r'\]{3,}', ']]', text)
    return text

def clean_filename(filename: str) -> str:
    """윈도우 파일 시스템에서 허용되지 않는 특수문자 정제"""
    cleaned = re.sub(r'[\x00-\x1f\\/:*?"<>|]', '_', filename)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned[:80]

def is_english_content(text: str) -> bool:
    """텍스트가 주로 영어로 작성되었는지 판별 (알파벳 비율 기준)"""
    alphabets = len(re.findall(r'[a-zA-Z]', text))
    korean = len(re.findall(r'[ㄱ-ㅎㅏ-ㅣ가-힣]', text))
    total = alphabets + korean
    if total == 0:
        return False
    return (alphabets / total) > 0.65

def detect_migration_need(file_path: Path, content: str) -> tuple:
    """
    기존 파일에 마이그레이션(한글화, 내용 보정, 태그 및 링크 주입)이 필요한지 여부 판별.
    반환값: (필요여부, 사유)
    """
    # Frontmatter 및 본문 추출
    yaml_pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n(.*)$', re.DOTALL | re.MULTILINE)
    match = yaml_pattern.match(content)
    
    frontmatter = ""
    body = content
    if match:
        frontmatter = match.group(1)
        body = match.group(2)
        
    # 1. 언어 검사
    lang_match = re.search(r'language:\s*["\']?(.*?)["\']?\s*$', frontmatter, re.MULTILINE)
    lang = lang_match.group(1).strip() if lang_match else "ko"
    
    if lang == "en" or is_english_content(body) or is_english_content(file_path.stem):
        return True, "영문 기사 (한글화 필요)"
        
    # 2. 내용 빈약성 검사 (본문이 250자 미만인 경우)
    # ## 기사 본문 이후 영역 추출
    body_content = body
    if "## 기사 본문" in body:
        body_content = body.split("## 기사 본문")[-1].strip()
    
    if len(body_content) < 250:
        return True, f"내용 빈약 ({len(body_content)}자)"
        
    # 3. 연결망 누락 검사 (태그 및 대괄호 링크 [[...]] 누락)
    has_tags = "tags:" in frontmatter or "#" in body
    has_links = "[[" in body
    
    if not has_tags or not has_links:
        return True, "옵시디언 연결망(태그/크로스링크) 누락"
        
    return False, "양호 (마이그레이션 불필요)"

def update_references_in_wiki(old_filename: str, new_filename: str):
    """Vault 내의 모든 마크다운 파일(.md)에서 구 파일명 참조 링크를 새 파일명 링크로 자동 치환"""
    old_link = f"[[raw/{old_filename}]]"
    new_link = f"[[raw/{new_filename}]]"
    
    # wiki 폴더뿐만 아니라 vault 하위 전체 .md 스캔하여 치환 (참조 무결성 철저 보장)
    for path in vault_path.glob("**/*.md"):
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                if old_link in content:
                    updated_content = content.replace(old_link, new_link)
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(updated_content)
                    rel_path = path.relative_to(vault_path)
                    print(f"    [치환 성공] {rel_path} 내 링크 치환 완료: {old_link} -> {new_link}")
            except Exception as e:
                print(f"    [!] {path.name} 내 링크 치환 중 오류 발생: {e}")

def run_migration():
    print("\n" + "="*60)
    print("[*] 기존 수집 기사(raw/) 일괄 지능형 마이그레이션 엔진 가동")
    print("="*60 + "\n")
    
    if not check_and_select_model():
        print("[!] 로컬 Ollama API 서버가 켜져 있지 않거나 가용한 모델이 없어 중단합니다.")
        return
        
    if not raw_dir.exists():
        print(f"[!] 원시 기사 디렉토리({raw_dir})가 존재하지 않습니다.")
        return
        
    all_files = sorted(list(raw_dir.glob("*.md")))
    print(f"[*] raw/ 폴더 내 전체 기사 수: {len(all_files)}개")
    
    migration_targets = []
    for file_path in all_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            need_mig, reason = detect_migration_need(file_path, content)
            if need_mig:
                migration_targets.append((file_path, content, reason))
        except Exception as e:
            print(f"[!] 파일 {file_path.name} 읽기 중 예외 발생: {e}")
            
    print(f"[*] 마이그레이션 대상 기사: {len(migration_targets)}개 / {len(all_files)}개")
    if not migration_targets:
        print("[*] 마이그레이션이 필요한 파일이 없습니다. 작업을 종료합니다.")
        return
        
    system_prompt = """당신은 세계 최고의 금융 및 가상자산 전문 애널리스트이자 지식 정리 에이전트입니다.
입력된 뉴스 기사의 메타데이터와 본문을 바탕으로, 금융 전문 용어 매핑 룰을 반영해 고품질의 한국어 마크다운용 요소들을 JSON 형식으로 정확히 생성해야 합니다.

* 필수 금융/크립토 한글 용어 매핑 규칙:
  - Fed / US Federal Reserve / Federal Reserve -> '미국 연방준비제도(연준)'
  - FOMC -> '연방공개시장위원회(FOMC)'
  - SEC -> '미국 증권거래위원회(SEC)'
  - ETF -> '상장지수펀드(ETF)'
  - Rate Cut -> '기준금리 인하'
  - Rate Hike -> '기준금리 인상'
  - Hawkish -> '매파적(긴축 선호)'
  - Dovish -> '비둘기파적(완화 선호)'
  - Halving -> '반감기'
  - Whale -> '고래(대형 투자자)'
  - Bull Market -> '강세장 / 상승장'
  - Bear Market -> '약세장 / 하락장'
  - Inflation / CPI -> '인플레이션 / 소비자물가지수(CPI)'
  - Insider Trading -> '내부자 거래'
  - Prediction Market -> '예측 시장'
  
응답은 반드시 아래 JSON 스키마 포맷을 100% 만족해야 하며, 마크다운이나 인사말 등 부가 설명은 절대 작성하지 마십시오:
{
  "translated_title": "자연스럽고 품격 있는 한국어 번역 기사 제목 (금융 용어 매핑 준수)",
  "enriched_body": "한글화 및 풍부하게 요약·분석 보정된 본문 (만약 본문이 짧다면 금융 지식을 결합해 3문장 이상의 상세한 뉴스 요약 및 시장 파급 효과 금융 분석으로 풍성하게 기술. 관련 핵심 키워드인 비트코인, 연준, 금리 등에는 반드시 [[Bitcoin]], [[US-Fed]], [[Korea-Economy]] 등 옵시디언 크로스링크 대괄호를 적절히 주입하여 작성)",
  "extracted_tags": ["추출된 핵심 영어 태그1", "태그2", "태그3"]
}
"""

    success_count = 0
    for idx, (file_path, original_content, reason) in enumerate(migration_targets, 1):
        print(f"\n[{idx}/{len(migration_targets)}] 마이그레이션 진행 중: {file_path.name}")
        print(f"    - 대상 사유: {reason}")
        
        # 날짜 추출 (파일명 앞 YYYY-MM-DD 파싱)
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        date_match = re.match(r'^(\d{4}-\d{2}-\d{2})_', file_path.name)
        if date_match:
            date_prefix = date_match.group(1)
            
        # 기존 Frontmatter 파싱
        yaml_pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n(.*)$', re.DOTALL | re.MULTILINE)
        match = yaml_pattern.match(original_content)
        
        metadata = {}
        body_text = original_content
        if match:
            yaml_str, body_text = match.group(1), match.group(2)
            for line in yaml_str.split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    metadata[k.strip()] = v.strip().strip('"').strip("'")
                    
        url_val = metadata.get("url", "")
        source_val = metadata.get("source", "Unknown")
        category_val = metadata.get("category", "global")
        pub_date = metadata.get("published_at", date_prefix + " 00:00:00")
        original_title = metadata.get("title", file_path.stem)
        
        # AI Enrichment 호출을 위한 프롬프트 구성
        prompt = f"""다음 원시 뉴스 기사 정보를 분석하여 한글로 번역 및 심층 금융 요약/분석을 추가하고, 옵시디언 크로스링크와 태그들을 추출하여 정확한 JSON 형태로 응답해 주세요.

[기사 메타데이터]
- 원문 제목: {original_title}
- 언론사: {source_val}
- 카테고리: {category_val}
- 발행일: {pub_date}

[기사 원문 본문]
\"\"\"
{body_text}
\"\"\"
"""
        
        print("    [*] 로컬 AI 분석 호출 중...")
        ai_response = call_ollama_json(prompt, system_prompt)
        
        if not ai_response or "translated_title" not in ai_response:
            print("    [❌ 실패] AI 응답이 유효하지 않아 마이그레이션을 건너뜁니다.")
            continue
            
        translated_title = ai_response["translated_title"]
        enriched_body = post_process_links(ai_response["enriched_body"])
        tags_list = ai_response.get("extracted_tags", [category_val, "migration"])
        
        # tags 리스트에 카테고리 및 migration 태그 강제 병합 및 중복제거
        tags_set = set([t.lower().strip() for t in tags_list])
        tags_set.add(category_val.lower())
        tags_set.add("news")
        tags_set.add("koreanized")
        final_tags = list(tags_set)
        
        # 파일명 정제 및 신규 파일 경로 생성
        clean_title = clean_filename(translated_title)
        clean_source = clean_filename(source_val if source_val else "Unknown")
        if not clean_source:
            clean_source = "Unknown"
        new_filename = f"{date_prefix}_{clean_source}_{clean_title}.md"
        new_file_path = raw_dir / new_filename
        
        # 마크다운 템플릿 생성
        escaped_url = url_val.replace('\\', '\\\\').replace('"', '\\"')
        escaped_source = source_val.replace('\\', '\\\\').replace('"', '\\"')
        escaped_title = translated_title.replace('\\', '\\\\').replace('"', '\\"')
        
        # YAML tags 포맷
        tags_str = ", ".join(final_tags)
        
        new_content = f"""---
url: "{escaped_url}"
source: "{escaped_source}"
category: "{category_val}"
published_at: "{pub_date}"
title: "{escaped_title}"
language: "ko"
tags: [{tags_str}]
---

# {translated_title}

**작성 언론사**: {source_val}
**게시 일자**: {pub_date}
**원문 주소**: {url_val}
**기사 언어**: ko (한글 번역 및 AI 보정 완료)

---

## 기사 본문

{enriched_body}
"""
        
        # 파일 작성 및 기존 파일 처리
        try:
            # 1. 새 파일 작성
            with open(new_file_path, "w", encoding="utf-8") as f:
                f.write(new_content.strip() + "\n")
            print(f"    [새 파일 생성 완료] {new_filename}")
            
            # 2. 기존 파일과 다른 이름이라면 기존 파일 제거 및 wiki 링크 치환 수행
            if file_path.name != new_filename:
                if file_path.exists():
                    file_path.unlink()
                    print(f"    [구 파일 삭제 완료] {file_path.name}")
                
                # wiki/log.md 및 wiki/index.md 내의 구 파일 링크 치환
                update_references_in_wiki(file_path.name, new_filename)
                
            success_count += 1
        except Exception as e:
            print(f"    [❌ 에러] 파일 저장 중 오류 발생: {e}")
            
    print("\n" + "="*60)
    print(f"[★ 성공] 기존 raw 기사 마이그레이션 완료! 총 {success_count}개 파일 성공적으로 한글화 및 연결망 탑재.")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_migration()
