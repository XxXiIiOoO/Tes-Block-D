# BlockTest

BlockTest - платформа для автоматизации тестирования блокчейн-приложений в изолированной Docker-среде.

Проект сделан как fullstack-приложение для дипломной работы: пользователь создает проекты, добавляет тесты, запускает их в контейнерах, смотрит логи, диагностику, аналитику и выгружает отчеты по запускам.

## Быстрый Старт

Требования:

- Docker Desktop / Docker Engine
- Docker Compose
- доступ к Docker socket для worker-сервиса

Запуск всего стенда:

```bash
docker compose up --build
```

После запуска:

- frontend: `http://localhost:5173`
- backend API: `http://localhost:8000`
- Swagger / OpenAPI: `http://localhost:8000/docs`
- локальная Hardhat-нода: `http://localhost:8545`

Backend при старте сам применяет Alembic-миграции и создает bootstrap-аккаунты из `.env`.

## Что Умеет Приложение

- регистрация, вход, refresh-токены, logout;
- подтверждение email и восстановление пароля;
- роли `admin`, `worker`, `viewer`;
- проекты и тестовые сценарии;
- запуск тестов в изолированных Docker-контейнерах;
- импорт публичного dApp из GitHub;
- подключение к RPC-ноду через URL и Chain ID;
- очередь задач через Redis + TaskIQ;
- live-логи через SSE;
- отмена, повторный запуск и история запусков;
- диагностика ошибок, метрики, рекомендации;
- JSON/HTML/PDF-отчеты по запуску;
- dashboard и расширенная аналитика;
- админ-панель пользователей и аудит-событий;
- PWA-ready frontend для desktop/mobile.

## Основной Сценарий Работы

1. Войти под одним из аккаунтов.
2. Открыть раздел **Проекты**.
3. Создать проект.
4. Открыть проект и создать тест.
5. Выбрать один из режимов теста:
   - `Скрипт Python`;
   - `Docker + команда`;
   - `GitHub dApp`.
6. Открыть созданный тест и нажать **Запустить тест**.
7. Открыть запуск, смотреть статус, логи и диагностику.
8. При необходимости скачать:
   - JSON export;
   - HTML report;
   - PDF report.

## Режимы Тестов

### 1. Скрипт Python

Подходит для быстрых smoke-тестов и проверок без отдельного репозитория.

Поля:

- название;
- описание;
- сценарий;
- Python-скрипт;
- Docker image, обычно `python:3.12-slim`.

Worker создает контейнер, кладет скрипт в `/workspace/script.py` и запускает:

```bash
python3 /workspace/script.py
```

### 2. Docker + Команда

Подходит, если тест уже упакован в Docker image.

Поля:

- Docker image;
- shell-команда.

Пример:

```bash
python -c "print('Blockchain test passed')"
```

Image должен быть разрешен через `DOCKER_ALLOWED_IMAGES`.

### 3. GitHub dApp

Это основной пользовательский режим для импорта dApp-приложения.

Поля в форме:

- GitHub repository: `https://github.com/org/repo`
- branch/tag: например `main`
- папка проекта: например `packages/contracts`
- Docker image: обычно `node:20-bookworm-slim`
- RPC URL: например `http://hardhat:8545`
- Chain ID: например `31337`
- install command: например `npm ci`
- test command: например `npx hardhat test`

Как это работает:

1. Worker скачивает публичный ZIP-архив с `github.com`.
2. Проверяет, что это именно GitHub-репозиторий.
3. Ограничивает размер архива 100 MB.
4. Распаковывает выбранную branch/tag.
5. Если задана подпапка, берет только ее.
6. Копирует исходники в `/workspace` контейнера.
7. Прокидывает переменные:

```env
BLOCKTEST_RPC_URL=<rpc_url>
BLOCKTEST_CHAIN_ID=<chain_id>
BLOCKTEST_REPOSITORY_URL=<repository_url>
```

8. Выполняет install command.
9. Выполняет test command.
10. Сохраняет stdout/stderr, exit code, статус, метрики и диагностику.

Ограничения текущей реализации:

- поддерживаются только публичные `github.com` репозитории;
- приватные GitHub-репозитории пока не поддержаны;
- загрузка идет через GitHub archive ZIP, без `git clone`;
- лимит архива: 100 MB;
- если `npm ci` или другая setup-команда требует интернет внутри контейнера, контейнер должен иметь сетевой доступ.

## Подключение Ноды

В локальном `docker-compose.yml` есть сервис `hardhat`, который поднимает RPC-ноду на порту `8545`.

Для тестов внутри Docker-сети используйте:

```text
http://hardhat:8545
```

Для доступа с хоста:

```text
http://localhost:8545
```

Текущий `.env` уже настроен на compose-сеть:

```env
DOCKER_NETWORK_DISABLED=false
DOCKER_COMPOSE_NETWORK=blocktest_default
```

Это позволяет контейнерам тестов обращаться к сервисам внутри Docker Compose сети.

## Отчеты По Запускам

Для каждого запуска доступны:

- UI-страница с логами и диагностикой;
- JSON export;
- HTML report;
- PDF report.

API:

```text
GET /runs/{run_id}/export
GET /runs/{run_id}/report.html
GET /runs/{run_id}/report.pdf
```

Отчет содержит:

- ID запуска;
- проект и тест;
- статус;
- время создания, старта, завершения;
- длительность и ожидание очереди;
- exit code;
- категорию сбоя;
- метрики логов;
- диагностические сигналы;
- рекомендации;
- quality gate;
- сохраненные логи.

PDF формируется через `reportlab`. В Dockerfile добавлен `fonts-dejavu-core`, чтобы PDF нормально работал с кириллицей.

## Архитектура

```text
frontend  ->  backend API  ->  PostgreSQL
                       |
                       v
                    Redis queue
                       |
                       v
                    worker
                       |
                       v
              temporary Docker container
```

Компоненты:

- `frontend` - React/Vite UI;
- `backend` - FastAPI API, auth, CRUD, аналитика, отчеты;
- `postgres` - пользователи, проекты, тесты, запуски, логи;
- `redis` - очередь TaskIQ;
- `worker` - выполнение тестов в Docker;
- `hardhat` - локальная RPC-нода для live blockchain сценариев.

## Структура Проекта

```text
BlockTest/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── workers/
│   ├── alembic/
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── auth/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── pages/
│   │   └── preferences/
│   ├── Dockerfile
│   └── package.json
├── presets/
│   ├── evm/
│   └── hardhat/
├── docs/
├── docker-compose.yml
├── .env
├── .env.example
└── README.md
```

## Модель Данных

Основные таблицы:

- `users` - пользователи, роли, email verification, профиль;
- `refresh_tokens` - хешированные refresh-токены;
- `projects` - проекты пользователей;
- `tests` - тесты проекта;
- `runs` - история запусков;
- `run_logs` - stdout/stderr/system логи;
- `test_chat_messages` - обсуждение тестов;
- `audit_events` - события админ-панели.

Тесты поддерживают поля:

- `docker_image`;
- `command`;
- `script`;
- `repository_url`;
- `repository_branch`;
- `repository_subdir`;
- `setup_command`;
- `rpc_url`;
- `chain_id`;
- automation/quality gate настройки.

## API

### Health

```text
GET /health
```

### Auth

```text
POST /auth/register
POST /auth/verify-email
POST /auth/resend-verification
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /auth/me
POST /auth/forgot-password
POST /auth/reset-password
```

### Projects

```text
GET    /projects
POST   /projects
GET    /projects/{project_id}
PUT    /projects/{project_id}
DELETE /projects/{project_id}
GET    /projects?search=wallet
```

### Tests

```text
GET    /projects/{project_id}/tests
POST   /projects/{project_id}/tests
GET    /tests/{test_id}
PUT    /tests/{test_id}
DELETE /tests/{test_id}
GET    /tests/{test_id}/chat
POST   /tests/{test_id}/chat
```

### Runs

```text
POST /tests/{test_id}/run
POST /runs/{run_id}/rerun
POST /runs/{run_id}/cancel
GET  /runs
GET  /tests/{test_id}/runs
GET  /runs/{run_id}
GET  /runs/{run_id}/logs
GET  /runs/{run_id}/logs/stream
GET  /runs/{run_id}/insights
GET  /runs/{run_id}/export
GET  /runs/{run_id}/report.html
GET  /runs/{run_id}/report.pdf
```

Фильтры запусков:

```text
GET /runs?status=finished
GET /runs?sort_by=created_at&order=desc
GET /runs?sort_by=started_at&order=asc
GET /runs?date_from=2026-05-01&date_to=2026-05-06
```

### Stats

```text
GET /stats/overview
```

### Automation

```text
GET   /tests/{test_id}/automation
PATCH /tests/{test_id}/automation
POST  /tests/{test_id}/automation/webhook-token
POST  /automation/webhook/{test_id}
POST  /automation/schedule/tick
```

### Admin

```text
GET   /admin/users
PATCH /admin/users/{user_id}
GET   /admin/audit-events
```

## Frontend Routes

```text
/login
/register
/verify-email
/forgot-password
/reset-password
/
/analytics
/admin
/projects
/projects/:projectId
/tests/:testId
/runs
/runs/:runId
/profile
/settings
```

## Переменные Окружения

Основные переменные из текущего `.env`:

```env
POSTGRES_USER=blocktest
POSTGRES_PASSWORD=blocktest
POSTGRES_DB=blocktest
DATABASE_URL=postgresql+psycopg://blocktest:blocktest@postgres:5432/blocktest

REDIS_URL=redis://redis:6379/0
BLOCKTEST_APP_NAME=BlockTest API
BLOCKTEST_DEBUG=false

BLOCKTEST_SEED_PRESETS=true
DEFAULT_DOCKER_IMAGE=python:3.12-slim
DOCKER_RUN_TIMEOUT_SECONDS=60
DOCKER_MEMORY_LIMIT=256m
DOCKER_NETWORK_DISABLED=false
DOCKER_COMPOSE_NETWORK=blocktest_default

VITE_API_URL=http://localhost:8000
```

Для GitHub dApp режима нужен image `node:20-bookworm-slim`. Если переменная `DOCKER_ALLOWED_IMAGES` задана явно, добавьте:

```env
DOCKER_ALLOWED_IMAGES=python:3.12-slim,node:20-bookworm-slim,blocktest-presets:latest
```

## Предустановленные EVM-Тесты

Так как в текущем `.env` указано:

```env
BLOCKTEST_SEED_PRESETS=true
```

backend создает проект `BlockTest EVM Presets` для admin-пользователя.

В preset-набор входят проверки:

- wallet checksum;
- HD mnemonic derivation;
- message signing/recovery;
- EIP-712 typed data;
- legacy transaction signing;
- EIP-1559 transaction signing;
- ERC20 ABI encode/decode;
- ERC20 Transfer event decoding;
- Merkle proof;
- batch signature benchmark;
- revert reason decoding;
- tampered signature rejection;
- access list transaction signing;
- JSON telemetry output;
- ABI throughput benchmark.

Preset image собирается локально из `presets/evm`, если его еще нет на Docker host.

## Изоляция Запусков

Каждый запуск выполняется во временном контейнере.

Контроль изоляции:

- allowlist Docker images через `DOCKER_ALLOWED_IMAGES`;
- лимит памяти через `DOCKER_MEMORY_LIMIT`;
- лимит CPU через `DOCKER_NANO_CPUS`;
- лимит процессов через `DOCKER_PIDS_LIMIT`;
- timeout через `DOCKER_RUN_TIMEOUT_SECONDS`;
- non-root user через `DOCKER_RUN_USER`;
- `cap_drop=["ALL"]`;
- `no-new-privileges`;
- read-only root filesystem;
- writable tmpfs для `/tmp` и `/workspace`;
- отключение сети или подключение к pinned compose network;
- удаление контейнера после завершения.

Важно: Docker isolation не равен полноценной VM-песочнице. Worker имеет доступ к Docker socket, поэтому host worker-а считается доверенной инфраструктурой.

## Безопасность

Реализовано:

- password hashing;
- JWT access token;
- persisted refresh-token rotation;
- logout с отзывом refresh token;
- email verification;
- password reset;
- rate limiting и lockout при неудачных логинах;
- роли `admin`, `worker`, `viewer`;
- SQLAlchemy expressions вместо ручной конкатенации SQL;
- validation через Pydantic;
- security headers;
- ограничение Docker images;
- ограничение GitHub imports публичным `github.com` и лимитом 100 MB.

Для production-like режима:

```env
BLOCKTEST_ENV=production
JWT_SECRET_KEY=<long-random-secret-at-least-32-chars>
BACKEND_CORS_ORIGINS=https://your-frontend.example
EXPOSE_VERIFICATION_TOKEN_IN_RESPONSE=false
EMAIL_DELIVERY_MODE=smtp
DOCKER_ALLOWED_IMAGES=python:3.12-slim,node:20-bookworm-slim,blocktest-presets:latest
DOCKER_NETWORK_DISABLED=true
```

## Локальная Разработка Backend

Запустить инфраструктуру:

```bash
docker compose up postgres redis hardhat -d
```

Создать окружение и поставить зависимости:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt
```

Применить миграции вручную при необходимости:

```bash
cd backend
alembic upgrade head
```

Запустить API:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Запустить worker:

```bash
cd backend
python -m taskiq worker app.workers.broker:broker app.workers.jobs
```

## Локальная Разработка Frontend

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Сборка:

```bash
cd frontend
npm run build
```

E2E:

```bash
cd frontend
npx playwright install chromium
npm run test:e2e
```

## Тесты

Backend:

```bash
cd backend
pytest
```

Проверка безопасности:

```bash
cd backend
pytest tests/test_security_hardening.py
```

Frontend:

```bash
cd frontend
npx tsc -b --noEmit
npm run build
```

## Run Flow

1. Пользователь нажимает **Запустить тест**.
2. Backend проверяет права.
3. Создает `runs` запись со статусом `queued`.
4. Отправляет `run_test_job(run_id)` в Redis через TaskIQ.
5. Worker берет задачу.
6. Run переходит в `running`.
7. Worker готовит Docker-контейнер.
8. Для GitHub dApp worker скачивает репозиторий и копирует его в `/workspace`.
9. Контейнер выполняет скрипт или shell-команды.
10. Worker сохраняет stdout/stderr, exit code, timestamps, статус и summary.
11. Контейнер удаляется.
12. UI показывает логи, диагностику, аналитику и отчеты.

## Диагностика Ошибок

BlockTest анализирует запуск и показывает:

- длительность выполнения;
- ожидание очереди;
- количество логов;
- stdout/stderr/system классификацию;
- warning/error counters;
- latest error;
- failure category;
- diagnostic signals;
- recommendations;
- quality gate result.

Категории сбоев включают:

- timeout;
- Docker runtime problem;
- network problem;
- missing dependency;
- smart contract revert;
- assertion failed;
- unhandled exception;
- cancelled run;
- generic failure.

## Troubleshooting

### Backend не стартует из-за старой БД

Обычно достаточно:

```bash
docker compose up --build
```

Если база сильно старая, можно удалить volume:

```bash
docker compose down -v
docker compose up --build
```

### GitHub dApp не скачивается

Проверьте:

- репозиторий публичный;
- URL вида `https://github.com/owner/repo`;
- branch/tag существует;
- archive меньше 100 MB.

### `npm ci` падает внутри контейнера

Проверьте:

- контейнер имеет сетевой доступ;
- image содержит Node/npm;
- `package-lock.json` есть, если используется `npm ci`;
- выбран правильный `repository_subdir`.

### Тест не видит Hardhat

Для контейнера используйте:

```text
http://hardhat:8545
```

И проверьте:

```env
DOCKER_NETWORK_DISABLED=false
DOCKER_COMPOSE_NETWORK=blocktest_default
```

### Docker Compose ругается на `$` в `.env`

Если значение содержит `$`, Docker Compose может интерпретировать его как переменную. Экранируйте как `$$` или используйте секрет без `$` для локального стенда.

## Что Можно Улучшить Позже

- приватные GitHub-репозитории через token/connector;
- загрузка ZIP-архива через UI;
- сохранение артефактов тестов;
- pagination для истории запусков;
- расширенные quality gates;
- групповые прогоны;
- интеграция с CI/CD;
- отдельный sandbox-host для worker;
- VM-level isolation.

## Материалы Для Диплома

Текстовые заготовки:

```text
docs/diploma-sections.md
```

В корне проекта также лежат схемы, диаграммы и `.docx` приложения для пояснительной записки.
