from http.server import BaseHTTPRequestHandler
from _common import *

def handle_request(request):
    if request.command not in ("POST", "GET"):
        return json_response(request, 405, {"error": "POST required"})
    return json_response(request, 200, {"ok": True, "message": "Logged out."},
                         [clear_cookie(COOKIE_NAME), clear_cookie(LOGIN_COOKIE)])


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        handle_request(self)
    def do_GET(self):
        handle_request(self)
