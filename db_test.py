import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# 환경 변수 로드
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def test_supabase_connection():
    print("===== Supabase 연동 검증 시작 =====")
    
    # 1. 환경 변수 유효성 검사
    if not SUPABASE_URL or "your_supabase" in SUPABASE_URL:
        print("[오류] SUPABASE_URL이 설정되지 않았거나 기본 템플릿 값입니다.")
        print("프로젝트 루트의 .env 파일에 실제 Supabase 프로젝트 URL을 기재해주세요.")
        return False
        
    if not SUPABASE_KEY or "your_supabase" in SUPABASE_KEY:
        print("[오류] SUPABASE_KEY가 설정되지 않았거나 기본 템플릿 값입니다.")
        print("프로젝트 루트의 .env 파일에 실제 Supabase API Key를 기재해주세요.")
        return False

    print(f"연결 시도 중... URL: {SUPABASE_URL}")
    
    try:
        # 2. 클라이언트 생성
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # 3. 테이블 존재 여부 및 간단한 데이터 조회 테스트 (news_articles 테이블)
        print("데이터베이스 테이블 조회 테스트 중...")
        
        # news_articles 테이블에서 1개의 데이터만 조회해봅니다.
        response = supabase.table("news_articles").select("*").limit(1).execute()
        
        print("데이터베이스 연결 성공!")
        print(f"조회 결과 데이터 수: {len(response.data)}")
        print("===== [검증 완료] Supabase 데이터베이스와 정상 연동되었습니다. =====")
        return True
        
    except Exception as e:
        print(f"[연동 실패] Supabase 연결 도중 에러가 발생했습니다: {e}")
        print("\n[가이드] Supabase 대시보드(SQL Editor)에서 아래 DDL 스크립트(schema.sql)를 실행하여 테이블을 먼저 생성하셨는지 확인해주세요.")
        return False

if __name__ == "__main__":
    success = test_supabase_connection()
    if not success:
        sys.exit(1)
