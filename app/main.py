import os
import time
import bcrypt
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, JSON
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import OperationalError

# Import HW detekce
try:
    from .hw_check import get_sys_info
except:
    from hw_check import get_sys_info

# --- KONFIGURACE ---
VERSION = "0.0.6"
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

# --- FUNKCE PRO ZABEZPEČENÍ (Přímý Bcrypt) ---
def hash_password(password: str) -> str:
    # Ošetření délky na 72 bajtů pro bcrypt a sůl
    pwd_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

# --- INICIALIZACE DB ---
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI(title="KLUCON PRIME")
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup_event():
    # Počkáme na databázi a vytvoříme tabulky
    for _ in range(10):
        try:
            Base.metadata.create_all(bind=engine)
            print(f"--- KLUCON PRIME DB: PŘIPOJENO (v{VERSION}) ---")
            break
        except Exception:
            print("Čekám na PostgreSQL...")
            time.sleep(2)

# --- ROUTY ---

@app.get("/")
async def root(db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        return RedirectResponse(url="/setup", status_code=303)
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request, db: Session = Depends(get_db)):
    if db.query(User).first():
        return RedirectResponse(url="/dashboard")
    
    sys_data = get_sys_info(VERSION)
    return templates.TemplateResponse("setup.html", {"request": request, "sys": sys_data})

@app.post("/do-setup")
async def do_setup(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    try:
        # 1. Kontrola, zda admin už neexistuje
        if db.query(User).first():
            return RedirectResponse(url="/dashboard", status_code=303)
            
        # 2. Hashování hesla napřímo přes bcrypt
        hashed_pwd = hash_password(password)
        
        # 3. Uložení admina
        new_user = User(username=username, hashed_password=hashed_pwd, role="admin")
        db.add(new_user)
        
        # 4. Základní nastavení systému
        new_settings = SystemSetting(
            key="core", 
            value={"lang": "cs", "modules": {"movies": False, "iptv": False}}
        )
        db.add(new_settings)
        
        db.commit()
        print(f"--- SETUP: Uživatel {username} úspěšně vytvořen ---")
        return RedirectResponse(url="/dashboard", status_code=303)
        
    except Exception as e:
        db.rollback()
        print(f"--- CHYBA SETUPU: {str(e)} ---")
        return HTMLResponse(content=f"Kritická chyba: {str(e)}", status_code=500)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        return RedirectResponse(url="/setup")
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "user": user,
        "t": {"welcome": f"Vítej, {user.username}", "ver": VERSION}
    })
