import os
import time
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, Integer, String, JSON
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import OperationalError

# Import tvého opraveného modulu
try:
    from .hw_check import get_sys_info
except ImportError:
    from hw_check import get_sys_info

# --- KONFIGURACE ---
VERSION = "0.0.4"
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

def init_db():
    _engine = create_engine(DB_URL)
    for i in range(10):
        try:
            connection = _engine.connect()
            connection.close()
            Base.metadata.create_all(bind=_engine)
            print(f"--- KLUCON PRIME DB: CONNECTED (v{VERSION}) ---")
            return _engine
        except OperationalError:
            print(f"Čekám na databázi... (pokus {i+1}/10)")
            time.sleep(3)
    raise Exception("Kritická chyba: PostgreSQL není dostupný.")

engine = init_db()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI(title="KLUCON PRIME")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ROUTY ---

@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request, db: Session = Depends(get_db)):
    if db.query(User).first():
        return RedirectResponse(url="/")
    
    sys_data = get_sys_info(VERSION)
    return templates.TemplateResponse("setup.html", {"request": request, "sys": sys_data})

@app.post("/do-setup")
async def do_setup(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    try:
        # Zahashování
        hashed_pwd = pwd_context.hash(password)
        
        # Vytvoření admina
        new_user = User(username=username, hashed_password=hashed_pwd, role="admin")
        db.add(new_user)
        
        # Základní nastavení
        default_settings = SystemSetting(
            key="core", 
            value={"lang": "cs_CZ", "modules": {"movies": False, "series": False, "iptv": False}}
        )
        db.add(default_settings)
        
        db.commit()
        print(f"--- SETUP: Admin '{username}' vytvořen ---")
        
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        db.rollback()
        print(f"--- SETUP CHYBA: {e} ---")
        return HTMLResponse(content=f"Chyba při instalaci: {e}", status_code=500)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    # 1. KONTROLA: Pokud v DB není žádný uživatel, VŽDY jdi na /setup
    user = db.query(User).first()
    if not user:
        return RedirectResponse(url="/setup", status_code=303)
    
    # 2. Pokud uživatel existuje, načti nastavení
    settings = db.query(SystemSetting).filter(SystemSetting.key == "core").first()
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "user": user,
        "config": settings.value if settings else {},
        "t": {"welcome": f"Vítej, {user.username}", "ver": VERSION}
    })
