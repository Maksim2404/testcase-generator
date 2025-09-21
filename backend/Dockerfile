# --- Frontend build stage ---
FROM node:20-slim AS webbuild
WORKDIR /src
COPY ./frontend/package*.json ./
RUN npm ci
COPY ./frontend/ ./
RUN npm run build   # outputs to /src/dist

# --- Backend runtime ---
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY ./backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# copy entire repo
COPY . /app

# serve built frontend from FastAPI
COPY --from=webbuild /src/dist /app/web

EXPOSE 8000
CMD ["uvicorn","backend.main:app","--host","0.0.0.0","--port","8000"]