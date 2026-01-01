import os
import json
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext

app = FastAPI(title="KLUCON PRIME")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Cesty relativní k běžící aplikaci
CONFIG_FILE = "config/settings.json"
LANG_DIR = "lang"

templates = Jinja2Templates(directory="templates")
templates.env.add_extension('jinja2.ext.do')

def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def load_lang(lang_code="cs_CZ"):
    # Načte core + dynamicky komponenty
    base_path = f"{LANG_DIR}/{lang_code}"
    t = {}
    if os.path.exists(f"{base_path}/core.json"):
        with open(f"{base_path}/core.json", "r", encoding="utf-8") as f:
            t.update(json.load(f))
    
    comp_path = f"{base_path}/components"
    if os.path.exists(comp_path):
        t["components"] = {}
        for file in os.listdir(comp_path):
            if file.endswith(".json"):
                name = file.replace(".json", "")
                with open(f"{comp_path}/{file}", "r", encoding="utf-8") as f:
                    t["components"][name] = json.load(f)
    return t

@app.middleware("http")
async def check_setup(request: Request, call_next):
    config = get_config()
    if not config and request.url.path not in ["/setup", "/do-setup"] and not request.url.path.startswith("/static"):
        return RedirectResponse(url="/setup")
    return await call_next(request)

@app.get("/setup", response_class=HTMLResponse)
async def setup(request: Request):
    t = load_lang("cs_CZ")
    return templates.TemplateResponse("setup.html", {"request": request, "t": t})

@app.post("/do-setup")
async def do_setup(username: str = Form(...), password: str = Form(...)):
    hashed_pwd = pwd_context.hash(password)
    config = {
        "system": {"app_name": "KLUCON PRIME", "version": "0.0.1", "lang": "cs_CZ"},
        "admin": {"username": username, "password": hashed_pwd},
        "modules": {"movies": False, "series": False}
    }
    os.makedirs("config", exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    return RedirectResponse(url="/", status_code=303)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    config = get_config()
    t = load_lang(config["system"]["lang"])
    return templates.TemplateResponse("index.html", {"request": request, "t": t, "config": config})
