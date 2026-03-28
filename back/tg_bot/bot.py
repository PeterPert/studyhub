"""
Telegram-бот для StudyHub: вход по логину/паролю API, расписание, напоминания, дублирование уведомлений.

Запуск (из папки back, с активным venv и запущенным FastAPI):
  python -m tg_bot.bot

Переменные окружения (в .env рядом с main.py или в корне back):
  TELEGRAM_BOT_TOKEN — токен от @BotFather (обязательно)
  API_BASE_URL — по умолчанию http://127.0.0.1:8000
"""
from __future__ import annotations

import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tg_bot.storage import Storage

# Всегда подхватываем back/.env (не зависит от текущей папки запуска)
_BACK_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_BACK_DIR / ".env")
# Дополнительно: .env из cwd, если запускают из другого места
load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _normalize_api_base(raw: str) -> str:
    """База без хвоста /api — пути вида /api/login добавляем сами."""
    u = (raw or "http://127.0.0.1:8000").strip().rstrip("/")
    if u.lower().endswith("/api"):
        u = u[:-4].rstrip("/")
    return u


# Токен только из окружения / .env (не вшивать в код)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8633452808:AAFQd9wMQuMQpPAtftQ-x-nK0UPYu4ogDvo").strip()
API_BASE_URL = _normalize_api_base(os.getenv("API_BASE_URL", "http://127.0.0.1:8000"))

WAIT_LOGIN, WAIT_PASSWORD = range(2)

BTN_SCHEDULE = "📅 Расписание на сегодня"

DAYS_SHORT = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
DAYS_LONG = [
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье",
]

# Ключи напоминаний за сессию процесса (чтобы не слать дважды)
_reminder_sent: set[str] = set()


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[BTN_SCHEDULE]],
        resize_keyboard=True,
        input_field_placeholder="Меню",
    )


async def api_login(client: httpx.AsyncClient, login: str, password: str) -> dict[str, Any]:
    url = f"{API_BASE_URL}/api/login"
    try:
        r = await client.post(url, json={"login": login, "password": password})
    except httpx.RequestError as e:
        raise ConnectionError(
            "Не удаётся связаться с сервером StudyHub.\n\n"
            f"Адрес API: {API_BASE_URL}\n"
            "Запустите бэкенд в отдельном терминале из папки back:\n"
            "  uvicorn main:app --host 127.0.0.1 --port 8000\n\n"
            f"Ошибка сети: {e}"
        ) from e
    if r.status_code != 200:
        raise ValueError(detail_from_response(r))
    return r.json()


def detail_from_response(r: httpx.Response) -> str:
    try:
        data = r.json()
        d = data.get("detail")
        if isinstance(d, str):
            return d
        if isinstance(d, list) and d:
            return str(d[0].get("msg", d))
    except Exception:
        pass
    t = (r.text or "").strip()
    if t:
        return t[:2000]
    if r.status_code == 503:
        return (
            "Сервер вернул 503 без ответа. Частые причины: не запущен uvicorn, "
            "PostgreSQL недоступен при DATABASE_URL в .env, или неверный API_BASE_URL у бота. "
            "Проверьте GET http://127.0.0.1:8000/api/health в браузере. "
            "Для работы без PostgreSQL удалите строку DATABASE_URL из back/.env — будет SQLite (studyhub_local.db), затем: python seed.py"
        )
    return f"HTTP {r.status_code}"


async def api_schedule_student(
    client: httpx.AsyncClient, user_id: int, day_of_week: int
) -> list[dict[str, Any]]:
    r = await client.get(
        f"{API_BASE_URL}/api/schedule/student/{user_id}",
        params={"day_of_week": day_of_week},
    )
    if r.status_code != 200:
        raise ValueError(detail_from_response(r))
    return r.json()


async def api_schedule_teacher(
    client: httpx.AsyncClient, user_id: int, day_of_week: int
) -> list[dict[str, Any]]:
    r = await client.get(
        f"{API_BASE_URL}/api/schedule/teacher/{user_id}",
        params={"day_of_week": day_of_week},
    )
    if r.status_code != 200:
        raise ValueError(detail_from_response(r))
    return r.json()


async def api_notifications(client: httpx.AsyncClient, user_id: int) -> list[dict[str, Any]]:
    r = await client.get(
        f"{API_BASE_URL}/api/student/{user_id}/notifications",
        headers={"X-User-Id": str(user_id)},
    )
    if r.status_code != 200:
        raise ValueError(detail_from_response(r))
    return r.json()


def format_schedule_lines(items: list[dict[str, Any]], title: str) -> str:
    if not items:
        return f"{title}\n\nПар на этот день нет."
    lines = [title, ""]
    for it in sorted(items, key=lambda x: (x.get("time") or "")):
        t = (it.get("time") or "")[:5]
        subj = it.get("subject") or "?"
        room = it.get("classroom") or "—"
        lines.append(f"• {t} — {subj} (ауд. {room})")
    return "\n".join(lines)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ConversationHandler.END
    chat_id = update.effective_chat.id
    storage: Storage = context.application.bot_data["storage"]
    client: httpx.AsyncClient = context.application.bot_data["http"]

    sess = storage.get_session(chat_id)
    if sess:
        await update.message.reply_text(
            f"Вы уже вошли как {sess['name']} ({sess['login']}).\n"
            f"Роль: {'студент' if sess['role'] == 'student' else 'преподаватель'}.\n\n"
            "Используйте кнопку ниже или /logout для выхода.",
            reply_markup=main_keyboard(),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Добро пожаловать в StudyHub.\n\n"
        "Введите **логин** от сайта (как при входе в браузере):",
        parse_mode="Markdown",
    )
    return WAIT_LOGIN


async def receive_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("Введите логин текстом.")
        return WAIT_LOGIN
    context.user_data["login"] = text
    await update.message.reply_text("Введите **пароль**:", parse_mode="Markdown")
    return WAIT_PASSWORD


async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ConversationHandler.END
    password = (update.message.text or "").strip()
    login = context.user_data.get("login", "").strip()
    chat_id = update.effective_chat.id
    storage: Storage = context.application.bot_data["storage"]
    client: httpx.AsyncClient = context.application.bot_data["http"]

    try:
        data = await api_login(client, login, password)
    except ConnectionError as e:
        logger.warning("login connection: %s", e)
        await update.message.reply_text(str(e))
        return ConversationHandler.END
    except ValueError as e:
        logger.info("login rejected: %s", e)
        await update.message.reply_text(
            f"{e}\n\n"
            "Если логин и пароль точно как на сайте:\n"
            "• в папке back выполните: python seed.py\n"
            "• API и сайт должны использовать одну и ту же БД (DATABASE_URL в .env)."
        )
        return ConversationHandler.END
    except Exception as e:
        logger.exception("login failed: %s", e)
        await update.message.reply_text(
            f"Ошибка при входе: {e}\n\nПовторите /start или проверьте логи бота в терминале."
        )
        return ConversationHandler.END

    role = data.get("role")
    if role not in ("student", "prepod"):
        await update.message.reply_text("Вход в бота только для студентов и преподавателей.")
        return ConversationHandler.END

    user_id = data["id"]
    name = data.get("name") or login

    last_notif = 0
    if role == "student":
        try:
            notifs = await api_notifications(client, user_id)
            if notifs:
                last_notif = max(n["id"] for n in notifs)
        except Exception as e:
            logger.warning("could not fetch notifications for init: %s", e)

    storage.save_session(chat_id, user_id, role, login, name, last_notif=last_notif)

    await update.message.reply_text(
        f"Здравствуйте, {name}!\n\n"
        f"Роль: {'студент' if role == 'student' else 'преподаватель'}.\n"
        "Ниже — расписание на сегодня. Уведомления с сайта дублируются сюда (для студентов).",
        reply_markup=main_keyboard(),
    )
    return ConversationHandler.END


async def cmd_logout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    storage: Storage = context.application.bot_data["storage"]
    storage.delete_session(chat_id)
    await update.message.reply_text(
        "Вы вышли. Нажмите /start для повторного входа.",
        reply_markup=ReplyKeyboardRemove(),
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Вход отменён. Нажмите /start.")
    return ConversationHandler.END


async def on_schedule_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    if update.message.text.strip() != BTN_SCHEDULE:
        return

    chat_id = update.effective_chat.id
    storage: Storage = context.application.bot_data["storage"]
    client: httpx.AsyncClient = context.application.bot_data["http"]
    sess = storage.get_session(chat_id)
    if not sess:
        await update.message.reply_text("Сначала выполните вход: /start")
        return

    dow = date.today().weekday()  # 0=пн … 6=вс
    day_name = DAYS_LONG[dow]
    ds = DAYS_SHORT[dow]
    title = f"Расписание на {day_name} ({ds}), {date.today().strftime('%d.%m.%Y')}"

    try:
        if sess["role"] == "student":
            items = await api_schedule_student(client, sess["user_id"], dow)
        else:
            items = await api_schedule_teacher(client, sess["user_id"], dow)
        text = format_schedule_lines(items, title)
    except Exception as e:
        logger.exception("schedule error")
        text = f"Ошибка загрузки расписания: {e}"

    await update.message.reply_text(text)


async def job_notifications(context: ContextTypes.DEFAULT_TYPE) -> None:
    storage: Storage = context.application.bot_data["storage"]
    client: httpx.AsyncClient = context.application.bot_data["http"]
    bot = context.application.bot

    for row in storage.all_student_sessions():
        chat_id = row["chat_id"]
        uid = row["user_id"]
        last_id = row["last_notif_id"]
        try:
            notifs = await api_notifications(client, uid)
        except Exception as e:
            logger.debug("notifications poll %s: %s", uid, e)
            continue

        new_ones = [n for n in notifs if n["id"] > last_id]
        new_ones.sort(key=lambda x: x["id"])
        max_id = last_id
        for n in new_ones:
            msg = n.get("message") or "Уведомление"
            dt = n.get("created_at", "")
            try:
                await bot.send_message(chat_id, f"🔔 {msg}\n\n{dt}")
            except Exception as e:
                logger.warning("send notif to %s: %s", chat_id, e)
            max_id = max(max_id, n["id"])
        if max_id > last_id:
            storage.update_last_notif_if_greater(chat_id, max_id)


async def job_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """За ~10 минут до начала пары у студента — одно сообщение на пару."""
    storage: Storage = context.application.bot_data["storage"]
    client: httpx.AsyncClient = context.application.bot_data["http"]
    bot = context.application.bot

    today = date.today()
    dow = today.weekday()
    now = datetime.now()

    for row in storage.all_student_sessions():
        chat_id = row["chat_id"]
        uid = row["user_id"]
        try:
            items = await api_schedule_student(client, uid, dow)
        except Exception:
            continue

        for it in items:
            d = it.get("date")
            if not d:
                continue
            if d[:10] != today.isoformat():
                continue
            tstr = it.get("time") or "00:00:00"
            if len(tstr) == 5:
                tstr = tstr + ":00"
            try:
                lesson_dt = datetime.fromisoformat(f"{today.isoformat()}T{tstr}")
            except ValueError:
                continue

            delta = (lesson_dt - now).total_seconds()
            # 9–11 минут до начала (под интервал опроса ~60 с)
            if not (540 <= delta <= 660):
                continue

            key = f"{uid}_{it.get('id')}_{d}"
            if key in _reminder_sent:
                continue
            _reminder_sent.add(key)

            subj = it.get("subject") or "?"
            room = it.get("classroom") or "—"
            tshow = (it.get("time") or "")[:5]
            try:
                await bot.send_message(
                    chat_id,
                    f"⏰ Через ~10 минут пара: {subj} в {tshow}, ауд. {room}.",
                )
            except Exception as e:
                logger.warning("reminder to %s: %s", chat_id, e)


async def post_init(application: Application) -> None:
    application.bot_data["storage"] = Storage()
    application.bot_data["http"] = httpx.AsyncClient(timeout=30.0)
    jq = application.job_queue
    if jq:
        jq.run_repeating(job_notifications, interval=30, first=10, name="notifications")
        jq.run_repeating(job_reminders, interval=60, first=15, name="reminders")
        logger.info("Фоновые задачи: уведомления каждые 30 с, напоминания каждые 60 с")
    else:
        logger.warning(
            "JobQueue недоступен. Установите: pip install \"python-telegram-bot[job-queue]\" "
            "— напоминания и дублирование уведомлений не будут работать."
        )
    logger.info("StudyHub TG bot started, API_BASE_URL=%s (логин: POST %s/api/login)", API_BASE_URL, API_BASE_URL)


async def post_shutdown(application: Application) -> None:
    http: Optional[httpx.AsyncClient] = application.bot_data.get("http")
    if http:
        await http.aclose()
    logger.info("Bot shutdown.")


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit(
            "Задайте TELEGRAM_BOT_TOKEN в переменных окружения или в .env (файл с токеном не коммитьте в git)."
        )

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            WAIT_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_login)],
            WAIT_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("logout", cmd_logout))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_schedule_button))

    logger.info("Polling… Остановка: Ctrl+C")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
