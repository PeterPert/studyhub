import logging
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Request, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import OperationalError
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Date,
    Time,
    DateTime,
    ForeignKey,
    Text,
    text,
    UniqueConstraint,
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pydantic import BaseModel
from typing import List, Optional
import datetime
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# --- 1. БАЗА ДАННЫХ ---
# PostgreSQL: DATABASE_URL=postgresql://...
# Если переменная не задана — локальный SQLite (файл back/studyhub_local.db), чтобы API и бот работали без установки PostgreSQL.
_BACK_DIR = Path(__file__).resolve().parent
_SQLITE_FILE = _BACK_DIR / "studyhub_local.db"
SQLALCHEMY_DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()
if not SQLALCHEMY_DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{_SQLITE_FILE.as_posix()}"
    logger.info("DATABASE_URL не задан — используется SQLite: %s", _SQLITE_FILE)

_IS_SQLITE = SQLALCHEMY_DATABASE_URL.startswith("sqlite")
_engine_kw: dict = {}
if _IS_SQLITE:
    _engine_kw["connect_args"] = {"check_same_thread": False}
else:
    _engine_kw["pool_pre_ping"] = True

engine = create_engine(SQLALCHEMY_DATABASE_URL, **_engine_kw)
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
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=True)
    message = Column(String)
    is_read = Column(Integer, default=0)  # 0=unread, 1=read
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Assignment(Base):
    """Задание от преподавателя для группы."""
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True, index=True)
    prepod_id = Column(Integer, ForeignKey("users.id"))
    group_id = Column(Integer, ForeignKey("groups.id"))
    subject = Column(String)
    description = Column(Text)
    published = Column(Integer, default=1)  # 1 = опубликовано
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class AssignmentStudentState(Base):
    """Статус студента по заданию: в процессе / сдано; засчитано преподавателем."""
    __tablename__ = "assignment_student_states"
    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"))
    student_id = Column(Integer, ForeignKey("users.id"))
    # student_status: "in_progress" | "submitted"
    student_status = Column(String, default="in_progress")
    # teacher_accepted: 1 = засчитано, иначе NULL/0 — задание ещё в ленте / на проверке
    teacher_accepted = Column(Integer, nullable=True, default=None)  # 1 accepted

    __table_args__ = (UniqueConstraint("assignment_id", "student_id", name="uq_assignment_student"),)


# Создаем таблицы (если их нет)
Base.metadata.create_all(bind=engine)


def _migrate_postgres_notifications():
    """Существующие БД PostgreSQL: сделать grade_id nullable и добавить assignment_id."""
    if _IS_SQLITE:
        return
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE notifications ALTER COLUMN grade_id DROP NOT NULL"))
    except Exception:
        pass
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS assignment_id INTEGER REFERENCES assignments(id)"
                )
            )
    except Exception:
        pass


_migrate_postgres_notifications()

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


class StudentGroupNameResponse(BaseModel):
    group_name: str


class NotificationResponse(BaseModel):
    id: int
    grade_id: Optional[int] = None
    assignment_id: Optional[int] = None
    message: str
    is_read: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class GroupOption(BaseModel):
    id: int
    name: str


class AssignmentMetaResponse(BaseModel):
    subjects: List[str]
    groups: List[GroupOption]


class AssignmentCreate(BaseModel):
    subject: str
    description: str
    group_id: int


class AssignmentStudentStatusRow(BaseModel):
    student_id: int
    student_name: str
    student_status: str  # in_progress | submitted
    teacher_accepted: bool


class AssignmentTeacherItem(BaseModel):
    id: int
    subject: str
    description: str
    group_id: int
    group_name: str
    created_at: datetime.datetime
    students: List[AssignmentStudentStatusRow]


class StudentAssignmentItem(BaseModel):
    id: int
    subject: str
    description: str
    prepod_name: str
    created_at: datetime.datetime
    student_status: str


class StudentAssignmentStatusUpdate(BaseModel):
    student_status: str  # in_progress | submitted


class TeacherAssignmentReview(BaseModel):
    student_id: int
    accept: bool  # True = засчитать, False = вернуть в «в процессе»

# --- 4. FASTAPI ПРИЛОЖЕНИЕ И РУЧКИ ---

app = FastAPI(title="Schedule API")


@app.exception_handler(OperationalError)
async def db_operational_error_handler(request: Request, exc: OperationalError) -> JSONResponse:
    logger.exception("Ошибка подключения к БД: %s", exc)
    return JSONResponse(
        status_code=503,
        content={
            "detail": (
                "База данных недоступна. Если в .env указан PostgreSQL — запустите службу PostgreSQL "
                "или проверьте DATABASE_URL. Для локальной работы без PostgreSQL удалите строку DATABASE_URL "
                "из .env — тогда будет использоваться файл back/studyhub_local.db (SQLite). "
                "После смены БД выполните: python seed.py"
            )
        },
    )


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


@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """Проверка, что API и база отвечают (удобно для отладки бота и деплоя)."""
    db.execute(text("SELECT 1"))
    return {"ok": True, "database": "sqlite" if _IS_SQLITE else "postgresql"}


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


@app.get("/api/student/{student_id}/group", response_model=StudentGroupNameResponse)
def get_student_group_name(
    student_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(verify_student),
):
    """Название учебной группы студента (для шапки интерфейса)."""
    link = db.query(StudentGroup).filter(StudentGroup.student_id == student_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Студент не привязан к группе")
    g = db.query(Group).filter(Group.id == link.group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Группа не найдена")
    return StudentGroupNameResponse(group_name=g.name_group)


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


# --- ЗАДАНИЯ (преподаватель / студент) ---


def _get_or_create_assignment_state(
    db: Session, assignment_id: int, student_id: int
) -> AssignmentStudentState:
    row = (
        db.query(AssignmentStudentState)
        .filter(
            AssignmentStudentState.assignment_id == assignment_id,
            AssignmentStudentState.student_id == student_id,
        )
        .first()
    )
    if not row:
        row = AssignmentStudentState(
            assignment_id=assignment_id,
            student_id=student_id,
            student_status="in_progress",
        )
        db.add(row)
        db.flush()
    return row


@app.get("/api/prepod/{prepod_id}/assignment-meta", response_model=AssignmentMetaResponse)
def get_assignment_meta(
    prepod_id: int,
    db: Session = Depends(get_db),
    prepod: User = Depends(get_prepod),
):
    if prepod.id != prepod_id:
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    rows = db.query(Schedule).filter(Schedule.prepod_id == prepod_id).all()
    subjects = sorted({r.subject for r in rows if r.subject})
    group_ids = sorted({r.group_id for r in rows if r.group_id})
    groups_out: List[GroupOption] = []
    for gid in group_ids:
        g = db.query(Group).filter(Group.id == gid).first()
        if g:
            groups_out.append(GroupOption(id=g.id, name=g.name_group))
    return AssignmentMetaResponse(subjects=subjects, groups=groups_out)


@app.post("/api/prepod/assignments")
def create_assignment(
    data: AssignmentCreate,
    db: Session = Depends(get_db),
    prepod: User = Depends(get_prepod),
):
    """Опубликовать задание для группы по предмету из расписания."""
    has_slot = (
        db.query(Schedule)
        .filter(
            Schedule.prepod_id == prepod.id,
            Schedule.group_id == data.group_id,
            Schedule.subject == data.subject,
        )
        .first()
    )
    if not has_slot:
        raise HTTPException(
            status_code=400,
            detail="Нет занятий по этому предмету у выбранной группы в расписании",
        )
    if not data.description.strip():
        raise HTTPException(status_code=400, detail="Введите описание задания")
    a = Assignment(
        prepod_id=prepod.id,
        group_id=data.group_id,
        subject=data.subject.strip(),
        description=data.description.strip(),
        published=1,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return {"id": a.id, "ok": True}


@app.get("/api/prepod/{prepod_id}/assignments", response_model=List[AssignmentTeacherItem])
def list_prepod_assignments(
    prepod_id: int,
    db: Session = Depends(get_db),
    prepod: User = Depends(get_prepod),
):
    if prepod.id != prepod_id:
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    items = (
        db.query(Assignment)
        .filter(Assignment.prepod_id == prepod_id)
        .order_by(Assignment.created_at.desc())
        .all()
    )
    out: List[AssignmentTeacherItem] = []
    for a in items:
        g = db.query(Group).filter(Group.id == a.group_id).first()
        group_name = g.name_group if g else ""
        links = (
            db.query(StudentGroup, User)
            .join(User, StudentGroup.student_id == User.id)
            .filter(StudentGroup.group_id == a.group_id, User.role == "student")
            .all()
        )
        students: List[AssignmentStudentStatusRow] = []
        for _sg, u in links:
            st = (
                db.query(AssignmentStudentState)
                .filter(
                    AssignmentStudentState.assignment_id == a.id,
                    AssignmentStudentState.student_id == u.id,
                )
                .first()
            )
            status_s = st.student_status if st else "in_progress"
            accepted = bool(st and (st.teacher_accepted == 1))
            students.append(
                AssignmentStudentStatusRow(
                    student_id=u.id,
                    student_name=u.name,
                    student_status=status_s,
                    teacher_accepted=accepted,
                )
            )
        students.sort(key=lambda x: x.student_name)
        out.append(
            AssignmentTeacherItem(
                id=a.id,
                subject=a.subject,
                description=a.description,
                group_id=a.group_id,
                group_name=group_name,
                created_at=a.created_at,
                students=students,
            )
        )
    return out


@app.get("/api/student/{student_id}/assignments", response_model=List[StudentAssignmentItem])
def list_student_assignments(
    student_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(verify_student),
):
    link = db.query(StudentGroup).filter(StudentGroup.student_id == student_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Студент не привязан к группе")
    rows = (
        db.query(Assignment)
        .filter(Assignment.group_id == link.group_id, Assignment.published == 1)
        .order_by(Assignment.created_at.desc())
        .all()
    )
    result: List[StudentAssignmentItem] = []
    for a in rows:
        st = (
            db.query(AssignmentStudentState)
            .filter(
                AssignmentStudentState.assignment_id == a.id,
                AssignmentStudentState.student_id == student_id,
            )
            .first()
        )
        if st and st.teacher_accepted == 1:
            continue
        prep = db.query(User).filter(User.id == a.prepod_id).first()
        result.append(
            StudentAssignmentItem(
                id=a.id,
                subject=a.subject,
                description=a.description,
                prepod_name=prep.name if prep else "",
                created_at=a.created_at,
                student_status=st.student_status if st else "in_progress",
            )
        )
    return result


@app.patch("/api/student/{student_id}/assignments/{assignment_id}/status")
def patch_student_assignment_status(
    student_id: int,
    assignment_id: int,
    data: StudentAssignmentStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(verify_student),
):
    if data.student_status not in ("in_progress", "submitted"):
        raise HTTPException(status_code=400, detail="Статус: in_progress или submitted")
    a = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    link = db.query(StudentGroup).filter(StudentGroup.student_id == student_id).first()
    if not link or link.group_id != a.group_id:
        raise HTTPException(status_code=403, detail="Задание не для вашей группы")
    row = _get_or_create_assignment_state(db, assignment_id, student_id)
    if row.teacher_accepted == 1:
        raise HTTPException(status_code=400, detail="Задание уже засчитано")
    row.student_status = data.student_status
    db.commit()
    return {"ok": True}


@app.patch("/api/prepod/assignments/{assignment_id}/review")
def review_assignment_student(
    assignment_id: int,
    data: TeacherAssignmentReview,
    db: Session = Depends(get_db),
    prepod: User = Depends(get_prepod),
):
    a = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    if a.prepod_id != prepod.id:
        raise HTTPException(status_code=403, detail="Это не ваше задание")
    row = (
        db.query(AssignmentStudentState)
        .filter(
            AssignmentStudentState.assignment_id == assignment_id,
            AssignmentStudentState.student_id == data.student_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Нет статуса по этому студенту")
    if row.student_status != "submitted":
        raise HTTPException(
            status_code=400,
            detail="Студент ещё не отметил задание как сданное",
        )
    if data.accept:
        row.teacher_accepted = 1
        msg = f"Домашнее задание «{a.subject}»: статус изменён — работа засчитана."
        n = Notification(
            student_id=data.student_id,
            grade_id=None,
            assignment_id=assignment_id,
            message=msg,
            is_read=0,
        )
        db.add(n)
    else:
        row.student_status = "in_progress"
        row.teacher_accepted = None
        msg = (
            f"Домашнее задание «{a.subject}»: статус изменён — не засчитано. "
            f"Верните задание в работу и при необходимости снова отметьте сдачу."
        )
        n = Notification(
            student_id=data.student_id,
            grade_id=None,
            assignment_id=assignment_id,
            message=msg,
            is_read=0,
        )
        db.add(n)
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