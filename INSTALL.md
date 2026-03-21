# StudyHub — установка и запуск

Инструкция для **macOS** и **Windows**.

---

## Требования

- **Python** 3.10–3.12
- **Node.js** 18+ и npm
- **PostgreSQL** 12+

---

## 1. Установка PostgreSQL

### macOS (Homebrew)

```bash
brew install postgresql@15
brew services start postgresql@15
```

Создание базы данных:

```bash
createdb schedule_db
```

### Windows

1. Скачайте установщик: https://www.postgresql.org/download/windows/
2. Установите PostgreSQL, задайте и запомните пароль пользователя `postgres`
3. Добавьте каталог `bin` PostgreSQL в PATH (обычно `C:\Program Files\PostgreSQL\16\bin`)
4. Создайте базу данных:

```cmd
psql -U postgres -c "CREATE DATABASE schedule_db;"
```

Либо создайте базу через **pgAdmin**.

---

## 2. Установка Backend (Python)

### macOS

```bash
cd back

# Создание виртуального окружения
python3 -m venv .venv

# Активация (обязательно перед каждой работой с бэкендом)
source .venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Копирование конфигурации
cp .env.example .env
```

### Windows (PowerShell)

```powershell
cd back

# Создание виртуального окружения
python -m venv .venv

# Активация
.\.venv\Scripts\Activate.ps1

# Установка зависимостей
pip install -r requirements.txt

# Копирование конфигурации
copy .env.example .env
```

### Windows (CMD)

```cmd
cd back
python -m venv .venv
.\.venv\Scripts\activate.bat
pip install -r requirements.txt
copy .env.example .env
```

### Настройка .env

Откройте файл `back/.env` и укажите `DATABASE_URL`:

| Система | Пример |
|--------|--------|
| macOS (Homebrew, без пароля) | `DATABASE_URL=postgresql://localhost:5432/schedule_db` |
| macOS (с паролем) | `DATABASE_URL=postgresql://postgres:ВАШ_ПАРОЛЬ@localhost:5432/schedule_db` |
| Windows | `DATABASE_URL=postgresql://postgres:ВАШ_ПАРОЛЬ@localhost:5432/schedule_db` |

### Заполнение базы тестовыми данными

```bash
# Убедитесь, что виртуальное окружение активировано
python seed.py
```

---

## 3. Установка Frontend (Node.js)

Одинаково для macOS и Windows:

```bash
cd front
npm install
```

---

## 4. Запуск проекта

Нужно запустить **два** процесса: бэкенд и фронтенд.

### macOS

**Терминал 1 — бэкенд:**

```bash
cd back
source .venv/bin/activate
uvicorn main:app --reload
```

**Терминал 2 — фронтенд:**

```bash
cd front
npm run dev
```

### Windows

**Терминал 1 — бэкенд:**

```powershell
cd back
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload
```

**Терминал 2 — фронтенд:**

```cmd
cd front
npm run dev
```

---

## 5. Доступ к приложению

- **Фронтенд (интерфейс):** http://localhost:5173
- **Бэкенд API:** http://127.0.0.1:8000
- **Swagger (документация API):** http://127.0.0.1:8000/docs

Запросы `/api` с фронтенда автоматически проксируются на бэкенд.

---

## 6. Тестовые аккаунты

После выполнения `seed.py`:

| Роль | Логин | Пароль |
|------|-------|--------|
| Студент | student1 … student15 | 123 |
| Преподаватель | prepod1 … prepod6 | 123 |
| Администратор | admin | admin |

После `seed.py`: три группы (ИУ1-22Б, ИУ1-21Б, БМТ2-23Б) по **5 студентов** в каждой; в расписании **несколько пар в день** на группу (Пн–Пт), добавлены предметы вроде английского, БД, электротехники и др.

---

## Возможные проблемы

### macOS: `command not found: python`

Используйте `python3` вместо `python`.

### macOS: `pip: externally-managed-environment`

Не устанавливайте пакеты в системный Python. Всегда активируйте виртуальное окружение (`.venv`) перед `pip install`.

### Windows: ошибка подключения к PostgreSQL

- Убедитесь, что служба PostgreSQL запущена (Службы Windows: `services.msc`)
- Проверьте пароль в `DATABASE_URL`
- Убедитесь, что порт 5432 не занят

### `npm` не найден

Установите Node.js: https://nodejs.org/ (рекомендуется LTS).

### Бэкенд не запускается

1. Проверьте наличие `DATABASE_URL` в `back/.env`
2. Убедитесь, что база `schedule_db` создана
3. Убедитесь, что PostgreSQL запущен
