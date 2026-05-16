install:
	python -m pip install -e .
	cd dashboard && npm install

dev:
	docker compose up --build

migrate:
	alembic upgrade head

seed:
	python seed_data.py

test:
	python -m pytest -q

