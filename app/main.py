import os
import psutil
import platform
import time
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, Integer, String, JSON
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import OperationalError

# --- KONFIGURACE ---
VERSION = "0.0.3"
DB_URL = os.getenv("DB_URL", "postgresql://prime_user:prime_password@db/klucon_prime")

# --- DATABÁZE A MODELY ---
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="admin")

class SystemSetting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True)
    value = Column(JSON)

# Funkce pro bezpečné připojení k DB při startu
def init_db():
    _engine = create_engine(DB_URL)
    for i in range(10):
        try:
            # Test připojení
            connection = _engine.connect()
            connection.close()
            # Vytvoření tabulek pokud neexistují
            Base.metadata.create_all(bind=_engine)
            print(f"--- DATABASE CONNECTED (v{VERSION}) ---")
            return _engine
        except OperationalError:
            print(f"Databáze se připravuje... (pokus {i+1}/10)")
            time.sleep(3)
    raise Exception("Chyba: Nepodařilo se připojit k PostgreSQL.")

engine = init_db()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- APLIKACE A ZABEZPEČENÍ ---
app = FastAPI(title="KLUCON PRIME")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
templates = Jinja2Templates(directory="templates")
templates.env.add_extension('jinja2.ext.do')

# Dependency pro získání DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_sys_info():
    return {
        "os": f"{platform.system()} {platform.release()}",
        "cpu": f"{psutil.cpu_count(logical=False)} jader, {platform.processor()}",
        "ram": f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB",
        "ver": VERSION
    }

# --- ROUTY ---

@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request, db: Session = Depends(get_db)):
    # Pokud už admin existuje, nepouštět do setupu
    if db.query(User).first():
        return RedirectResponse(url="/")
    
    return templates.TemplateResponse("setup.html", {
        "request": request, 
        "sys": get_sys_info(),
        "t": {
            "setup_title": "PRIME Setup", 
            "btn_finish_setup": "DOKONČIT A SOUHLASIT"
        }
    })

@app.post("/do-setup")
async def do_setup(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    # Zahashování hesla
    hashed_pwd = pwd_context.hash(password)
    
    # Vytvoření admina
    new_user = User(username=username, hashed_password=hashed_pwd, role="admin")
    db.add(new_user)
    
    # Základní systémové nastavení
    default_settings = SystemSetting(
        key="core", 
        value={
            "lang": "cs_CZ", 
            "modules": {"movies": False, "series": False, "iptv": False}
        }
    )
    db.add(default_settings)
    
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    # Kontrola, zda proběhl setup
    user = db.query(User).first()
    if not user:
        return RedirectResponse(url="/setup")
    
    settings = db.query(SystemSetting).filter(SystemSetting.key == "core").first()
    
    # Dočasné texty pro Dashboard (dokud neuděláme lang soubory v DB)
    t = {
        "welcome": "Vítejte",
        "dashboard": "Nástěnka",
        "settings": "Nastavení",
        "users_man": "Uživatelé",
        "no_modules_title": "Žádné aktivní moduly",
        "no_modules_text": "Vypadá to, že zatím nemáte aktivovaný žádný modul.",
        "btn_install_mods": "Přejít do nastavení"
    }
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "config": {
            "admin": user, 
            "system": {"version": VERSION}, 
            "modules": settings.value["modules"]
        },
        "t": t
    })
