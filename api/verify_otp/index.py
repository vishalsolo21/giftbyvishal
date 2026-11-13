import os,json,base64,hashlib,hmac,time,random
from http.server import BaseHTTPRequestHandler
import requests
from cryptography.fernet import Fernet,InvalidToken
BASE="https://golddropgolddhamaka.com";HEAD={"User-Agent":"Mozilla/5.0 Chrome/120.0 Safari/537.36","Accept":"*/*","Origin":BASE,"Referer":BASE+"/","Content-Type":"application/json"};CHARS="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
def decode(r):
 try:d=r.json()
 except Exception:return {"raw_text":r.text or "Empty response"}
 if isinstance(d,dict) and "resp" in d:
  try:return json.loads(base64.b64decode(d["resp"]+"==").decode())
  except Exception:pass
 return d
def encode(p,key):
 t=str(int(time.time()*1000));tb=base64.b64encode(t.encode()).decode();jb=base64.b64encode(json.dumps({**p,"t":t},separators=(",",":")).encode()).decode()
 dig=hmac.new(key[4:18].encode(),(tb+"."+jb).encode(),hashlib.sha256).hexdigest();f=base64.b64encode(dig.encode()).decode();n=random.randint(1,6);ln=random.randint(2,8);noise="".join(random.choices(CHARS,k=ln))
 return f"{tb}.{jb}.{ln}{n}{f[:n]}{noise}{f[n:]}"
def reply(h,s,obj):
 b=json.dumps(obj).encode();h.send_response(s);h.send_header("Content-Type","application/json");h.send_header("Cache-Control","no-store");h.send_header("Content-Length",str(len(b)));h.end_headers();h.wfile.write(b)
class handler(BaseHTTPRequestHandler):
 def do_POST(self):
  try:
   n=int(self.headers.get("Content-Length","0"))
   if n<1 or n>100000:raise ValueError("Invalid request size.")
   x=json.loads(self.rfile.read(n));otp=str(x.get("otp","")).strip()
   if not otp.isdigit() or len(otp)!=6:raise ValueError("Enter a valid 6-digit OTP.")
   master=os.environ["MASTER_KEY"];f=Fernet(os.environ["STATE_FERNET_KEY"].encode())
   try:state=json.loads(f.decrypt(str(x.get("sessionToken","")).encode()).decode())
   except (InvalidToken,ValueError):raise ValueError("OTP session is invalid. Request a new OTP.")
   uk,dk=state["userKey"],state["dataKey"];signed=encode({"otp":otp,"userKey":uk},dk)
   s=requests.Session();s.cookies.set("gold-drop-id",master,domain="golddropgolddhamaka.com")
   r=s.post(f"{BASE}/api/users/verify-otp/{uk}?t={int(time.time()*1000)}",json={"data":signed},headers=HEAD,timeout=30);result=decode(r);ok=result.get("statusCode")==200
   safe={k:v for k,v in result.items() if k.lower() not in ("accesstoken","token","secret","datakey")}
   if r.status_code>=400:reply(self,400,{"success":False,"response":safe});return
   reply(self,200,{"success":ok,"response":safe})
  except ValueError as e:reply(self,400,{"success":False,"message":str(e)})
  except requests.RequestException as e:reply(self,502,{"success":False,"message":"Upstream request failed: "+str(e)})
  except Exception as e:reply(self,500,{"success":False,"message":str(e) or "Internal server error."})
 def log_message(self,*a):pass
