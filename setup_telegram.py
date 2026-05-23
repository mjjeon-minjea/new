import os
import requests
from dotenv import load_dotenv

# .env 로드
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ENV_PATH = ".env"

print("[*] 텔레그램 Chat ID 자동 감지 및 설정을 시작합니다...")
print(f"[*] 대상 봇 토큰: {BOT_TOKEN}")

if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token":
    print("[!] 에러: .env 파일에 올바른 텔레그램 봇 토큰이 설정되어 있지 않습니다.")
    exit(1)

def get_latest_chat_id():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get("result", [])
            
            if not results:
                print("\n[!] 감지된 대화 기록(Update)이 전혀 없습니다.")
                print("[!] 설정 안내:")
                print("    1. 스마트폰이나 PC 텔레그램 앱에서 t.me/JMJ_BTC_Analysis_AI_BOT 링크를 클릭합니다.")
                print("    2. 봇방에 진입한 후 [/start] 또는 [아무 메시지]나 1회 이상 전송해주세요.")
                print("    3. 메시지를 보내신 후, 이 스크립트를 다시 구동하시면 Chat ID가 자동으로 잡힙니다.\n")
                return None
                
            # 가장 최신 메시지를 보낸 사용자의 chat_id 추출
            for update in reversed(results):
                message = update.get("message")
                if message:
                    chat = message.get("chat")
                    if chat:
                        chat_id = chat.get("id")
                        user_first_name = chat.get("first_name", "사용자")
                        print(f"[+] 최근 메시지 감지 완료!")
                        print(f"    - 발신자명: {user_first_name}")
                        print(f"    - Chat ID: {chat_id}")
                        return chat_id
            
            print("[!] 메시지 구조가 올바르지 않습니다.")
            return None
        else:
            print(f"[!] 텔레그램 API 요청 실패: HTTP {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"[!] 통신 장애 발생: {e}")
        return None

def update_env_chat_id(chat_id):
    if not os.path.exists(ENV_PATH):
        print(f"[!] {ENV_PATH} 파일이 없습니다.")
        return
        
    try:
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            content = f.read()
            
        # TELEGRAM_CHAT_ID 부분 정규식 교체
        pattern = r"TELEGRAM_CHAT_ID=.*"
        replacement = f"TELEGRAM_CHAT_ID={chat_id}"
        
        if re_search := requests.get: # 정규식을 이용해 치환
            import re
            new_content = re.sub(pattern, replacement, content)
            
            with open(ENV_PATH, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"[+] .env 파일에 TELEGRAM_CHAT_ID={chat_id} 설정 업데이트가 완료되었습니다!")
    except Exception as e:
        print(f"[!] .env 파일 업데이트 실패: {e}")

if __name__ == "__main__":
    chat_id = get_latest_chat_id()
    if chat_id:
        update_env_chat_id(chat_id)
