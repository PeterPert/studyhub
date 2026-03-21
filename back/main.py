from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Date, Time, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
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


class Grade(Base):
    __tablename__ = "grades"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    prepod_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String)
    value = Column(Integer)  # 2-5
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    grade_id = Column(Integer, ForeignKey("grades.id"))
    message = Column(String)
    is_read = Column(Integer, default=0)  # 0=unread, 1=read
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

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


class GradeCreate(BaseModel):
    student_id: int
    subject: str
    value: int  # 2-5
    comment: Optional[str] = None


class GradeResponse(BaseModel):
    id: int
    student_id: int
    prepod_id: int
    subject: str
    value: int
    comment: Optional[str] = None
    created_at: datetime.datetime
    prepod_name: Optional[str] = None

    class Config:
        from_attributes = True


class StudentOption(BaseModel):
    id: int
    name: str
    group_name: str


class NotificationResponse(BaseModel):
    id: int
    grade_id: int
    message: str
    is_read: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True

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


# Проверка прав преподавателя (X-User-Id)
def get_prepod(user_id: Optional[int] = Header(None, alias="X-User-Id"), db: Session = Depends(get_db)):
    if user_id is None:
        raise HTTPException(status_code=401, detail="Требуется заголовок X-User-Id")
    user = db.query(User).filter(User.id == user_id, User.role == "prepod").first()
    if not user:
        raise HTTPException(status_code=403, detail="Доступ только для преподавателей.")
    return user


# Проверка что студент смотрит только свои данные (X-User-Id должен совпадать с student_id)
def verify_student(student_id: int, user_id: Optional[int] = Header(None, alias="X-User-Id"), db: Session = Depends(get_db)):
    if user_id is None:
        raise HTTPException(status_code=401, detail="Требуется заголовок X-User-Id")
    user = db.query(User).filter(User.id == user_id, User.role == "student").first()
    if not user or user.id != student_id:
        raise HTTPException(status_code=403, detail="Доступ запрещён.")
    return user

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/app", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

@app.get("/")
def root():
    return RedirectResponse(url="/app/")

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


# --- ОЦЕНКИ И УВЕДОМЛЕНИЯ ---

@app.get("/api/prepod/{prepod_id}/students", response_model=List[StudentOption])
def get_prepod_students(prepod_id: int, db: Session = Depends(get_db), prepod: User = Depends(get_prepod)):
    """Список студентов в группах, которые ведёт преподаватель"""
    if prepod.id != prepod_id:
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    # Группы преподавателя из расписания
    group_ids = db.query(Schedule.group_id).filter(Schedule.prepod_id == prepod_id).distinct().all()
    group_ids = [g[0] for g in group_ids if g[0]]
    if not group_ids:
        return []
    # Студенты в этих группах
    links = db.query(StudentGroup, User, Group).join(User, StudentGroup.student_id == User.id).join(
        Group, StudentGroup.group_id == Group.id
    ).filter(StudentGroup.group_id.in_(group_ids)).all()
    seen = set()
    result = []
    for sg, u, g in links:
        if u.id not in seen:
            seen.add(u.id)
            result.append(StudentOption(id=u.id, name=u.name, group_name=g.name_group))
    return sorted(result, key=lambda x: (x.group_name, x.name))


@app.post("/api/prepod/grades", response_model=GradeResponse)
def create_grade(data: GradeCreate, db: Session = Depends(get_db), prepod: User = Depends(get_prepod)):
    """Преподаватель выставляет оценку студенту"""
    if not 2 <= data.value <= 5:
        raise HTTPException(status_code=400, detail="Оценка должна быть от 2 до 5")
    student = db.query(User).filter(User.id == data.student_id, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")
    grade = Grade(student_id=data.student_id, prepod_id=prepod.id, subject=data.subject, value=data.value, comment=data.comment)
    db.add(grade)
    db.flush()
    msg = f"Поставлена оценка {data.value} по предмету «{data.subject}»"
    notif = Notification(student_id=data.student_id, grade_id=grade.id, message=msg)
    db.add(notif)
    db.commit()
    db.refresh(grade)
    return grade


@app.get("/api/student/{student_id}/grades", response_model=List[GradeResponse])
def get_student_grades(student_id: int, db: Session = Depends(get_db), _: User = Depends(verify_student)):
    """Студент получает свои оценки"""
    grades = db.query(Grade, User).join(User, Grade.prepod_id == User.id).filter(
        Grade.student_id == student_id
    ).order_by(Grade.created_at.desc()).all()
    return [
        GradeResponse(
            id=g.id, student_id=g.student_id, prepod_id=g.prepod_id, subject=g.subject,
            value=g.value, comment=g.comment, created_at=g.created_at, prepod_name=u.name
        )
        for g, u in grades
    ]


@app.get("/api/student/{student_id}/notifications", response_model=List[NotificationResponse])
def get_student_notifications(
    student_id: int,
    unread_only: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(verify_student),
):
    """Уведомления студента"""
    q = db.query(Notification).filter(Notification.student_id == student_id)
    if unread_only:
        q = q.filter(Notification.is_read == 0)
    notifs = q.order_by(Notification.created_at.desc()).limit(50).all()
    return notifs


@app.get("/api/student/{student_id}/notifications/unread-count")
def get_unread_count(student_id: int, db: Session = Depends(get_db), _: User = Depends(verify_student)):
    """Количество непрочитанных уведомлений"""
    count = db.query(Notification).filter(Notification.student_id == student_id, Notification.is_read == 0).count()
    return {"count": count}


@app.patch("/api/student/{student_id}/notifications/{notif_id}/read")
def mark_notification_read(
    student_id: int, notif_id: int, db: Session = Depends(get_db), _: User = Depends(verify_student)
):
    notif = db.query(Notification).filter(Notification.id == notif_id, Notification.student_id == student_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Уведомление не найдено")
    notif.is_read = 1
    db.commit()
    return {"ok": True}


@app.patch("/api/student/{student_id}/notifications/read-all")
def mark_all_notifications_read(student_id: int, db: Session = Depends(get_db), _: User = Depends(verify_student)):
    db.query(Notification).filter(Notification.student_id == student_id, Notification.is_read == 0).update(
        {Notification.is_read: 1}
    )
    db.commit()
    return {"ok": True}


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