from http.server import BaseHTTPRequestHandler
from _common import *
import re, time

def handle_request(request):
    if request.command != "POST":
        return json_response(request, 405, {"error": "POST required"})
    try:
        data = read_json(request)
        mobile = str(data.get("mobile", "")).strip().replace(" ", "")
        if not re.fullmatch(r"\+[0-9]{10,15}", mobile):
            return json_response(request, 400, {"error": "Enter mobile with country code, e.g. +91XXXXXXXXXX"})
        session = requests.Session()
        session.headers.update(HEADERS)
        encrypted = encrypt_cryptojs(json.dumps({"mobile": mobile}, separators=(",", ":")).encode())
        resp = api_call(session, "POST", "/gyftrapi/api/v1/chrismas/checkMobile",
                        params={"campaign": CAMPAIGN},
                        body=json.dumps({"encryptedBody": encrypted}, separators=(",", ":")))
        login_state = {
            "mobile": mobile,
            "cookies": requests.utils.dict_from_cookiejar(session.cookies),
            "expires": time.time() + 300,
        }
        return json_response(request, 200, {"message": resp.get("message", "OTP requested.")},
                             [set_cookie(LOGIN_COOKIE, seal(login_state), 300)])
    except Exception as e:
        return json_response(request, 400, {"error": str(e)[:300]})


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        handle_request(self)
