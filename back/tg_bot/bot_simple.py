"""
Простой бот для просмотра расписания StudyHub.
Запуск: python -m tg_bot.bot_simple
"""
import logging
import os
from datetime import date
from pathlib import Path

import httpx
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Загружаем .env из папки back
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Настройки
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("Задайте TELEGRAM_BOT_TOKEN в back/.env")

# Состояния диалога
WAIT_LOGIN, WAIT_PASSWORD = range(2)

# Хранилище сессий в памяти (для простоты)
# В продакшене используйте базу данных
sessions: dict[int, dict] = {}

# Кнопки
BTN_SCHEDULE = "📅 Расписание на сегодня"
BTN_LOGOUT = "🚪 Выйти"


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[BTN_SCHEDULE], [BTN_LOGOUT]],
        resize_keyboard=True,
        one_time_keyboard=False
    )


async def api_request(endpoint: str, method: str = "GET", json_data: dict = None) -> dict:
    """Простой клиент для API."""
    url = f"{API_BASE_URL}{endpoint}"
    async with httpx.AsyncClient(timeout=30) as client:
        if method == "POST":
            resp = await client.post(url, json=json_data)
        else:
            resp = await client.get(url)
        
        if resp.status_code != 200:
            raise Exception(f"API error {resp.status_code}: {resp.text[:200]}")
        return resp.json()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало диалога /start"""
    chat_id = update.effective_chat.id
    
    # Если уже авторизован
    if chat_id in sessions:
        user = sessions[chat_id]
        await update.message.reply_text(
            f"👋 Вы уже вошли как **{user['name']}** ({user['role']}).\n\n"
            "Нажмите кнопку ниже для просмотра расписания.",
            reply_markup=main_keyboard(),
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🔐 **Вход в StudyHub**\n\n"
        "Введите ваш **логин** от сайта:",
        parse_mode="Markdown"
    )
    return WAIT_LOGIN


async def receive_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение логина"""
    login = update.message.text.strip()
    if not login:
        await update.message.reply_text("❌ Логин не может быть пустым. Попробуйте ещё раз:")
        return WAIT_LOGIN
    
    context.user_data["login"] = login
    await update.message.reply_text("🔑 Введите **пароль**:")
    return WAIT_PASSWORD


async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение пароля и авторизация"""
    login = context.user_data.get("login")
    password = update.message.text.strip()
    chat_id = update.effective_chat.id
    
    try:
        # Авторизация через API
        data = await api_request(
            "/api/login",
            method="POST",
            json_data={"login": login, "password": password}
        )
        
        # Сохраняем сессию
        sessions[chat_id] = {
            "user_id": data["id"],
            "login": login,
            "name": data["name"],
            "role": data["role"]  # 'student' или 'prepod'
        }
        
        await update.message.reply_text(
            f"✅ **Успешный вход!**\n\n"
            f"👤 {data['name']}\n"
            f"🎭 Роль: {'студент' if data['role'] == 'student' else 'преподаватель'}\n\n"
            "Нажмите кнопку ниже для просмотра расписания на сегодня.",
            reply_markup=main_keyboard(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.warning(f"Login failed for {login}: {e}")
        await update.message.reply_text(
            f"❌ **Ошибка входа**\n\n"
            f"{str(e)[:300]}\n\n"
            "Проверьте логин/пароль или запустите бэкенд:\n"
            "```\nuvicorn main:app --host 127.0.0.1 --port 8000\n```",
            parse_mode="Markdown"
        )
    
    return ConversationHandler.END


async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показ расписания на сегодня"""
    chat_id = update.effective_chat.id
    user = sessions.get(chat_id)
    
    if not user:
        await update.message.reply_text(
            "⚠️ Сначала выполните вход: `/start`",
            parse_mode="Markdown"
        )
        return
    
    today = date.today()
    day_of_week = today.weekday()  # 0=пн, 6=вс
    day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    
    try:
        # Запрос расписания в зависимости от роли
        if user["role"] == "student":
            endpoint = f"/api/schedule/student/{user['user_id']}"
        else:
            endpoint = f"/api/schedule/teacher/{user['user_id']}"
        
        schedule = await api_request(f"{endpoint}?day_of_week={day_of_week}")
        
        # Формируем сообщение
        if not schedule:
            text = f"📅 **Расписание на {day_names[day_of_week]}, {today.strftime('%d.%m.%Y')}**\n\n"
            text += "✨ Пар на сегодня нет!"
        else:
            text = f"📅 **Расписание на {day_names[day_of_week]}, {today.strftime('%d.%m.%Y')}**\n\n"
            for item in sorted(schedule, key=lambda x: x.get("time", "")):
                time = item.get("time", "??")[:5]
                subject = item.get("subject", "Неизвестно")
                classroom = item.get("classroom", "—")
                text += f"⏰ {time} — {subject}\n   📍 Ауд. {classroom}\n\n"
        
        await update.message.reply_text(text, parse_mode="Markdown")
        
    except Exception as e:
        logger.exception("Schedule error")
        await update.message.reply_text(
            f"❌ Не удалось загрузить расписание:\n{str(e)[:200]}"
        )


async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выход из аккаунта"""
    chat_id = update.effective_chat.id
    if chat_id in sessions:
        del sessions[chat_id]
        await update.message.reply_text(
            "👋 Вы вышли из аккаунта.\nДля входа снова используйте `/start`",
            reply_markup=None
        )
    else:
        await update.message.reply_text("Вы уже не авторизованы.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена входа"""
    await update.message.reply_text("✋ Вход отменён. Используйте `/start` для начала.")
    return ConversationHandler.END


def main() -> None:
    """Запуск бота"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Диалог авторизации
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAIT_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_login)],
            WAIT_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_SCHEDULE}$"), show_schedule))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_LOGOUT}$"), logout))
    app.add_handler(CommandHandler("logout", logout))
    
    logger.info(f"🤖 Бот запущен! API: {API_BASE_URL}")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()