import re
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Dict, Any

from agents.shared.config import (
    DEEPSEARCH_API_KEY, DEEPSEARCH_API_URL, NEWS_DIR, 
    OLLAMA_MODEL, TELEGRAM_BOT_TOKEN
)
from agents.shared.protocols import AgentResult
from agents.shared.ollama_client import check_ollama_connection, call_ollama_json
from agents.shared.file_utils import write_file_safely, get_existing_urls
from agents.shared.text_utils import clean_filename, post_process_links, parse_rss_date
from agents.shared.prompts import INGESTION_SYSTEM_PROMPT, INGESTION_USER_PROMPT_TEMPLATE

class BaseReporter:
    """3대 리포터의 공통 부모 에이전트 클래스. Template Method 패턴 적용."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.agent_name = config.get("agent_name", "BaseReporter")
        self.category = config.get("category", "global")
        self.deepsearch_endpoint = config.get("deepsearch_endpoint", "/v1/global-articles")
        self.deepsearch_keyword = config.get("deepsearch_keyword", "")
        self.rss_urls = config.get("rss_urls", [])
        self.special_prompts = config.get("special_prompts", "")
        
    def collect(self, financial_data: Dict[str, Any] = None) -> AgentResult:
        """
        [Template Method] 전체 뉴스 수집, Enrichment 및 raw 마크다운 저장 프로세스 제어.
        자식 클래스는 이를 오버라이드하지 않고 공통 알고리즘 템플릿을 활용합니다.
        """
        start_time = time.time()
        processed_files = []
        errors = []
        
        # 1. 헬스 체크
        is_ollama_available = check_ollama_connection()
        
        # 2. 기존 수집 완료 목록 로딩
        existing_urls = get_existing_urls()
        
        # 3. 원시 기사 수집 (DeepSearch API 시도 -> 실패/비활성 시 RSS Fallback)
        raw_articles = []
        try:
            raw_articles = self._fetch_raw_articles()
        except Exception as e:
            err_msg = f"[{self.agent_name}] 원시 뉴스 수집 에러: {e}"
            print(f"    [!] {err_msg}")
            errors.append(err_msg)
            
        print(f"[*] [{self.agent_name}] 최종 수집 대상 원시 기사 개수: {len(raw_articles)}개")
        
        # 4. 개별 기사 순차 처리
        for article in raw_articles:
            url = article.get("url", "")
            title = article.get("title", "")
            feed_name = article.get("feed_name", "Unknown")
            pub_date = article.get("published_at", "")
            fallback_text = article.get("fallback_text", "")
            is_english = article.get("is_english", False)
            
            if not url or not title:
                continue
                
            if url in existing_urls:
                print(f"    [-] 중복 수집 패스: {title}")
                continue
                
            print(f"    [+] 기사 본문 크롤링 시도: {title}")
            body_content = self._crawl_article_body(url, fallback_text)
            article["body_content"] = body_content
            
            # AI Enrichment 적용 여부 결정 (Hook Method 호출)
            translated_title = title
            enriched_body = body_content
            final_tags = [self.category, "news"]
            lang_val = "en" if is_english else "ko"
            
            if is_ollama_available and self._should_enrich(article):
                print(f"    [*] AI Ingestion Enrichment 가동 중 ({OLLAMA_MODEL})...")
                
                # 금융 데이터(당일 실측 수치)를 시스템/유저 프롬프트에 녹여넣을 컨텍스트 생성
                financial_context = ""
                if financial_data:
                    financial_context = f"\n[참고: 실시간 금융 주요 지표]\n" \
                                        f"- 비트코인: {financial_data.get('btc_krw', 0):,.0f}원 ({financial_data.get('btc_krw_change', 0):+.2f}%)\n" \
                                        f"- 김치프리미엄: {financial_data.get('kimchi_premium', 0):+.2f}%\n" \
                                        f"- 환율: {financial_data.get('exchange_rate', 0):,.2f}원\n" \
                                        f"- 기준금리: {financial_data.get('bok_rate', 0):.2f}%\n"
                
                user_prompt = INGESTION_USER_PROMPT_TEMPLATE.format(
                    title=title,
                    feed_name=feed_name,
                    category=self.category,
                    formatted_date=pub_date,
                    body_content=body_content
                )
                if financial_context:
                    user_prompt += financial_context
                    
                system_prompt = INGESTION_SYSTEM_PROMPT
                if self.special_prompts:
                    system_prompt += f"\n* 추가 지침:\n{self.special_prompts}"
                    
                try:
                    ai_res = call_ollama_json(user_prompt, system_prompt)
                    if ai_res and "translated_title" in ai_res:
                        translated_title = ai_res["translated_title"]
                        enriched_body = post_process_links(ai_res["enriched_body"])
                        tags_list = ai_res.get("extracted_tags", [self.category])
                        
                        tags_set = set([t.lower().strip() for t in tags_list])
                        tags_set.add(self.category.lower())
                        tags_set.add("news")
                        tags_set.add("enriched")
                        final_tags = list(tags_set)
                        lang_val = "ko"
                        print("      [+] AI Enrichment 적용 성공!")
                    else:
                        print("      [!] AI Ingestion 결과 스키마 무결성 실패. 기본 내용을 보존합니다.")
                except Exception as ex:
                    print(f"      [!] AI Enrichment 처리 실패: {ex}")
                    
            # 5. raw 마크다운 파일 안전 쓰기 ( enriched_body + details 접이식 원문 )
            clean_title = clean_filename(translated_title)
            clean_source = clean_filename(feed_name)
            if not clean_source:
                clean_source = "Unknown"
                
            date_only = pub_date.split(" ")[0]
            filename = f"{date_only}_{clean_source}_{clean_title}.md"
            file_path = NEWS_DIR / filename
            
            escaped_title = translated_title.replace('\\', '\\\\').replace('"', '\\"')
            escaped_feed_name = feed_name.replace('\\', '\\\\').replace('"', '\\"')
            escaped_link = url.replace('\\', '\\\\').replace('"', '\\"')
            tags_str = ", ".join(final_tags)
            
            # 사일런트 버그 완치: AI가 가공한 본문(enriched_body)을 최상단에, 원문(body_content)은 접이식 보관
            markdown_content = f"""---
url: "{escaped_link}"
source: "{escaped_feed_name}"
category: "{self.category}"
published_at: "{pub_date}"
title: "{escaped_title}"
language: "{lang_val}"
tags: [{tags_str}]
---

# {translated_title}

**작성 언론사**: {feed_name}
**게시 일자**: {pub_date}
**원문 주소**: {url}
**기사 언어**: {lang_val}

---

## 기사 본문 (AI 분석 요약)

{enriched_body}

---
<details><summary>📄 원문 보기</summary>

{body_content}
</details>
"""
            try:
                write_file_safely(file_path, markdown_content.strip() + "\n")
                processed_files.append(str(file_path))
                existing_urls.add(url)
                print(f"    [수집 성공] {filename}")
            except Exception as write_err:
                err_msg = f"기사 파일 쓰기 실패 ({title}): {write_err}"
                print(f"    [!] {err_msg}")
                errors.append(err_msg)
                
        elapsed = time.time() - start_time
        return AgentResult(
            agent_name=self.agent_name,
            success=len(errors) == 0,
            collected_count=len(processed_files),
            files_created=processed_files,
            errors=errors,
            elapsed_seconds=elapsed
        )

    def _should_enrich(self, article: Dict[str, Any]) -> bool:
        """
        [Hook Method] 특정 기사에 AI Enrichment(번역 및 분석 요약)를 적용할지 여부를 판별합니다.
        자식 클래스(예: BitcoinReporter 등)는 필요에 따라 오버라이드하여 커스텀 판정 규칙을 구현할 수 있습니다.
        """
        is_english = article.get("is_english", False)
        body_len = len(article.get("body_content", ""))
        return is_english or body_len < 250

    def _fetch_raw_articles(self) -> List[Dict[str, Any]]:
        """원시 뉴스 기사를 수집하는 이중 경로 (DeepSearch API 시도 -> 실패/비활성 시 RSS Fallback)"""
        articles = []
        is_deepsearch_active = False
        
        # 1차 시도: DeepSearch API가 활성화되어 있는 경우
        if DEEPSEARCH_API_KEY and DEEPSEARCH_API_KEY != "DEMO_API_KEY":
            print(f"\n[*] [{self.agent_name}] DeepSearch News API 연동 수집 시작...")
            try:
                today = datetime.now()
                three_days_ago = today - timedelta(days=3)
                date_from = three_days_ago.strftime("%Y-%m-%d")
                date_to = today.strftime("%Y-%m-%d")
                
                params = {
                    "keyword": self.deepsearch_keyword,
                    "date_from": date_from,
                    "date_to": date_to,
                    "page_size": 3,
                    "order": "published_at",
                    "api_key": DEEPSEARCH_API_KEY
                }
                
                url = f"{DEEPSEARCH_API_URL}{self.deepsearch_endpoint}"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                
                response = requests.get(url, headers=headers, params=params, timeout=12)
                if response.status_code == 200:
                    api_data = response.json().get("data", [])
                    if api_data:
                        is_deepsearch_active = True
                        print(f"  [→] DeepSearch 발견 기사: {len(api_data)}개")
                        for item in api_data:
                            title = item.get("title", "").strip()
                            link = item.get("url", item.get("link", "")).strip()
                            pub_date = item.get("published_at", item.get("created_at", item.get("date", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))))
                            description = item.get("content", item.get("briefing", item.get("summary", "")))
                            feed_name = item.get("publisher", item.get("source", "DeepSearch")).strip()
                            
                            if not title or not link:
                                continue
                                
                            soup_desc = BeautifulSoup(description, "html.parser")
                            fallback_text = soup_desc.get_text()
                            formatted_date = parse_rss_date(pub_date)
                            
                            # 제목의 아스키 코드 비율을 검토하여 영어 판별
                            is_english = (self.category in ["bitcoin", "global"]) or any(ord(char) < 128 for char in title[:10])
                            
                            articles.append({
                                "title": title,
                                "url": link,
                                "published_at": formatted_date,
                                "fallback_text": fallback_text,
                                "feed_name": feed_name,
                                "is_english": is_english
                            })
            except Exception as e:
                print(f"  [!] DeepSearch API 연동 실패 및 무력화 (에러: {e}). RSS 피드 Fallback 가동 준비...")
                
        # 2차 시도: DeepSearch 비활성 또는 실패 시 RSS Fallback 수집
        if not is_deepsearch_active:
            print(f"\n[*] [{self.agent_name}] RSS Fallback 피드 수집 시작...")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            for feed in self.rss_urls:
                feed_name = feed.get("name", "Unknown")
                feed_url = feed.get("url", "")
                print(f"  [→] RSS 소스: {feed_name} 스캔 중...")
                
                try:
                    response = requests.get(feed_url, headers=headers, timeout=10)
                    if response.status_code != 200:
                        continue
                        
                    root = ET.fromstring(response.content)
                    items = root.findall(".//item")
                    target_items = items[:2]  # 최신 뉴스 2건만 제한적 수집
                    
                    for item in target_items:
                        title = item.find("title").text if item.find("title") is not None else "제목 없음"
                        link = item.find("link").text if item.find("link") is not None else ""
                        pub_date = item.find("pubDate").text if item.find("pubDate") is not None else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        description = item.find("description").text if item.find("description") is not None else ""
                        
                        if not link:
                            continue
                            
                        soup_desc = BeautifulSoup(description, "html.parser")
                        fallback_text = soup_desc.get_text()
                        formatted_date = parse_rss_date(pub_date)
                        
                        english_sources = {"CoinDesk", "CoinTelegraph", "Decrypt", "Blockworks"}
                        is_english = (feed_name in english_sources) or (self.category == "bitcoin") or any(ord(char) < 128 for char in title[:10])
                        
                        articles.append({
                            "title": title,
                            "url": link,
                            "published_at": formatted_date,
                            "fallback_text": fallback_text,
                            "feed_name": feed_name,
                            "is_english": is_english
                        })
                except Exception as rss_err:
                    print(f"  [!] RSS 피드 파싱 실패 ({feed_name}): {rss_err}")
                    
        return articles

    def _crawl_article_body(self, url: str, fallback_text: str) -> str:
        """기사 본문 크롤링 헬퍼. 실패 시 요약을 Fallback 텍스트로 보존."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            response = requests.get(url, headers=headers, timeout=8)
            if response.status_code == 200:
                response.encoding = response.apparent_encoding
                soup = BeautifulSoup(response.text, "lxml")
                
                # 불필요한 태그 제거
                for tag in soup(["script", "style", "nav", "footer", "iframe", "header", "aside"]):
                    tag.decompose()
                    
                article_body = ""
                
                # Decrypt 등 특정 미디어의 코인 가격 리스크 피하기 위해, 구체적인 본문 클래스부터 우선 스캔
                body_div = soup.find("div", class_=re.compile(r'(post-content|article_body|article-body|news-body|view-content|story-content|article-content|news_content|news-text)', re.I))
                if body_div:
                    article_body = body_div.get_text("\n")
                else:
                    article_tag = soup.find("article")
                    if article_tag:
                        # article 내부의 코인 가격 위젯이나 사이드바가 있으면 제거하여 순수 본문 팩트 확보
                        for side_widget in article_tag.find_all(class_=re.compile(r'(coin-prices|price-data|sidebar|widget|promo)', re.I)):
                            side_widget.decompose()
                        article_body = article_tag.get_text("\n")
                    else:
                        p_tags = soup.find_all("p")
                        if len(p_tags) > 2:
                            article_body = "\n".join([p.get_text().strip() for p in p_tags if len(p.get_text().strip()) > 10])
                
                lines = [line.strip() for line in article_body.split("\n") if line.strip()]
                cleaned_body = "\n\n".join(lines)
                
                if len(cleaned_body) < 150:
                    return fallback_text
                    
                return cleaned_body
        except Exception:
            pass
        return fallback_text
