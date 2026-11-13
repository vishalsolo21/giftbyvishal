import os,json,base64,hashlib,hmac,time,random,re
from http.server import BaseHTTPRequestHandler
import requests
from cryptography.fernet import Fernet
BASE="https://golddropgolddhamaka.com"; CODE=os.environ.get("REFERRAL_CODE","KKD2LS01261026")
HEAD={"User-Agent":"Mozilla/5.0 Chrome/120.0 Safari/537.36","Accept":"*/*","Origin":BASE,"Referer":BASE+"/","Content-Type":"application/json"}
CHARS="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
def decode(r):
    try:d=r.json()
    except Exception:return {"raw_text":r.text or "Empty response"}
    if isinstance(d,dict) and "resp" in d:
        try:return json.loads(base64.b64decode(d["resp"]+"==").decode())
        except Exception:pass
    return d
def encode(p,key):
    t=str(int(time.time()*1000));packed={**p,"t":t};tb=base64.b64encode(t.encode()).decode();jb=base64.b64encode(json.dumps(packed,separators=(",",":")).encode()).decode()
    dig=hmac.new(key[4:18].encode(),(tb+"."+jb).encode(),hashlib.sha256).hexdigest();f=base64.b64encode(dig.encode()).decode();n=random.randint(1,6);ln=random.randint(2,8);noise="".join(random.choices(CHARS,k=ln))
    return f"{tb}.{jb}.{ln}{n}{f[:n]}{noise}{f[n:]}"
def reply(h,s,obj):
    b=json.dumps(obj).encode();h.send_response(s);h.send_header("Content-Type","application/json");h.send_header("Cache-Control","no-store");h.send_header("Content-Length",str(len(b)));h.end_headers();h.wfile.write(b)
def body(h):
    n=int(h.headers.get("Content-Length","0"))
    if n<1 or n>2000000:raise ValueError("Invalid request size.")
    return json.loads(h.rfile.read(n))
class handler(BaseHTTPRequestHandler):
 def do_GET(self):
  path=self.path.split("?",1)[0]
  if path not in ("/","/index.html"):
   self.send_error(404,"Not found");return
  try:
   with open("index.html","rb") as page: data=page.read()
   self.send_response(200)
   self.send_header("Content-Type","text/html; charset=utf-8")
   self.send_header("Content-Length",str(len(data)))
   self.send_header("Cache-Control","no-cache")
   self.end_headers()
   self.wfile.write(data)
  except Exception:
   self.send_error(500,"Homepage could not be loaded")
 def do_POST(self):
  path=self.path.split("?",1)[0].rstrip("/")
  if path=="/api/verify_otp":
   from api.verify_otp import handler as verify_handler
   return verify_handler.do_POST(self)
  if path!="/api/request_otp":
   reply(self,404,{"success":False,"message":"Unknown API endpoint."});return
  try:
   x=body(self);name=str(x.get("name","")).strip();mobile=str(x.get("mobile","")).strip();email=str(x.get("email","")).strip();pin=str(x.get("pincode","")).strip()
   if not name or len(name)>80:raise ValueError("Enter a valid full name.")
   if not re.fullmatch(r"[0-9]{10}",mobile):raise ValueError("Mobile number must contain 10 digits.")
   if not re.fullmatch(r"[^@\s]+@[^\s]+\.[^\s]+",email) or len(email)>120:raise ValueError("Enter a valid email address.")
   if not re.fullmatch(r"[0-9]{6}",pin):raise ValueError("Pincode must contain 6 digits.")
   image_url="https://img.sanishtech.com/u/2d10efe202ce0db247b36206f115604d.png"
   image_response=requests.get(image_url,headers={"User-Agent":"Mozilla/5.0","Accept":"image/avif,image/webp,image/apng,image/*,*/*;q=0.8"},timeout=25)
   image_response.raise_for_status()
   try:
    from io import BytesIO
    from PIL import Image
    source=Image.open(BytesIO(image_response.content))
    source.load()
    source.thumbnail((1200,1200))
    if source.mode in ("RGBA","LA") or "transparency" in source.info:
     rgba=source.convert("RGBA")
     canvas=Image.new("RGB",rgba.size,(255,255,255))
     canvas.paste(rgba,mask=rgba.getchannel("A"))
     source=canvas
    else:
     source=source.convert("RGB")
    output=BytesIO()
    quality=85
    source.save(output,format="JPEG",quality=quality,optimize=True)
    while output.tell()>950000 and quality>45:
     output=BytesIO()
     quality-=10
     source.save(output,format="JPEG",quality=quality,optimize=True)
    if output.tell()>1000000:raise ValueError("The default registration image is too large after compression.")
    photo=output.getvalue()
   except ValueError:
    raise
   except Exception as image_error:
    raise ValueError("The required default image could not be decoded: "+str(image_error)[:180])
   master=os.environ["MASTER_KEY"];ipkey=os.environ["IP_API_KEY"];fernet=Fernet(os.environ["STATE_FERNET_KEY"].encode())
   ip=requests.get("https://pro.ip-api.com/json",params={"key":ipkey},timeout=15);ip.raise_for_status()
   s=requests.Session();s.cookies.set("gold-drop-id",master,domain="golddropgolddhamaka.com")
   cr=s.post(BASE+"/api/users",json={"masterKey":master,"ipInfo":ip.json()},headers=HEAD,timeout=25);cr.raise_for_status();u=decode(cr);uk=str(u["userKey"]);dk=str(u["dataKey"])
   st=s.post(f"{BASE}/api/users/get-start/{uk}",headers=HEAD,data=b"",timeout=25);st.raise_for_status();start=decode(st)
   signed=encode({"name":name,"mobile":mobile,"email":email,"pincode":pin,"code":CODE,"terms_accepted":"1","userKey":uk},dk)
   hdr={k:v for k,v in HEAD.items() if k.lower()!="content-type"}
   reg=s.post(f"{BASE}/api/users/register/{uk}?t={int(time.time()*1000)}",files={"data":(None,signed),"img":("default-photo.jpg",photo,"image/jpeg")},headers=hdr,timeout=35);rd=decode(reg)
   if reg.status_code>=400 or rd.get("statusCode")!=200:reply(self,400,{"success":False,"message":rd.get("message") or rd.get("raw_text") or f"Registration failed ({reg.status_code})","response":rd});return
   token=fernet.encrypt(json.dumps({"userKey":uk,"dataKey":dk}).encode()).decode()
   reply(self,200,{"success":True,"sessionToken":token,"response":{"message":rd.get("message","OTP request submitted."),"statusCode":rd.get("statusCode"),"winner_count":start.get("winner_count")}})
  except ValueError as e:reply(self,400,{"success":False,"message":str(e)})
  except requests.RequestException as e:reply(self,502,{"success":False,"message":"Upstream request failed: "+str(e)})
  except Exception as e:reply(self,500,{"success":False,"message":str(e) or "Internal server error."})
 def log_message(self,*a):pass
