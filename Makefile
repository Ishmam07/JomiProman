.PHONY: help up down logs db test backend frontend reset-demo

help:            ## list commands
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/'

up:              ## build and start everything (http://localhost:3100)
	docker compose up --build -d

down:            ## stop everything (data volumes are kept)
	docker compose down

logs:            ## follow backend logs
	docker compose logs -f backend

db:              ## start only MySQL + Redis (for running backend/frontend from the IDE)
	docker compose up -d mysql redis

test:            ## run backend tests (SQLite, no Docker needed)
	cd backend && python -m pytest

backend:         ## run API locally with auto-reload (needs `make db`)
	cd backend && uvicorn app.main:app --reload --port 8101

frontend:        ## run React dev server (http://localhost:5173)
	cd frontend && npm install && npm run dev

reset-demo:      ## wipe and reload the dummy data (uses the default demo registrar key)
	curl -s -X POST "http://localhost:8101/api/seed?reset=true" -H "X-Registrar-Key: $${REGISTRAR_KEY:-demo-registrar}"; echo
