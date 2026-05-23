# main_pipeline.py (마스터 릴레이 파이프라인 엔트리)

import os
import sys
import subprocess
import time
from datetime import datetime

# agents 패키지 임포트
from agents.shared.config import OLLAMA_MODEL
from agents.chief_agent import ChiefAgent

def run_pipeline() -> bool:
    """
    [전체 파이프라인 통합 실행]
    신규 chief_agent를 통해 0선 DB선행 ➡️ 3대 리포터 수집 ➡️ Wiki 지식 합성을 
    동기식 순차 릴레이로 구동하고 최종 결과를 텔레그램으로 전송합니다.
    """
    start_time = time.time()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("\n" + "="*60)
    print(f"[*] AI 비서 마스터 릴레이 파이프라인 기동 시각: {now_str}")
    print(f"[*] 탑재 가용 모델: {OLLAMA_MODEL}")
    print("="*60 + "\n")
    
    # 1. ChiefAgent 릴레이 구동 (0~4선 전격 자동 순차 처리)
    print("[1/2] 👑 0선~4선 에이전트 릴레이 협업 프로세스 가동...")
    try:
        agent = ChiefAgent()
        briefing_content = agent.run_relay()
        print("[+] 0선~4선 에이전트 릴레이 협업 구동 완료.\n")
    except Exception as e:
        print(f"[❌ 치명적 에러] 에이전트 릴레이 중 붕괴 발생: {e}")
        return False
        
    # 2. 텔레그램 일일 요약 브리핑 푸시 송출
    print("[2/2] 📢 텔레그램 요약 브리핑 Push 전송 시작...")
    try:
        # telegram_bot.py --send-briefing 인자를 서브프로세스로 호출하여
        # 새로 생성된 master 위키 분석 결과물과 금융 카드를 종합 발송
        bot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telegram_bot.py")
        result = subprocess.run(
            [sys.executable, bot_path, "--send-briefing"], 
            capture_output=True, text=True, encoding='utf-8', check=True
        )
        print(result.stdout)
        print("[+] 텔레그램 브리핑 발송 프로세스 완료.\n")
    except Exception as e:
        print(f"[⚠️ 경고] 텔레그램 브리핑 발송 실패 (봇 토큰/Chat ID 설정 상태 확인 필요): {e}")
        
    elapsed = time.time() - start_time
    print("="*60)
    print(f"[★ 성공] 로컬 AI 비서 파이프라인 릴레이 전체 완료! (총 소요 시간: {elapsed:.2f}초)")
    print("="*60 + "\n")
    return True

if __name__ == "__main__":
    run_pipeline()
