.PHONY: frontend backend backend-test lint

frontend:
	cd frontend && npm run dev

backend:
	cd backend && uvicorn app.main:app --reload

backend-test:
	cd backend && python3 -m pytest

lint:
	cd backend && ruff check app tests
