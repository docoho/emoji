.PHONY: frontend backend backend-test lint run-bg stop

frontend:
	cd frontend && npm run dev

backend:
	cd backend && ./venv/bin/uvicorn app.main:app --reload

backend-test:
	cd backend && ./venv/bin/python -m pytest

lint:
	cd backend && ./venv/bin/ruff check app tests

run-bg:
	@echo "Starting backend in background..."
	@cd backend && exec nohup ./venv/bin/uvicorn app.main:app --reload > ../backend.log 2>&1 & echo $$! > backend.pid
	@echo "Starting frontend in background..."
	@cd frontend && exec nohup npm run dev > ../frontend.log 2>&1 & echo $$! > frontend.pid
	@echo "Servers started. Logs in backend.log and frontend.log"

stop:
	@if [ -f backend.pid ]; then kill `cat backend.pid` 2>/dev/null || true; rm backend.pid; echo "Backend stopped"; fi
	@if [ -f frontend.pid ]; then kill `cat frontend.pid` 2>/dev/null || true; rm frontend.pid; echo "Frontend stopped"; fi
