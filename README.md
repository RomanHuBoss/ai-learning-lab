# AI Learning Lab

Русскоязычный интерактивный самоучитель по машинному обучению, нейронным сетям и большим языковым моделям. Цель курса — дать выпускнику свободную ориентацию в современном ИИ и способность применять ML/AI в повседневной практике и бизнесе. В этом репозитории собран рабочий вертикальный срез мастер-промпта. Он включает dashboard ученика, prerequisite-карту, интерактивную лабораторию градиентного спуска, тренажёр задач, словарь терминов, проекты, настройки доступности и минимальный FastAPI-контур.

## Быстрый запуск

### Docker Compose

```bash
docker compose up --build -d
```

Откройте [http://localhost](http://localhost) через Caddy или прямой API-адрес [http://localhost:8000](http://localhost:8000). Проверки готовности:

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

После запуска можно создать демонстрационные аккаунты:

```bash
docker compose run --rm api python scripts/seed_db.py
```

Демо-пользователи: `demo@ai-learning.local / DemoPass123!`, `mentor@ai-learning.local / MentorPass123!`, `admin@ai-learning.local / AdminPass123!`.

Compose поднимает PostgreSQL, Redis, API, worker и Caddy. База и Redis имеют health checks, API ждёт их готовности, а Caddy проксирует HTTP-запросы. Для production замените значения в `.env`, особенно `SECRET_KEY` и пароль PostgreSQL.

### Локальный запуск

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# Linux/macOS
# source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

Статический демо-режим можно открыть напрямую через `app/index.html`, однако API-эндпоинты доступны при запуске FastAPI.

## Проверки

```bash
python scripts/check_terms.py
pytest -q
```

Проверка контента ищет отсутствующие поля словаря, дубликаты терминов, необъяснимые аббревиатуры и циклы prerequisite-графа. Тесты проверяют health endpoints, покрытие уроков и сохранение прогресса.

## Что реализовано в вертикальном срезе

- навигация по dashboard, карте курса, лаборатории, задачам, проектам, словарю, достижениям и настройкам;
- тёмная и светлая тема, клавиатурный focus, reduced motion, текстовое описание лаборатории и адаптивная верстка от 320 px;
- лаборатория градиентного спуска с запуском, паузой, пошаговым режимом, сбросом, тремя параметрами и прогнозом результата;
- после ошибки в задаче показываются причина, misconception и ссылка на урок;
- прогресс темы и текущий экран сохраняются локально, прогресс можно экспортировать в JSON;
- versioned curriculum, терминологический словарь, банк из 250 заданий и 6 проектов;
- расширенная карта `data/full_program.json` на 25 модулей и 100 уроков, включая GNN, RNN/LSTM/GRU, веса, инференс, KV-кэш, квантизацию, оборудование и стоимость;
- каталог `data/labs.json` из 26 вычисляемых лабораторий по классическому ML, нейросетям, графам, LLM и производственной практике;
- FastAPI endpoints для контента, health checks, auth, групп, профилей, каталога выпускников, панелей наставника и администратора, прогресса, sandbox, RAG-поиска с chunking/reranking/цитатами и оценки groundedness, а также AI-тьютора;
- PostgreSQL persistence through SQLAlchemy, registration/login with Argon2 and JWT, role-aware cohorts, profiles with visibility consent, alumni catalog filters, mentor dashboard, admin role management/export, enrollments, versioned exams, deterministic attempts, audit logs and private `/api/me/progress`;
- Docker Compose deployment для демонстрационного режима.
- PostgreSQL, Redis, отдельный worker, Caddy reverse proxy, health checks и GitHub Actions в `.github/workflows/ci.yml`.

## Структура

```text
app/                  статический frontend
api/main.py           FastAPI API и раздача frontend
api/models.py         SQLAlchemy сущности пользователей, групп и прогресса
api/auth.py           Argon2/JWT authentication и role guards
data/                 versioned контент
data/full_program.json расширенная карта 25 модулей и 100 уроков
data/lesson_content.json обязательные блоки 49 уроков вертикального среза
data/labs.json        каталог из 26 вычисляемых лабораторий
infra/Caddyfile       reverse proxy и security headers
scripts/backup.sh     резервная копия PostgreSQL
scripts/restore.sh    восстановление PostgreSQL
.github/workflows     CI, Compose smoke test и сборка образов
docs/                 Фаза 0 и матрица покрытия
scripts/              content lint
migrations/           versioned PostgreSQL schema migrations
tests/                API smoke tests
Dockerfile            production-like контейнер
docker-compose.yml    one-command запуск
```

## Ограничения текущего среза

Гостевой режим разрешает только чтение демо-прогресса `/api/progress/demo`. Запись и доступ к пользовательскому прогрессу требуют Bearer-токен и совпадение владельца, а зарегистрированные пользователи сохраняют прогресс через PostgreSQL `/api/me/progress`. AI-тьютор работает через provider abstraction с demo provider без внешнего ключа. Полный VPS smoke test требует окружения с Docker. Архитектурная граница и API-контракт описаны в [docs/phase-0.md](docs/phase-0.md).

## Демо-путь

1. Откройте «Обзор» и нажмите «Продолжить обучение».
2. В лаборатории измените скорость обучения, нажмите «Запустить» и попробуйте пошаговый режим.
3. Откройте «Тренажёр задач», выберите ответ и запросите объяснение ошибки.
4. В «Словаре» найдите «поиск с дополнением контекста» и откройте связанный урок.
5. Переключите тему и экспортируйте прогресс в JSON.
