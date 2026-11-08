from http.server import BaseHTTPRequestHandler
from common import *
import re

def handle_request(request):
    if request.command != "POST":
        return json_response(request, 405, {"error": "POST required"})
    account = get_session(request)
    if not account:
        return json_response(request, 401, {"error": "Please log in first."})
    try:
        data = read_json(request)
        try:
            points = int(data.get("points"))
        except Exception:
            return json_response(request, 400, {"error": "Points must be a whole number."})
        if not 1 <= points <= 150:
            return json_response(request, 400, {"error": "Points must be between 1 and 150."})
        # Confirm current campaign status before allowing a user-controlled action.
        current = profile(account["token"])
        rotated = current.get("rotated_token") or account["token"]
        pdata = current.get("decrypted")
        if isinstance(pdata, dict) and pdata.get("alreadyPlayed"):
            auth = {"mobile": account["mobile"], "token": rotated, "expires": account.get("expires", 0)}
            return json_response(request, 409, {"error": "This account has already played this campaign today."},
                                 [set_cookie(COOKIE_NAME, seal(auth))])
        user_type = str(pdata.get("user_type") or "B2C") if isinstance(pdata, dict) else "B2C"
        sess = requests.Session()
        sess.headers.update(HEADERS)
        payload = {"user_type": user_type, "points": points}
        encrypted = encrypt_cryptojs(json.dumps(payload, separators=(",", ":")).encode())
        result = api_call(sess, "POST", PLAY_PATH,
                          body=json.dumps({"encryptedBody": encrypted}, separators=(",", ":")),
                          token=rotated, auth=True)
        out = result.get("data") or {}
        auth = {"mobile": account["mobile"], "token": rotated, "expires": account.get("expires", 0)}
        return json_response(request, 200, {
            "message": result.get("message"),
            "points": points,
            "epay": out.get("epay"),
            "lucky": bool(out.get("luckuser")),
        }, [set_cookie(COOKIE_NAME, seal(auth))])
    except Exception as e:
        return json_response(request, 400, {"error": str(e)[:300]})


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        handle_request(self)
