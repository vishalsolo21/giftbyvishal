import os, json, base64, hashlib, time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding
import requests

API_BASE = "https://api.gyftr.com"
CAMPAIGN = "DIWALI2026"
CAMPAIGN_PATH = "diwali2026"
PLAY_PATH = f"/gyftrapi/api/v1/caimpaign/{CAMPAIGN_PATH}"
PASSPHRASE = os.getenv("GYFTR_PASSPHRASE", "d909dg78609e47ak47diy4cf87t90c4a")
COOKIE_NAME = "gyftr_session"
LOGIN_COOKIE = "gyftr_login"
COOKIE_MAX_AGE = 3600 * 8

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "origin": "https://www.gyftr.com",
    "referer": "https://www.gyftr.com/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36",
}
AUTH_HEADERS = {
    "device": "desktop", "platform": "web",
    "cache-control": "no-cache, no-store, must-revalidate",
    "pragma": "no-cache",
}

def fernet():
    key = os.getenv("GYFTR_SESSION_KEY", "")
    if not key:
        raise RuntimeError("GYFTR_SESSION_KEY environment variable is missing.")
    return Fernet(key.encode())

def json_response(handler, status, data, cookies=None):
    body = json.dumps(data).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    for cookie in cookies or []:
        handler.send_header("Set-Cookie", cookie)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)

def read_json(handler):
    try:
        length = int(handler.headers.get("Content-Length", "0"))
        if length > 16000:
            raise ValueError("Request too large")
        raw = handler.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))
    except Exception:
        raise ValueError("Invalid JSON request.")

def cookie_value(handler, name):
    raw = handler.headers.get("cookie", "")
    cookie = SimpleCookie()
    try:
        cookie.load(raw)
        morsel = cookie.get(name)
        return morsel.value if morsel else None
    except Exception:
        return None

def set_cookie(name, value, max_age=COOKIE_MAX_AGE):
    secure = "; Secure" if os.getenv("VERCEL") else ""
    return f"{name}={value}; Path=/; HttpOnly; SameSite=Lax; Max-Age={max_age}{secure}"

def clear_cookie(name):
    secure = "; Secure" if os.getenv("VERCEL") else ""
    return f"{name}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0{secure}"

def seal(data):
    return fernet().encrypt(json.dumps(data, separators=(",", ":")).encode()).decode()

def unseal(value):
    if not value:
        return None
    try:
        data = json.loads(fernet().decrypt(value.encode()).decode())
        if data.get("expires", 0) < time.time():
            return None
        return data
    except Exception:
        return None

def evp_bytes_to_key(password: bytes, salt: bytes, key_len=32, iv_len=16):
    out, prev = b"", b""
    while len(out) < key_len + iv_len:
        prev = hashlib.md5(prev + password + salt).digest()
        out += prev
    return out[:key_len], out[key_len:key_len + iv_len]

def encrypt_cryptojs(plaintext: bytes):
    salt = os.urandom(8)
    key, iv = evp_bytes_to_key(PASSPHRASE.encode(), salt)
    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    enc = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    ct = enc.update(padded) + enc.finalize()
    return base64.b64encode(b"Salted__" + salt + ct).decode()

def decrypt_cryptojs(blob):
    raw = base64.b64decode(blob)
    if raw[:8] != b"Salted__":
        raise ValueError("Unexpected encrypted profile format.")
    salt, ct = raw[8:16], raw[16:]
    key, iv = evp_bytes_to_key(PASSPHRASE.encode(), salt)
    dec = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    padded = dec.update(ct) + dec.finalize()
    unpadder = sym_padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()

def api_call(session, method, path, params=None, body=None, token=None, auth=False):
    headers = {}
    if auth:
        headers.update(AUTH_HEADERS)
        if token:
            headers["token"] = token
    response = session.request(method, API_BASE + path, params=params, data=body,
                               headers=headers, timeout=25)
    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError(f"Gyftr returned HTTP {response.status_code} with a non-JSON response.")
    if payload.get("code") not in (200, 201, 202) or payload.get("status") not in ("SUCCESS", None):
        raise RuntimeError(str(payload.get("message") or f"Gyftr HTTP {response.status_code}")[:300])
    return payload

def get_session(handler):
    data = unseal(cookie_value(handler, COOKIE_NAME))
    if not data or not data.get("token"):
        return None
    return data

def profile(token):
    sess = requests.Session()
    sess.headers.update(HEADERS)
    resp = api_call(sess, "GET", "/gyftrapi/api/v1/user/profile",
                    params={"_": str(int(time.time() * 1000))}, token=token, auth=True)
    decrypted = None
    if isinstance(resp.get("data"), str):
        try:
            decoded = decrypt_cryptojs(resp["data"]).decode()
            try:
                decrypted = json.loads(decoded)
            except json.JSONDecodeError:
                decrypted = decoded
        except Exception:
            pass
    return {"decrypted": decrypted, "rotated_token": resp.get("token")}
