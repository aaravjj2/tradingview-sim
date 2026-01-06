# Supergraph Pro - Full Stack Trading Dashboard

Professional-grade options trading dashboard built with React + FastAPI.

## Stack
- **Frontend**: React + TypeScript + Vite + Tailwind CSS + Lightweight Charts
- **Backend**: FastAPI + SQLite + Alpaca API

## Quick Start

### Backend
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Project Structure
```
supergraph-pro/
├── api/                 # FastAPI Backend
│   ├── main.py
│   ├── routers/
│   ├── services/
│   └── models/
└── frontend/            # React Frontend
    └── src/
        ├── components/
        ├── hooks/
        └── pages/
```
