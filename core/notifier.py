import os
import json
import time
import requests
from typing import Dict, Any, Optional

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
KAKAO_TOKEN_FILE = os.path.join(DATA_DIR, "kakao_token.json")

def get_kakao_token_data() -> Dict[str, Any]:
    if not os.path.exists(KAKAO_TOKEN_FILE):
        return {}
    try:
        with open(KAKAO_TOKEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_kakao_token_data(token_data: Dict[str, Any]):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(KAKAO_TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=2, ensure_ascii=False)

def refresh_kakao_access_token(rest_api_key: str, refresh_token: str, client_secret: Optional[str] = None) -> Optional[str]:
    """
    Refreshes the Kakao access token using the refresh token.
    """
    url = "https://kauth.kakao.com/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "client_id": rest_api_key,
        "refresh_token": refresh_token
    }
    if client_secret:
        payload["client_secret"] = client_secret
    headers = {"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"}

    try:
        res = requests.post(url, data=payload, headers=headers, timeout=10)
        data = res.json()
        if "access_token" in data:
            token_info = get_kakao_token_data()
            token_info["access_token"] = data["access_token"]
            token_info["expires_at"] = time.time() + data.get("expires_in", 21600)
            if "refresh_token" in data:
                token_info["refresh_token"] = data["refresh_token"]
            save_kakao_token_data(token_info)
            return data["access_token"]
        else:
            print(f"[KakaoNotifier] Token refresh failed: {data}")
            return None
    except Exception as e:
        print(f"[KakaoNotifier] Error refreshing token: {e}")
        return None

def send_kakao_message(text: str) -> bool:
    """
    Sends a message to the user's own KakaoTalk chat (나에게 보내기).
    """
    token_info = get_kakao_token_data()
    if not token_info:
        print("[KakaoNotifier] token_info is empty")
        return False

    access_token = token_info.get("access_token")
    rest_api_key = token_info.get("rest_api_key")
    client_secret = token_info.get("client_secret")
    refresh_token = token_info.get("refresh_token")
    expires_at = token_info.get("expires_at", 0)

    # Refresh access token if expired and refresh_token is available
    if (not access_token or time.time() >= (expires_at - 300)) and refresh_token and rest_api_key:
        access_token = refresh_kakao_access_token(rest_api_key, refresh_token, client_secret) or access_token

    if not access_token:
        print("[KakaoNotifier] No access token available")
        return False

    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
    }
    
    # Fix #10: Use configurable dashboard URL (env var > Tailscale IP > localhost fallback)
    dashboard_url = (
        os.environ.get("BACKUP_DASHBOARD_URL")
        or "http://100.99.168.69:8765"
    )

    template_object = {
        "object_type": "text",
        "text": text,
        "link": {
            "web_url": dashboard_url,
            "mobile_web_url": dashboard_url
        },
        "button_title": "백업 대시보드"
    }

    try:
        payload_data = {"template_object": json.dumps(template_object, ensure_ascii=False)}
        res = requests.post(url, headers=headers, data=payload_data, timeout=10)
        if res.status_code == 200 and res.json().get("result_code") == 0:
            print("[KakaoNotifier] KakaoTalk message sent successfully!")
            return True
        elif res.status_code == 401 and refresh_token and rest_api_key:
            # Token invalid, try refreshing once
            access_token = refresh_kakao_access_token(rest_api_key, refresh_token)
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
                res = requests.post(url, headers=headers, data=payload_data, timeout=10)
                return res.status_code == 200
        print(f"[KakaoNotifier] Send failed: {res.status_code}")
        return False
    except Exception as e:
        print(f"[KakaoNotifier] Error sending message: {type(e).__name__} {e}")
        return False

def notify_backup_result(manifest: Optional[Dict[str, Any]] = None, error_msg: Optional[str] = None, profile_name: str = "자동 백업"):
    """
    Formats and broadcasts backup summary notification to KakaoTalk.
    """
    if error_msg:
        text = (
            f"⚠️ [백업 시스템] 백업 오류 알림\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"• 대상 프로필: {profile_name}\n"
            f"• 상태: 백업 실패 ❌\n"
            f"• 오류 내용: {error_msg}\n"
            f"• 발생 시각: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
    elif manifest:
        summary = manifest.get("summary", {})
        total_files = summary.get("total_files", 0)
        new_mod_files = summary.get("new_files", 0) + summary.get("modified_files", 0)
        dedup_mb = round(summary.get("dedup_saved_bytes", 0) / (1024 * 1024), 1)
        duration = summary.get("duration_seconds", 0)
        snap_id = manifest.get("id", "-")

        text = (
            f"🛡️ [백업 시스템] 정기 백업 완료!\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"• 대상 프로필: {profile_name}\n"
            f"• 상태: 백업 성공 (정상) ✅\n"
            f"• 스냅샷 ID: {snap_id}\n"
            f"• 총 파일: {total_files:,}개 (신규/수정 {new_mod_files:,}개)\n"
            f"• 중복제거 절감: {dedup_mb:,} MB\n"
            f"• 소요 시간: {duration}초\n"
            f"• 완료 시각: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        return

    # Trigger Kakao notification
    send_kakao_message(text)
