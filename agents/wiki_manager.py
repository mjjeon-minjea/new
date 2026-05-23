import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from agents.shared.config import WIKI_DIR, RAW_DIR, OLLAMA_MODEL
from agents.shared.protocols import AgentResult
from agents.shared.ollama_client import check_ollama_connection, call_ollama
from agents.shared.file_utils import write_file_safely
from agents.shared.prompts import (
    WIKI_COMPOUND_SYSTEM_PROMPT_TEMPLATE, WIKI_COMPOUND_USER_PROMPT_TEMPLATE,
    TRANSLATION_INSTRUCTIONS
)

# 각 카테고리별 마스터 위키 파일 이름 매핑
CATEGORY_TO_WIKI = {
    "bitcoin": "Bitcoin",
    "global": "US-Fed",
    "korea": "Korea-Economy"
}

class WikiManager:
    """Wiki 관리자 에이전트: 4선 지식 융합, 누적 컴파운딩 및 index.md/log.md 갱신 담당"""
    
    def __init__(self):
        self.agent_name = "WikiManager"
        
    def run_compounding(self, financial_data: Dict[str, Any] = None) -> AgentResult:
        """
        [4선 실행 메서드] raw/ 폴더의 미처리 뉴스를 스캔하여
        기존 위키 파일에 Gemma4 AI로 점진적 지식 누적(Compounding)을 수행합니다.
        """
        start_time = time.time()
        processed_files = []
        errors = []
        
        print("\n" + "="*55)
        print(f"[*] [{self.agent_name}] 4선: 로컬 AI LLM Wiki 점진적 지식 합성 프로세스 시작...")
        print("="*55)
        
        # 1. 헬스 체크
        if not check_ollama_connection():
            err_msg = "로컬 Ollama API 연결 실패 또는 가용 모델 탐색 실패"
            print(f"    [!] {err_msg}")
            return AgentResult(agent_name=self.agent_name, success=False, errors=[err_msg])
            
        # 2. 미처리 기사 탐색
        processed_news = self._get_processed_files()
        print(f"[*] 기존 완료된 기사 수: {len(processed_news)}개")
        
        if not RAW_DIR.exists():
            err_msg = f"raw 기사 보관 디렉토리가 존재하지 않습니다 ({RAW_DIR})"
            print(f"    [!] {err_msg}")
            return AgentResult(agent_name=self.agent_name, success=False, errors=[err_msg])
            
        all_raw_files = sorted(list(RAW_DIR.glob("*.md")))
        unprocessed = [f for f in all_raw_files if f.name not in processed_news]
        
        print(f"[*] 수집된 전체 기사: {len(all_raw_files)}개 | 신규 미처리 기사: {len(unprocessed)}개")
        
        if not unprocessed:
            print("[*] 신규로 누적할 뉴스 기사가 없습니다. 위키 지식 합성을 종료합니다.")
            return AgentResult(agent_name=self.agent_name, success=True, collected_count=0)
            
        # 3. SCHEMA.md 품질 규칙 로드 (품질 제어 주입 완벽화)
        schema_file = WIKI_DIR / "SCHEMA.md"
        schema_context = ""
        if schema_file.exists():
            try:
                with open(schema_file, "r", encoding="utf-8") as sf:
                    schema_context = sf.read()
                print("[+] SCHEMA.md 품질 제어 지침서 로드 성공.")
            except Exception as e:
                print(f"[!] SCHEMA.md 로드 실패: {e}")
                
        # 4. 실시간 금융/크립토 수치 연계 정보 빌드
        financial_context = ""
        if financial_data:
            btc_krw = financial_data.get("btc_krw", 0)
            btc_krw_change = financial_data.get("btc_krw_change", 0)
            btc_usd = financial_data.get("btc_usd", 0)
            exchange_rate = financial_data.get("exchange_rate", 0)
            bok_rate = financial_data.get("bok_rate", 0)
            kimchi_premium = financial_data.get("kimchi_premium", 0)
            updated_at = financial_data.get("updated_at", "")
            
            financial_context = f"""[📊 실시간 금융 및 크립토 주요 지표 (당일 실측 수치)]
- 비트코인 원화 시세 (Upbit): {btc_krw:,.0f}원 ({btc_krw_change:+.2f}%)
- 비트코인 달러 시세 (Binance): ${btc_usd:,.2f}
- 김치 프리미엄 (Premium): {kimchi_premium:+.2f}%
- 원/달러 환율 (USD/KRW): {exchange_rate:,.2f}원
- 한국 기준금리 (BOK Rate): {bok_rate:.2f}%
- 지표 기준시: {updated_at}
"""

        # 5. 각 기사별 순차 누적 처리
        for file_path in unprocessed:
            print(f"\n[*] [지식 누적 시작] 대상 파일: {file_path.name}")
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_text = f.read()
            except Exception as e:
                err = f"원시 기사 파일 로드 오류 ({file_path.name}): {e}"
                print(f"    [!] {err}")
                errors.append(err)
                continue
                
            # 메타데이터 파싱
            category_match = re.search(r'category:\s*["\']?(.*?)["\']?\s*$', raw_text, re.MULTILINE)
            category = category_match.group(1).strip() if category_match else "global"
            wiki_name = CATEGORY_TO_WIKI.get(category, "Global-Market")
            
            lang_match = re.search(r'language:\s*["\']?(.*?)["\']?\s*$', raw_text, re.MULTILINE)
            language = lang_match.group(1).strip() if lang_match else "ko"
            
            title_match = re.search(r'title:\s*["\']?(.*?)["\']?\s*$', raw_text, re.MULTILINE)
            article_title = title_match.group(1).strip() if title_match else file_path.stem
            
            print(f"    - 분석 카테고리: {category} (원문언어: {language}) -> 마스터 위키: [[{wiki_name}]]")
            
            # 마스터 위키 현재 상태 로드
            metadata, existing_body = self._load_wiki_page(wiki_name)
            sources_count = int(metadata.get("sources_count", 0)) + 1
            
            # 번역 지침서 구성
            translation_instructions = ""
            lang_prompt_guideline = ""
            if language == "en":
                translation_instructions = TRANSLATION_INSTRUCTIONS
                lang_prompt_guideline = "[영어 번역 필수] 새로 수집된 기사가 영문으로 작성되었습니다. 위 시스템 프롬프트의 번역 지침서 룰을 100% 반영하여, 크립토/금융 전문 용어 매핑을 지키며 완벽하고 매끄러운 한글로 기존 한글 위키 본문과 유기적으로 합성(Compounding)해 주세요. 번역된 용어는 자연스럽게 본문에 녹여내야 하며 절대 영문 그대로 방치하지 마십시오."
                
        # R4 반영: wiki_manager 에이전트 물리 격리 폴더 참조 및 RAG 로드
        from agents.shared.config import ROOT_DIR
        agent_dir = ROOT_DIR / "_company" / "_agents" / "wiki_manager"
        
        # prompt.md 동적 로드 (갭 3 해결)
        prompt_path = agent_dir / "prompt.md"
        if prompt_path.exists():
            try:
                system_prompt_template = prompt_path.read_text(encoding="utf-8")
                print("[+] prompt.md 동적 프롬프트 로드 성공.")
            except Exception as e:
                print(f"[!] prompt.md 로드 실패, Fallback 적용: {e}")
                system_prompt_template = WIKI_COMPOUND_SYSTEM_PROMPT_TEMPLATE
        else:
            system_prompt_template = WIKI_COMPOUND_SYSTEM_PROMPT_TEMPLATE
            
        # load_rag_context 함수 호출
        from agents.shared.rag_utils import load_rag_context
        rag_context = load_rag_context(agent_dir)
        
        # R4 보완: 포맷 바인딩 예외 처리
        system_prompt = system_prompt_template
        if "{rag_context}" in system_prompt:
            system_prompt = system_prompt.replace("{rag_context}", rag_context)
        else:
            system_prompt = rag_context + "\n\n" + system_prompt
            
        if "{schema_context}" in system_prompt:
            system_prompt = system_prompt.replace("{schema_context}", schema_context if schema_context else "지식을 체계적으로 누적 합성하십시오.")
            
        if "{translation_instructions}" in system_prompt:
            system_prompt = system_prompt.replace("{translation_instructions}", translation_instructions)

        # 5. 각 기사별 순차 누적 처리
        for file_path in unprocessed:
            print(f"\n[*] [지식 누적 시작] 대상 파일: {file_path.name}")
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_text = f.read()
            except Exception as e:
                err = f"원시 기사 파일 로드 오류 ({file_path.name}): {e}"
                print(f"    [!] {err}")
                errors.append(err)
                continue
                
            # 메타데이터 파싱
            category_match = re.search(r'category:\s*["\']?(.*?)["\']?\s*$', raw_text, re.MULTILINE)
            category = category_match.group(1).strip() if category_match else "global"
            wiki_name = CATEGORY_TO_WIKI.get(category, "Global-Market")
            
            # WIKI_DIR는 기존 처리용 로그 파싱을 위해 놔두고, 초안 수동 승인으로 전환하므로 WIKI_DIR 경로 유지
            lang_match = re.search(r'language:\s*["\']?(.*?)["\']?\s*$', raw_text, re.MULTILINE)
            language = lang_match.group(1).strip() if lang_match else "ko"
            
            title_match = re.search(r'title:\s*["\']?(.*?)["\']?\s*$', raw_text, re.MULTILINE)
            article_title = title_match.group(1).strip() if title_match else file_path.stem
            
            print(f"    - 분석 카테고리: {category} (원문언어: {language}) -> 마스터 위키: [[{wiki_name}]]")
            
            # 마스터 위키 현재 상태 로드
            metadata, existing_body = self._load_wiki_page(wiki_name)
            sources_count = int(metadata.get("sources_count", 0)) + 1
            
            # 번역 지침서 구성
            translation_instructions = ""
            lang_prompt_guideline = ""
            if language == "en":
                translation_instructions = TRANSLATION_INSTRUCTIONS
                lang_prompt_guideline = "[영어 번역 필수] 새로 수집된 기사가 영문으로 작성되었습니다. 위 시스템 프롬프트의 번역 지침서 룰을 100% 반영하여, 크립토/금융 전문 용어 매핑을 지키며 완벽하고 매끄러운 한글로 기존 한글 위키 본문과 유기적으로 합성(Compounding)해 주세요. 번역된 용어는 자연스럽게 본문에 녹여내야 하며 절대 영문 그대로 방치하지 마십시오."
                
            user_prompt = WIKI_COMPOUND_USER_PROMPT_TEMPLATE.format(
                wiki_name=wiki_name,
                financial_context=financial_context,
                existing_body=existing_body if existing_body else "신규 문서입니다. 아직 축적된 내용이 없습니다.",
                raw_text=raw_text,
                lang_prompt_guideline=lang_prompt_guideline,
                date_str=datetime.now().strftime("%Y-%m-%d"),
                article_title=article_title
            )
            
            print(f"    [*] Ollama Gemma4 위키 합성 분석 수행 중... (시간이 다소 소요될 수 있습니다)")
            analyzed_response = call_ollama(user_prompt, system_prompt)
            
            if not analyzed_response or len(analyzed_response) < 100:
                err = f"Ollama 분석 결과물이 없거나 너무 짧아 갱신을 생략합니다 ({file_path.name})"
                print(f"    [!] {err}")
                errors.append(err)
                continue
                
            # 6. [R4 개편] 공식 위키에 즉시 쓰지 않고, 승인 대기 대기실에 격리 격재합니다. (갭 1 해결)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updated_wiki_content = f"""---
type: wiki
tags: [economy, {category}]
last_updated: "{now_str}"
sources_count: {sources_count}
---

{analyzed_response}
"""
            draft_file_path = ROOT_DIR / "_company" / "approvals" / "pending" / f"{wiki_name}_draft.md"
            draft_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                write_file_safely(draft_file_path, updated_wiki_content)
                print(f"    [대기] 임시 초안 [[approvals/pending/{wiki_name}_draft.md]] 격재 완료 (사용자 승인 대기)")
                
                # log.md 및 index.md 업데이트는 사용자 최종 컨펌 시 봇이 처리하도록 위임
                processed_files.append(str(draft_file_path))
            except Exception as e:
                err = f"임시 초안 파일 쓰기 오류 ({wiki_name}): {e}"
                print(f"    [!] {err}")
                errors.append(err)
                
        elapsed = time.time() - start_time
        return AgentResult(
            agent_name=self.agent_name,
            success=len(errors) == 0,
            collected_count=len(processed_files),
            files_created=processed_files,
            errors=errors,
            elapsed_seconds=elapsed
        )

    def _get_processed_files(self) -> set:
        """기존 완료된 뉴스 파일명 스캔"""
        processed = set()
        log_file = WIKI_DIR / "log.md"
        if not log_file.exists():
            return processed
            
        file_pattern = re.compile(r'\[\[raw/(.+?\.md)\]\]')
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    match = file_pattern.search(line)
                    if match:
                        processed.add(match.group(1).strip())
        except Exception as e:
            print(f"[!] log.md 파싱 오류: {e}")
        return processed

    def _load_wiki_page(self, wiki_name: str) -> tuple:
        """기존 위키 파일의 YAML Frontmatter와 Content를 읽어서 반환"""
        file_path = WIKI_DIR / f"{wiki_name}.md"
        if not file_path.exists():
            return {}, ""
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
                
            yaml_pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n(.*)$', re.DOTALL | re.MULTILINE)
            match = yaml_pattern.match(text)
            if match:
                yaml_str, body = match.group(1), match.group(2)
                metadata = {}
                for line in yaml_str.split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        metadata[k.strip()] = v.strip().strip('"').strip("'")
                return metadata, body
            return {}, text
        except Exception as e:
            print(f"[!] 위키 {wiki_name} 로딩 중 오류: {e}")
            return {}, ""

    def _update_index_and_log(self, raw_filename: str, article_title: str, wiki_name: str):
        """log.md와 index.md에 작업 로그와 색인을 갱신"""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_only = now_str.split(" ")[0]
        
        # 1. log.md에 append-only로 기입
        log_file = WIKI_DIR / "log.md"
        log_entry = f"## [{now_str}] ingest | [[raw/{raw_filename}]] 수집 및 [[{wiki_name}]] 위키 페이지 갱신\n"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
            print(f"    [+] log.md 작업 로그 기록 완료: [[raw/{raw_filename}]] -> [[{wiki_name}]]")
        except Exception as e:
            print(f"    [!] log.md 기록 실패: {e}")
            
        # 2. index.md에 색인 갱신 기입
        index_file = WIKI_DIR / "index.md"
        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    index_content = f.read()
                
                pattern = re.compile(rf'(-\s*\[\[{re.escape(wiki_name)}\]\]\s*-\s*[^(\n]*)(\s*\(최근 갱신:.*?\))?', re.MULTILINE)
                if pattern.search(index_content):
                    updated_content = pattern.sub(rf'\1 (최근 갱신: {date_only})', index_content)
                    with open(index_file, "w", encoding="utf-8") as f:
                        f.write(updated_content)
                    print(f"    [+] index.md 색인 맵 최근 갱신일({date_only}) 업데이트 완료.")
            except Exception as e:
                print(f"    [!] index.md 업데이트 실패: {e}")
