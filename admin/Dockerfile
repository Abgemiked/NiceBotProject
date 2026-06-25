# nicebot-admin — Multi-Stage Build
# Stage 1: Frontend (React/Vite) bauen
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Backend (FastAPI) + gebaute SPA
FROM python:3.12-slim AS app
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
# Gebaute Frontend-Dateien ins von main.py erwartete Verzeichnis
COPY --from=frontend /fe/dist /app/frontend_dist

EXPOSE 8140
# Kein Host-Port-Mapping in compose — NPM routet intern auf 8140.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8140"]
