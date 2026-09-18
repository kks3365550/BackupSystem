import os
import sys
import time
import json
import webbrowser
import urllib.parse
import requests

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TOKEN_FILE = os.path.join(DATA_DIR, "kakao_token.json")

def setup_kakao():
    print("=" * 65)
    print("   [백업 매니저] 카카오톡 '나에게 보내기' 1-클릭 연동 마법사")
    print("=" * 65)
    print()
    print("카카오톡으로 매일 백업 완료 결과를 받아보시려면 1회성 토큰 발급이 필요합니다.\n")
    
    rest_api_key = input("1. 카카오 Developers의 [REST API 키]를 입력하세요: ").strip()
    if not rest_api_key:
        print("[ERROR] REST API 키가 입력되지 않았습니다.")
        return

    redirect_uri = "https://localhost"
    auth_url = (
        f"https://kauth.kakao.com/oauth/authorize?"
        f"client_id={rest_api_key}&redirect_uri={urllib.parse.quote(redirect_uri)}&response_type=code&scope=talk_message"
    )

    print("\n2. 카카오 로그인 및 메시지 전송 권한 승인 창을 브라우저에 엽니다...")
    print(f"   (수동 접속 주소: {auth_url})")
    webbrowser.open(auth_url)

    print("\n3. 로그인 및 동의 후 브라우저 주소창이 'https://localhost/?code=XXXXX...' 로 변경됩니다.")
    print("   주소창의 code= 뒤에 있는 인증코드(문자열)를 복사하여 아래에 붙여넣으세요.\n")
    
    auth_code_input = input("인증 코드(또는 주소창 전체)를 입력하세요: ").strip()
    if "code=" in auth_code_input:
        auth_code = auth_code_input.split("code=")[1].split("&")[0].strip()
    else:
        auth_code = auth_code_input.strip()

    if not auth_code:
        print("[ERROR] 인증 코드가 입력되지 않았습니다.")
        return

    print("\n4. 토큰 발급 중...")
    token_url = "https://kauth.kakao.com/oauth/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": rest_api_key,
        "redirect_uri": redirect_uri,
        "code": auth_code
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"}

    try:
        res = requests.post(token_url, data=payload, headers=headers, timeout=10)
        token_data = res.json()
        if "access_token" in token_data and "refresh_token" in token_data:
            os.makedirs(DATA_DIR, exist_ok=True)
            expires_in = token_data.get("expires_in", 21600)
            save_data = {
                "rest_api_key": rest_api_key,
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "expires_at": time.time() + expires_in
            }
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)

            print("\n🎉 [축하합니다!] 카카오톡 연동이 100% 완료되었습니다!")
            print("테스트 메시지를 전송합니다...")

            from core.notifier import send_kakao_message
            if send_kakao_message("💬 [백업 시스템] 카카오톡 알림 연동 테스트 성공!\n앞으로 백업이 완료될 때마다 이 채팅방으로 결과가 전송됩니다."):
                print("✅ 카카오톡 '나와의 채팅방'으로 테스트 메시지가 도착했습니다! 확인해 보세요.")
            else:
                print("⚠️ 메시지 전송에 실패했습니다. 동의항목(카카오톡 메시지 전송)을 확인해 주세요.")
        else:
            print(f"[ERROR] 토큰 발급 실패: {token_data}")
    except Exception as e:
        print(f"[ERROR] 오류 발생: {e}")

if __name__ == "__main__":
    setup_kakao()
