from http.server import BaseHTTPRequestHandler
from _common import *

def handle_request(request):
    if request.command != "GET":
        return json_response(request, 405, {"error": "GET required"})
    account = get_session(request)
    if not account:
        return json_response(request, 401, {"error": "Please log in first."})
    try:
        result = profile(account["token"])
        token = result.get("rotated_token") or account["token"]
        data = result.get("decrypted")
        if not isinstance(data, dict):
            return json_response(request, 200, {"mobile": account["mobile"], "details": "Profile data could not be decoded."})
        auth = {"mobile": account["mobile"], "token": token, "expires": account.get("expires", 0)}
        return json_response(request, 200, {
            "mobile": account["mobile"],
            "user_type": data.get("user_type", "B2C"),
            "epay_balance": data.get("epay_balance"),
            "already_played": bool(data.get("alreadyPlayed")),
        }, [set_cookie(COOKIE_NAME, seal(auth))])
    except Exception as e:
        return json_response(request, 400, {"error": str(e)[:300]})


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        handle_request(self)
