import json
import requests
from agents.shared.config import OLLAMA_API_URL, OLLAMA_MODEL

def check_ollama_connection() -> bool:
    """로컬 Ollama API 연결 및 gemma4:e4b 가용 여부 강제 헬스체크"""
    try:
        response = requests.get(f"{OLLAMA_API_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models_data = response.json()
            available_models = [m["name"] for m in models_data.get("models", [])]
            print(f"[*] 로컬 Ollama 사용 가능 모델 목록: {available_models}")
            
            # gemma4:e4b 모델 사용 보장
            if OLLAMA_MODEL in available_models or f"{OLLAMA_MODEL}:latest" in available_models:
                print(f"[+] 성공: AI 엔진 '{OLLAMA_MODEL}' 연결 및 구동 준비 완료.")
                return True
            else:
                # ollama는 tag가 생략되었을 때 gemma4:e4b 혹은 gemma4:latest 등의 칭호 확인을 대비해 한 번 더 체크
                for model in available_models:
                    if model.startswith("gemma4:e4b"):
                        print(f"[+] 성공: AI 엔진 '{model}' 발견 및 매핑 완료.")
                        return True
                
                print(f"[!] 에러: 필수 모델 '{OLLAMA_MODEL}'이 로컬 Ollama에 존재하지 않습니다.")
                return False
        return False
    except Exception as e:
        print(f"[!] Ollama 연결 에러: {OLLAMA_API_URL} 연결 실패. 올라마 가동 여부를 확인하세요. 세부: {e}")
        return False

def call_ollama(prompt: str, system_prompt: str = "") -> str:
    """Ollama API를 통해 텍스트 완성 요청 (비스트리밍 단일 응답)"""
    url = f"{OLLAMA_API_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "top_p": 0.9,
            "num_predict": 2048
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=90)
        if response.status_code == 200:
            return response.json().get("response", "").strip()
        else:
            print(f"[!] Ollama API 에러: HTTP {response.status_code} - {response.text}")
            return ""
    except Exception as e:
        print(f"[!] Ollama 호출 중 통신 장애 발생: {e}")
        return ""

def call_ollama_json(prompt: str, system_prompt: str = "") -> dict:
    """Ollama API를 통해 JSON 형식으로 Enrichment 결과 수신 및 파싱"""
    url = f"{OLLAMA_API_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
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
            res_text = response.json().get("response", "").strip()
            return json.loads(res_text)
    except Exception as e:
        print(f"[!] Ollama JSON 파싱 예외 발생: {e}")
    return {}
