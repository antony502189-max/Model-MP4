.PHONY: up down logs test bootstrap train
up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f api worker

test:
	pytest -q

bootstrap:
	python scripts/bootstrap_dataset.py input.mp4 --out dataset --samples 600

train:
	docker compose --profile train run --rm trainer
