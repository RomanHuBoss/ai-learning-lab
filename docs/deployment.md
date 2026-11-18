# Развёртывание

## Демонстрационный режим

На Ubuntu 24.04 с Docker Compose:

```bash
git clone <repository-url> ai-learning-lab
cd ai-learning-lab
cp .env.example .env
docker compose up --build -d
docker compose ps
curl http://127.0.0.1:8000/health/ready
docker compose run --rm api python scripts/migrate.py
docker compose run --rm api python scripts/seed_db.py
```

Стек включает PostgreSQL, Redis, API, worker и Caddy. Caddy доступен на 80 и 443 портах, API для прямой диагностики — на 8000. Перед публичным запуском задайте собственные секреты в `.env` и подключите доменное имя для HTTPS.

## Backup и restore демо-контента

Контент хранится в versioned JSON и попадает в Git. Для локального состояния API можно сохранить копию каталога:

```bash
tar -czf ai-learning-lab-content-$(date +%F).tar.gz data docs
tar -xzf ai-learning-lab-content-YYYY-MM-DD.tar.gz
```

Резервная копия базы и восстановление:

```bash
./scripts/backup.sh
./scripts/restore.sh backups/ailab-YYYYMMDDTHHMMSSZ.sql.gz
```

CI выполняет проверку JSON, content lint, тесты Python, проверку JavaScript, `docker compose config`, сборку образов и smoke test `/health/live` и `/health/ready`.

Зарегистрированные пользователи используют PostgreSQL progress store. Versioned migrations применяются через `scripts/migrate.py`, а CI дважды проверяет идемпотентность, seed demo accounts и backup/restore PostgreSQL. Профили, visibility consent, каталог выпускников, mentor/admin views и CSV-экспорт включены в миграцию `002_profiles_catalog.sql`.

## Публикация на shared-hosting без root-доступа

Если виртуальный хост обслуживается связкой Nginx и Apache, а доступ к Docker есть только у root, frontend можно разместить в каталоге домена, а API запустить от пользователя сайта на loopback-порту. Каталог `infra/apache-api-proxy` содержит PHP-прокси для `/api/*`, который передаёт запросы локальному Uvicorn. Системные health URL можно отдать статическими файлами из `infra/static-health`.

Прокси требует PHP cURL и rewrite для каталога `api`. Процесс API должен запускаться через пользовательский supervisor, systemd user service с включённым linger или detached screen/tmux. Секреты хранятся в отдельном `.env` с правами `0600`.
