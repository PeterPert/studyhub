from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String, Date, Time, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pydantic import BaseModel
from typing import List, Optional
import datetime
import os

from dotenv import load_dotenv
load_dotenv()

# --- 1. НАСТРОЙКА БАЗЫ ДАННЫХ (PostgreSQL) ---
# Создай .env с: DATABASE_URL=postgresql://пользователь:пароль@localhost:5432/schedule_db
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError(
        "Задай DATABASE_URL в .env. Пример:\n"
        "  DATABASE_URL=postgresql://postgres:stef4587@localhost:5432/schedule_db\n"
        "На macOS (Homebrew) часто работает: postgresql://localhost:5432/schedule_db"
    )
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 2. МОДЕЛИ БАЗЫ ДАННЫХ (SQLAlchemy) ---

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String) # 'student', 'teacher', 'admin'
    name = Column(String)
    login = Column(String, unique=True, index=True)
    password = Column(String) # В реальном проекте хранить ТОЛЬКО хэши!

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    name_group = Column(String)

class StudentGroup(Base):
    __tablename__ = "student_groups"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    group_id = Column(Integer, ForeignKey("groups.id"))

class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date)
    time = Column(Time)
    subject = Column(String)
    group_id = Column(Integer, ForeignKey("groups.id"))
    prepod_id = Column(Integer, ForeignKey("users.id"))
    classroom = Column(String)

# Создаем таблицы (если их нет)
Base.metadata.create_all(bind=engine)

# --- 3. PYDANTIC СХЕМЫ (Для валидации входящих/исходящих данных) ---

class LoginRequest(BaseModel):
    login: str
    password: str

class LoginResponse(BaseModel):
    id: int
    role: str
    name: str

class ScheduleResponse(BaseModel):
    id: int
    date: datetime.date
    time: datetime.time
    subject: str
    classroom: str
    group_id: Optional[int] = None
    prepod_id: Optional[int] = None

    class Config:
        from_attributes = True

class ScheduleCreate(BaseModel):
    date: datetime.date
    time: datetime.time
    subject: str
    group_id: int
    prepod_id: int
    classroom: str

class ScheduleUpdate(BaseModel):
    date: Optional[datetime.date] = None
    time: Optional[datetime.time] = None
    subject: Optional[str] = None
    group_id: Optional[int] = None
    prepod_id: Optional[int] = None
    classroom: Optional[str] = None

# --- 4. FASTAPI ПРИЛОЖЕНИЕ И РУЧКИ ---

app = FastAPI(title="Schedule API")

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Зависимость для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Проверка прав админа (передавать заголовок X-Admin-Id с id пользователя)
def get_admin(admin_id: Optional[int] = Header(None, alias="X-Admin-Id"), db: Session = Depends(get_db)):
    if admin_id is None:
        raise HTTPException(status_code=401, detail="Требуется заголовок X-Admin-Id")
    user = db.query(User).filter(User.id == admin_id, User.role == "admin").first()
    if not user:
        raise HTTPException(status_code=403, detail="Доступ запрещён. Требуются права администратора.")
    return user

@app.get("/")
def root():
    return RedirectResponse(url="/docs")

@app.post("/api/login", response_model=LoginResponse)
def login(user_data: LoginRequest, db: Session = Depends(get_db)):
    """Ручка для авторизации"""
    # Ищем пользователя. ВАЖНО: в проде пароли нужно сравнивать через хэши (например, bcrypt)
    user = db.query(User).filter(User.login == user_data.login, User.password == user_data.password).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")
    
    # Возвращаем id и роль, чтобы фронтенд знал, куда направить пользователя
    return {"id": user.id, "role": user.role, "name": user.name}

@app.get("/api/schedule/teacher/{teacher_id}", response_model=List[ScheduleResponse])
def get_teacher_schedule(
    teacher_id: int,
    day_of_week: int,  # 0=Пн, 1=Вт, ..., 6=Вс
    db: Session = Depends(get_db),
):
    """Расписание преподавателя на день недели"""
    if not 0 <= day_of_week <= 6:
        raise HTTPException(status_code=400, detail="day_of_week: 0–6 (0=Пн, 6=Вс)")
    schedules = (
        db.query(Schedule)
        .filter(Schedule.prepod_id == teacher_id)
        .all()
    )
    result = [s for s in schedules if s.date.weekday() == day_of_week]
    return sorted(result, key=lambda s: s.time)

@app.get("/api/schedule/student/{student_id}", response_model=List[ScheduleResponse])
def get_student_schedule(
    student_id: int,
    day_of_week: int,  # 0=Пн, 1=Вт, ..., 6=Вс
    db: Session = Depends(get_db),
):
    """Расписание студента на день недели (группа берётся из БД)"""
    if not 0 <= day_of_week <= 6:
        raise HTTPException(status_code=400, detail="day_of_week: 0–6 (0=Пн, 6=Вс)")
    link = db.query(StudentGroup).filter(StudentGroup.student_id == student_id).first()
    if not link:
        raise HTTPException(
            status_code=404,
            detail="Студент не привязан ни к одной группе",
        )
    schedules = (
        db.query(Schedule)
        .filter(Schedule.group_id == link.group_id)
        .all()
    )
    result = [s for s in schedules if s.date.weekday() == day_of_week]
    return sorted(result, key=lambda s: s.time)


# --- АДМИНКА: добавление и изменение расписания ---

@app.post("/api/admin/schedule", response_model=ScheduleResponse)
def create_schedule(data: ScheduleCreate, db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    """Добавить запись в расписание (только для админа)"""
    schedule = Schedule(
        date=data.date,
        time=data.time,
        subject=data.subject,
        group_id=data.group_id,
        prepod_id=data.prepod_id,
        classroom=data.classroom,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule

@app.put("/api/admin/schedule/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(schedule_id: int, data: ScheduleUpdate, db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    """Изменить запись в расписании (только для админа)"""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Запись расписания не найдена")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(schedule, key, value)
    db.commit()
    db.refresh(schedule)
    return schedule