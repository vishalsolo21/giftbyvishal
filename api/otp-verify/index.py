from http.server import BaseHTTPRequestHandler
from common import *
import time, re

def handle_request(request):
    if request.command != "POST":
        return json_response(request, 405, {"error": "POST required"})
    try:
        state = unseal(cookie_value(request, LOGIN_COOKIE))
        if not state or not state.get("mobile"):
            return json_response(request, 401, {"error": "OTP flow expired. Request a new OTP."})
        data = read_json(request)
        otp = str(data.get("otp", "")).strip()
        if not re.fullmatch(r"[0-9]{4,8}", otp):
            return json_response(request, 400, {"error": "Enter the numeric OTP."})
        session = requests.Session()
        session.headers.update(HEADERS)
        session.cookies.update(state.get("cookies", {}))
        mobile = state["mobile"]
        encrypted = encrypt_cryptojs(json.dumps({"mobile": mobile, "otp": otp}, separators=(",", ":")).encode())
        resp = api_call(session, "POST", "/gyftrapi/api/v1/chrismas/validateOtp",
                        params={"campaign": CAMPAIGN},
                        body=json.dumps({"encryptedBody": encrypted}, separators=(",", ":")))
        token = resp.get("token")
        if not token:
            raise RuntimeError("Gyftr did not return a session token.")
        try:
            p = api_call(session, "GET", "/gyftrapi/api/v1/user/profile",
                         params={"_": str(int(time.time() * 1000))}, token=token, auth=True)
            token = p.get("token") or token
        except Exception:
            pass
        auth = {"mobile": mobile, "token": token, "expires": time.time() + COOKIE_MAX_AGE}
        return json_response(request, 200, {"ok": True, "mobile": mobile},
                             [set_cookie(COOKIE_NAME, seal(auth)), clear_cookie(LOGIN_COOKIE)])
    except Exception as e:
        return json_response(request, 400, {"error": str(e)[:300]})


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        handle_request(self)
