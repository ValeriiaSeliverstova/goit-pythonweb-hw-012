# goit-pythonweb-hw-012

# 1. Start Postgres

postgres: localhost:5432 (admin / 12345)

# 2. Install deps (Poetry)

poetry install --no-root

# 3. Run migrations

poetry run alembic revision --autogenerate -m "create users & contacts"
poetry run alembic upgrade head

# 4. Run app

poetry run python main.py

# Endpoints (summary)

GET /api/contacts — list (pagination: skip, limit)
GET /api/contacts/{contact_id} — get by id
POST /api/contacts — create
PUT /api/contacts/{contact_id} — update
DELETE /api/contacts/{contact_id} — delete
GET /api/contacts/search?first_name=&last_name=&email=&skip=&limit= — search
GET /api/contacts/upcoming_birthdays?days=7 — birthdays next N days

# Pytest check

poetry run pytest --cov=src --cov-report=term-missing
