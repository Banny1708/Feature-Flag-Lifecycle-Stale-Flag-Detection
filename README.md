# Feature Flag Lifecycle and Stale Flag Detection

A modern dashboard and management platform to track feature flags across repositories, detect stale or obsolete flags, analyze code dependencies, and automate safe removal operations.

## Features

- **Dashboard & Metrics**: Real-time overview of active, stale, deprecated, and rollout flags with health scoring.
- **Feature Flag Inventory**: Full lifecycle management with search, filtering by status, environment, and tags.
- **Stale Flag Detection**: Automated heuristics and rules to identify flags past their lifecycle, unused flags, and 100% rollout candidates.
- **Code Analysis**: Deep inspection of flag usage across repositories, files, and AST references.
- **Safe Removal Workflows**: Automated PR generation, verification tests, and rollback safety checks for flag cleanup.
- **Multi-Repository Support**: Connect and scan multiple code repositories seamlessly.
- **Audit Reports & Compliance**: Detailed reports on technical debt reduction and flag retirement history.

## Tech Stack

- **Framework**: React 18 + TypeScript + Vite
- **Styling**: Tailwind CSS + Lucide Icons
- **Routing**: React Router DOM v6
- **Architecture**: Modular services, custom hooks, and strongly typed domain models

## Getting Started

### Prerequisites

- Node.js (v18 or higher recommended)
- npm or yarn

### Installation

```bash
# Clone the repository
git clone https://github.com/Banny1708/Feature-Flag-Lifecycle-Stale-Flag-Detection.git

# Navigate to the directory
cd Feature-Flag-Lifecycle-Stale-Flag-Detection

# Install dependencies
npm install
```

### Running Locally (frontend + backend)

```bash
# Terminal 1: backend (FastAPI + SQLite, seeds demo data on first start)
cd backend
pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# API docs: http://127.0.0.1:8000/docs

# Terminal 2: frontend (Vite, talks to backend via VITE_API_URL)
npm run dev
```

Visit `http://localhost:5173` to explore the application.
Copy `.env.example` to `.env` to override `VITE_API_URL` (defaults to `http://127.0.0.1:8000`).
When the backend is unreachable, the UI automatically falls back to bundled mock data.

See `backend/README.md` for the full lifecycle workflow (register repo → scan →
evidence/risk → Piranha removal → tests → verification) and tool-integration notes.

### Building for Production

```bash
# Type check and build bundle
npm run build

# Preview production build
npm run preview
```

## Docker Deployment (FFSD Frontend)

The frontend is containerized using a multi-stage Docker build served via Nginx with SPA routing support.

### Option 1: Docker Compose (Recommended)

```bash
# Build and run container
docker compose up -d

# View logs
docker compose logs -f

# Stop container
docker compose down
```

### Option 2: Docker CLI

```bash
# Build the image
docker build -t ffsd-frontend:latest .

# Run the container
docker run -d --name ffsd-frontend -p 3000:80 ffsd-frontend:latest
```

The application will be available at: **`http://localhost:3000`**

## License

MIT
