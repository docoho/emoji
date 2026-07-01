.PHONY: frontend backend backend-test backend-migrate lint run-bg stop status

frontend:
	cd frontend && npm run dev

backend:
	cd backend && ./venv/bin/uvicorn app.main:app --reload --host 0.0.0.0

backend-test:
	cd backend && ./venv/bin/python -m pytest

backend-migrate:
	cd backend && ./venv/bin/alembic upgrade head

lint:
	cd backend && ./venv/bin/ruff check app tests

run-bg:
	@$(MAKE) stop
	@echo "Starting backend in background..."
	@cd backend && exec nohup ./venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 > ../backend.log 2>&1 & echo $$! > backend.pid
	@echo "Starting frontend in background..."
	@cd frontend && exec nohup npm run dev > ../frontend.log 2>&1 & echo $$! > frontend.pid
	@echo "Servers started. Logs in backend.log and frontend.log"

stop:
	@if [ -f backend.pid ]; then kill `cat backend.pid` 2>/dev/null || true; rm backend.pid; echo "Backend pid stopped"; fi
	@if [ -f frontend.pid ]; then kill `cat frontend.pid` 2>/dev/null || true; rm frontend.pid; echo "Frontend pid stopped"; fi
	@backend_pids=$$(lsof -tiTCP:8000 -sTCP:LISTEN 2>/dev/null || true); \
	if [ -n "$$backend_pids" ]; then \
		echo "Stopping backend listeners on :8000: $$backend_pids"; \
		kill $$backend_pids 2>/dev/null || true; \
	fi
	@frontend_pids=$$(lsof -tiTCP:5173 -sTCP:LISTEN 2>/dev/null || true); \
	if [ -n "$$frontend_pids" ]; then \
		echo "Stopping frontend listeners on :5173: $$frontend_pids"; \
		kill $$frontend_pids 2>/dev/null || true; \
	fi

status:
	@echo "Backend (:8000)"
	@lsof -nP -iTCP:8000 -sTCP:LISTEN 2>/dev/null || true
	@echo "Frontend (:5173)"
	@lsof -nP -iTCP:5173 -sTCP:LISTEN 2>/dev/null || true
