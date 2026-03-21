"""
Скрипт заполнения БД тестовыми данными.
Запуск: python seed.py
"""
import os
import datetime

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import Base, User, Group, StudentGroup, Schedule, Grade, Notification

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed():
    db = SessionLocal()
    try:
        # --- Группы ---
        groups_data = [
            {"name_group": "ИУ1-22Б"},
            {"name_group": "ИУ1-21Б"},
            {"name_group": "БМТ2-23Б"},
        ]
        groups = {}
        for g in groups_data:
            existing = db.query(Group).filter(Group.name_group == g["name_group"]).first()
            if existing:
                groups[g["name_group"]] = existing
            else:
                group = Group(**g)
                db.add(group)
                db.flush()
                groups[g["name_group"]] = group

        # --- Пользователи: студенты, преподаватели, админ ---
        users_data = [
            {"role": "student", "name": "Иванов Иван", "login": "student1", "password": "123"},
            {"role": "student", "name": "Петрова Анна", "login": "student2", "password": "123"},
            {"role": "student", "name": "Сидоров Пётр", "login": "student3", "password": "123"},
            {"role": "prepod", "name": "Козлова М.И.", "login": "prepod1", "password": "123"},
            {"role": "prepod", "name": "Новиков А.В.", "login": "prepod2", "password": "123"},
            {"role": "prepod", "name": "Смирнова Е.П.", "login": "prepod3", "password": "123"},
            {"role": "admin", "name": "Администратор", "login": "admin", "password": "admin"},
        ]
        users_by_login = {}
        for u in users_data:
            existing = db.query(User).filter(User.login == u["login"]).first()
            if existing:
                users_by_login[u["login"]] = existing
            else:
                user = User(**u)
                db.add(user)
                db.flush()
                users_by_login[u["login"]] = user

        students = [users_by_login["student1"], users_by_login["student2"], users_by_login["student3"]]
        prepods = [users_by_login["prepod1"], users_by_login["prepod2"], users_by_login["prepod3"]]

        # --- Связь студентов с группами ---
        group_list = [groups["ИУ1-22Б"], groups["ИУ1-21Б"], groups["БМТ2-23Б"]]
        for i, student in enumerate(students):
            sg = db.query(StudentGroup).filter(
                StudentGroup.student_id == student.id,
                StudentGroup.group_id == group_list[i].id
            ).first()
            if not sg:
                db.add(StudentGroup(student_id=student.id, group_id=group_list[i].id))

        # --- Расписание на неделю ---
        # Понедельник–пятница, пары: 9:00, 10:30, 12:00, 14:00
        today = datetime.date.today()
        monday = today - datetime.timedelta(days=today.weekday())
        week_dates = [monday + datetime.timedelta(days=d) for d in range(5)]

        schedule_entries = [
            # (date_offset, time, subject, group_name, prepod_login, classroom)
            (0, "09:00", "Математика", "ИУ1-22Б", "prepod1", "101"),
            (0, "10:30", "Физика", "ИУ1-21Б", "prepod2", "202"),
            (0, "12:00", "Программирование", "БМТ2-23Б", "prepod3", "305"),
            (0, "14:00", "История", "ИУ1-22Б", "prepod3", "102"),
            (1, "09:00", "Программирование", "ИУ1-22Б", "prepod3", "305"),
            (1, "10:30", "Математика", "ИУ1-21Б", "prepod1", "101"),
            (1, "12:00", "Химия", "БМТ2-23Б", "prepod2", "203"),
            (2, "09:00", "Физика", "ИУ1-22Б", "prepod2", "202"),
            (2, "10:30", "Программирование", "ИУ1-21Б", "prepod3", "305"),
            (2, "14:00", "Математика", "БМТ2-23Б", "prepod1", "101"),
            (3, "09:00", "Математика", "ИУ1-22Б", "prepod1", "101"),
            (3, "12:00", "Физика", "ИУ1-21Б", "prepod2", "202"),
            (3, "14:00", "Программирование", "БМТ2-23Б", "prepod3", "305"),
            (4, "09:00", "Химия", "ИУ1-22Б", "prepod2", "203"),
            (4, "10:30", "Программирование", "ИУ1-21Б", "prepod3", "305"),
            (4, "12:00", "Физика", "БМТ2-23Б", "prepod2", "202"),
        ]

        for day_off, time_str, subject, grp_name, prepod_login, classroom in schedule_entries:
            date = week_dates[day_off]
            hour, minute = map(int, time_str.split(":"))
            time_val = datetime.time(hour, minute)
            grp = groups[grp_name]
            prepod = users_by_login[prepod_login]
            existing = db.query(Schedule).filter(
                Schedule.date == date,
                Schedule.time == time_val,
                Schedule.group_id == grp.id,
            ).first()
            if not existing:
                db.add(Schedule(
                    date=date,
                    time=time_val,
                    subject=subject,
                    group_id=grp.id,
                    prepod_id=prepod.id,
                    classroom=classroom,
                ))

        # --- Примеры оценок ---
        grade_entries = [
            (students[0].id, prepods[0].id, "Математика", 5, "Отличная работа"),
            (students[0].id, prepods[2].id, "Программирование", 4, None),
            (students[1].id, prepods[0].id, "Математика", 4, None),
            (students[2].id, prepods[2].id, "Программирование", 5, "Молодец!"),
        ]
        for student_id, prepod_id, subject, value, comment in grade_entries:
            existing_grade = db.query(Grade).filter(
                Grade.student_id == student_id,
                Grade.subject == subject,
                Grade.prepod_id == prepod_id,
            ).first()
            if not existing_grade:
                g = Grade(student_id=student_id, prepod_id=prepod_id, subject=subject, value=value, comment=comment)
                db.add(g)
                db.flush()
                msg = f"Поставлена оценка {value} по предмету «{subject}»"
                db.add(Notification(student_id=student_id, grade_id=g.id, message=msg, is_read=0))

        db.commit()
        print("✓ Данные успешно добавлены (включая примеры оценок)")
        print("  Группы: ИУ1-22Б, ИУ1-21Б, БМТ2-23Б")
        print("  Студенты: student1/123, student2/123, student3/123")
        print("  Преподаватели: prepod1/123, prepod2/123, prepod3/123")
        print("  Админ: admin/admin")
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
