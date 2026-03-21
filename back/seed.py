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

from main import User, Group, StudentGroup, Schedule, Grade, Notification

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

        # --- Пользователи: студенты (15), преподаватели (6), админ ---
        student_names = [
            "Иванов Иван",
            "Петрова Анна",
            "Сидоров Пётр",
            "Кузнецова Мария",
            "Волков Дмитрий",
            "Морозова Елена",
            "Соколов Андрей",
            "Лебедева Ольга",
            "Новиков Илья",
            "Фёдорова Татьяна",
            "Козлов Артём",
            "Михайлова София",
            "Андреев Никита",
            "Егорова Виктория",
            "Романов Максим",
        ]
        users_data = [
            {
                "role": "student",
                "name": student_names[i - 1],
                "login": f"student{i}",
                "password": "123",
            }
            for i in range(1, 16)
        ]
        users_data += [
            {"role": "prepod", "name": "Козлова М.И.", "login": "prepod1", "password": "123"},
            {"role": "prepod", "name": "Новиков А.В.", "login": "prepod2", "password": "123"},
            {"role": "prepod", "name": "Смирнова Е.П.", "login": "prepod3", "password": "123"},
            {"role": "prepod", "name": "Васильев К.Д.", "login": "prepod4", "password": "123"},
            {"role": "prepod", "name": "Орлова Н.С.", "login": "prepod5", "password": "123"},
            {"role": "prepod", "name": "Громов П.А.", "login": "prepod6", "password": "123"},
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

        students = [users_by_login[f"student{i}"] for i in range(1, 16)]
        prepods = [users_by_login[f"prepod{i}"] for i in range(1, 7)]

        # --- Связь студентов с группами: по 5 человек на группу ---
        group_list = [groups["ИУ1-22Б"], groups["ИУ1-21Б"], groups["БМТ2-23Б"]]
        for i, student in enumerate(students):
            gid = group_list[i // 5].id
            # Убрать лишние привязки, оставить одну нужную (удобно при повторном seed)
            for link in db.query(StudentGroup).filter(StudentGroup.student_id == student.id).all():
                if link.group_id != gid:
                    db.delete(link)
            if not db.query(StudentGroup).filter(
                StudentGroup.student_id == student.id,
                StudentGroup.group_id == gid,
            ).first():
                db.add(StudentGroup(student_id=student.id, group_id=gid))

        # --- Расписание на неделю (Пн–Пт): много пар в день на каждую группу ---
        # Понедельник–пятница; пары в день: до 6–7 слотов (08:30 … 17:30)
        today = datetime.date.today()
        monday = today - datetime.timedelta(days=today.weekday())
        week_dates = [monday + datetime.timedelta(days=d) for d in range(5)]

        G1, G2, G3 = "ИУ1-22Б", "ИУ1-21Б", "БМТ2-23Б"

        # (день_0_4, время, предмет, группа, преподаватель login, аудитория)
        schedule_entries = [
            # ——— Понедельник ———
            (0, "08:30", "Математика", G1, "prepod1", "101"),
            (0, "08:30", "Физика", G2, "prepod2", "202"),
            (0, "08:30", "Программирование", G3, "prepod3", "305"),
            (0, "10:00", "Физика", G1, "prepod2", "202"),
            (0, "10:00", "Математика", G2, "prepod1", "101"),
            (0, "10:00", "Инженерная графика", G3, "prepod4", "401"),
            (0, "11:30", "Программирование", G1, "prepod3", "305"),
            (0, "11:30", "Химия", G2, "prepod2", "203"),
            (0, "11:30", "Физика", G3, "prepod2", "202"),
            (0, "13:00", "История", G1, "prepod3", "102"),
            (0, "13:00", "Базы данных", G2, "prepod3", "306"),
            (0, "13:00", "Математика", G3, "prepod1", "101"),
            (0, "14:30", "Английский язык", G1, "prepod5", "103"),
            (0, "14:30", "Программирование", G2, "prepod3", "305"),
            (0, "14:30", "Электротехника", G3, "prepod6", "204"),
            (0, "16:00", "ОПД", G1, "prepod1", "104"),
            (0, "16:00", "Английский язык", G2, "prepod5", "103"),
            (0, "16:00", "Инженерная графика", G3, "prepod4", "401"),
            # ——— Вторник ———
            (1, "08:30", "Программирование", G1, "prepod3", "305"),
            (1, "08:30", "Химия", G2, "prepod2", "203"),
            (1, "08:30", "Математика", G3, "prepod1", "101"),
            (1, "10:00", "Математика", G1, "prepod1", "101"),
            (1, "10:00", "Программирование", G2, "prepod3", "305"),
            (1, "10:00", "Физика", G3, "prepod2", "202"),
            (1, "11:30", "Физика", G1, "prepod2", "202"),
            (1, "11:30", "Базы данных", G2, "prepod3", "306"),
            (1, "11:30", "Программирование", G3, "prepod3", "305"),
            (1, "13:00", "Английский язык", G1, "prepod5", "103"),
            (1, "13:00", "Математика", G2, "prepod1", "101"),
            (1, "13:00", "Химия", G3, "prepod2", "203"),
            (1, "14:30", "История", G1, "prepod3", "102"),
            (1, "14:30", "Электротехника", G2, "prepod6", "204"),
            (1, "14:30", "Инженерная графика", G3, "prepod4", "401"),
            (1, "16:00", "Электротехника", G1, "prepod6", "204"),
            (1, "16:00", "Физкультура", G2, "prepod4", "Спортзал"),
            (1, "16:00", "ОПД", G3, "prepod1", "104"),
            # ——— Среда ———
            (2, "08:30", "Физика", G1, "prepod2", "202"),
            (2, "08:30", "Программирование", G2, "prepod3", "305"),
            (2, "08:30", "Электротехника", G3, "prepod6", "204"),
            (2, "10:00", "Программирование", G1, "prepod3", "305"),
            (2, "10:00", "Физика", G2, "prepod2", "202"),
            (2, "10:00", "Математика", G3, "prepod1", "101"),
            (2, "11:30", "Математика", G1, "prepod1", "101"),
            (2, "11:30", "Химия", G2, "prepod2", "203"),
            (2, "11:30", "Физика", G3, "prepod2", "202"),
            (2, "13:00", "Базы данных", G1, "prepod3", "306"),
            (2, "13:00", "Английский язык", G2, "prepod5", "103"),
            (2, "13:00", "Программирование", G3, "prepod3", "305"),
            (2, "14:30", "История", G2, "prepod3", "102"),
            (2, "14:30", "Инженерная графика", G1, "prepod4", "401"),
            (2, "14:30", "Английский язык", G3, "prepod5", "103"),
            (2, "16:00", "ОПД", G2, "prepod1", "104"),
            (2, "16:00", "Физкультура", G1, "prepod4", "Спортзал"),
            (2, "16:00", "Химия", G3, "prepod2", "203"),
            # ——— Четверг ———
            (3, "08:30", "Математика", G1, "prepod1", "101"),
            (3, "08:30", "Физика", G2, "prepod2", "202"),
            (3, "08:30", "Инженерная графика", G3, "prepod4", "401"),
            (3, "10:00", "Программирование", G1, "prepod3", "305"),
            (3, "10:00", "Математика", G2, "prepod1", "101"),
            (3, "10:00", "Физика", G3, "prepod2", "202"),
            (3, "11:30", "Физика", G1, "prepod2", "202"),
            (3, "11:30", "Программирование", G2, "prepod3", "305"),
            (3, "11:30", "Базы данных", G3, "prepod3", "306"),
            (3, "13:00", "Английский язык", G1, "prepod5", "103"),
            (3, "13:00", "Электротехника", G2, "prepod6", "204"),
            (3, "13:00", "Математика", G3, "prepod1", "101"),
            (3, "14:30", "История", G3, "prepod3", "102"),
            (3, "14:30", "Химия", G1, "prepod2", "203"),
            (3, "14:30", "Базы данных", G2, "prepod3", "306"),
            (3, "16:00", "Электротехника", G1, "prepod6", "204"),
            (3, "16:00", "ОПД", G3, "prepod1", "104"),
            (3, "16:00", "Физкультура", G2, "prepod4", "Спортзал"),
            # ——— Пятница ———
            (4, "08:30", "Химия", G1, "prepod2", "203"),
            (4, "08:30", "Математика", G2, "prepod1", "101"),
            (4, "08:30", "Программирование", G3, "prepod3", "305"),
            (4, "10:00", "Программирование", G1, "prepod3", "305"),
            (4, "10:00", "Физика", G2, "prepod2", "202"),
            (4, "10:00", "Математика", G3, "prepod1", "101"),
            (4, "11:30", "Математика", G1, "prepod1", "101"),
            (4, "11:30", "Программирование", G2, "prepod3", "305"),
            (4, "11:30", "Физика", G3, "prepod2", "202"),
            (4, "13:00", "Физика", G1, "prepod2", "202"),
            (4, "13:00", "Английский язык", G2, "prepod5", "103"),
            (4, "13:00", "Электротехника", G3, "prepod6", "204"),
            (4, "14:30", "Инженерная графика", G2, "prepod4", "401"),
            (4, "14:30", "История", G1, "prepod3", "102"),
            (4, "14:30", "ОПД", G3, "prepod1", "104"),
            (4, "16:00", "Базы данных", G1, "prepod3", "306"),
            (4, "16:00", "Электротехника", G2, "prepod6", "204"),
            (4, "16:00", "Физкультура", G3, "prepod4", "Спортзал"),
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
                db.add(
                    Schedule(
                        date=date,
                        time=time_val,
                        subject=subject,
                        group_id=grp.id,
                        prepod_id=prepod.id,
                        classroom=classroom,
                    )
                )

        # --- Примеры оценок (расширено) ---
        grade_entries = [
            (students[0].id, prepods[0].id, "Математика", 5, "Отличная работа"),
            (students[0].id, prepods[2].id, "Программирование", 4, None),
            (students[1].id, prepods[0].id, "Математика", 4, None),
            (students[2].id, prepods[2].id, "Программирование", 5, "Молодец!"),
            (students[3].id, prepods[1].id, "Физика", 5, None),
            (students[5].id, prepods[3].id, "Инженерная графика", 4, "Хорошо"),
            (students[7].id, prepods[4].id, "Английский язык", 5, None),
            (students[10].id, prepods[5].id, "Электротехника", 4, None),
            (students[12].id, prepods[2].id, "Базы данных", 5, None),
        ]
        for student_id, prepod_id, subject, value, comment in grade_entries:
            existing_grade = db.query(Grade).filter(
                Grade.student_id == student_id,
                Grade.subject == subject,
                Grade.prepod_id == prepod_id,
            ).first()
            if not existing_grade:
                g = Grade(
                    student_id=student_id,
                    prepod_id=prepod_id,
                    subject=subject,
                    value=value,
                    comment=comment,
                )
                db.add(g)
                db.flush()
                msg = f"Поставлена оценка {value} по предмету «{subject}»"
                db.add(Notification(student_id=student_id, grade_id=g.id, message=msg, is_read=0))

        db.commit()
        print("✓ Данные успешно добавлены (включая примеры оценок)")
        print("  Группы: ИУ1-22Б, ИУ1-21Б, БМТ2-23Б (по 5 студентов в каждой)")
        print("  Студенты: student1 … student15 / пароль 123")
        print("  Преподаватели: prepod1 … prepod6 / пароль 123")
        print("  Админ: admin / admin")
        print("  Расписание: до 6–7 пар в день на группу (Пн–Пт), больше предметов и аудиторий")
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
