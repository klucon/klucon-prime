import os
import psutil
import platform
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from sqlalchemy import create_all_models, create_engine, Column, Integer, String, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Nastavení
VERSION = "0.0.2"
DB_URL = os.getenv("DB_URL", "postgresql://prime_user:prime_password@db/klucon_prime")

# Databáze
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODELY ---
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

Base.metadata.create_all(bind=engine)

# --- APLIKACE ---
app = FastAPI(title="KLUCON PRIME")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
templates = Jinja2Templates(directory="templates")
templates.env.add_extension('jinja2.ext.do')

# Dependency pro DB
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def get_sys_info():
    return {
        "os": f"{platform.system()} {platform.release()}",
        "cpu": f"{psutil.cpu_count(logical=False)} jader {platform.processor()}",
        "ram": f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB",
        "ver": VERSION
    }

# --- ROUTY ---
@app.get("/setup", response_class=HTMLResponse)
async def setup(request: Request, db: Session = Depends(get_db)):
    if db.query(User).first(): return RedirectResponse(url="/")
    return templates.TemplateResponse("setup.html", {
        "request": request, 
        "sys": get_sys_info(),
        "t": {"setup_title": "PRIME Setup", "btn_finish_setup": "DOKONČIT A SOUHLASIT"}
    })

@app.post("/do-setup")
async def do_setup(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    hashed_pwd = pwd_context.hash(password)
    new_user = User(username=username, hashed_password=hashed_pwd, role="admin")
    db.add(new_user)
    # Základní nastavení
    default_settings = SystemSetting(key="core", value={"lang": "cs_CZ", "modules": {"movies": False}})
    db.add(default_settings)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user: return RedirectResponse(url="/setup")
    settings = db.query(SystemSetting).filter(SystemSetting.key == "core").first()
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "config": {"admin": user, "system": {"version": VERSION}, "modules": settings.value["modules"]},
        "t": {"welcome": "Vítejte", "dashboard": "Nástěnka", "no_modules_title": "Žádné moduly"}
    })
