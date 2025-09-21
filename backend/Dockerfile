# --- Frontend build stage ---
FROM node:20-slim AS webbuild
WORKDIR /src
COPY testcase-generator/frontend/package*.json ./
RUN npm ci
COPY testcase-generator/frontend/ ./
RUN npm run build   # outputs to /src/dist

# --- Backend runtime ---
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# backend deps
COPY testcase-generator/backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# copy entire repo (for apps/, scripts/, etc.)
COPY . /app

# copy built frontend into /app/web (served by FastAPI)
COPY --from=webbuild /src/dist /app/web

EXPOSE 8000
CMD ["uvicorn","testcase-generator.backend.main:app","--host","0.0.0.0","--port","8000"]