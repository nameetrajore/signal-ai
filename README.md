# SignalAI

> Cut through the noise. Get the signal.

SignalAI is an AI news curator that filters out hype, fear-mongering, and speculation from AI journalism. It aggregates articles from top sources, scores them on a hype scale using Claude AI, and surfaces what actually matters — so you don't have to.

---

## What It Does

The AI news cycle is full of breathless headlines and half-baked predictions. SignalAI helps you:

- **Score the hype** — Every article gets a 1–5 hype rating powered by Claude AI
- **Group related stories** — TF-IDF clustering shows you how the same story is covered across sources
- **Find blindspots** — Surface underreported stories that major outlets are ignoring
- **Track predictions** — Log claims and predictions from journalists and executives, then verify them over time
- **Check any URL** — Paste any article or YouTube video link to get an instant hype score and claims analysis
- **Get a daily digest** — Subscribe to a curated email of the day's top 5 low-hype articles

---

## Tech Stack

**Frontend**
- React 19 + React Router v7
- Tailwind CSS + Shadcn/UI
- Recharts for data visualization

**Backend**
- FastAPI + Motor (async MongoDB)
- APScheduler for cron jobs (ingestion every 6h, digest at 8 AM UTC)
- Claude Sonnet for hype scoring and claims extraction
- scikit-learn / TF-IDF for article clustering
- newspaper3k + BeautifulSoup4 for content extraction
- Resend for transactional email

**Data Sources**
- NewsAPI
- RSS feeds: MIT Tech Review, Ars Technica, VentureBeat, Wired, TechCrunch, The Verge, and more

---

## Getting Started

### Prerequisites

- Node.js + Yarn
- Python 3.9+
- MongoDB (local or Atlas)
- A [Resend](https://resend.com) API key for email

### Backend

```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:

```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=signalai
RESEND_API_KEY=your-resend-api-key
SENDER_EMAIL=digest@yourdomain.com
```

Start the server:

```bash
python server.py
# or
uvicorn server:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
yarn install
```

Create a `.env` file in the `frontend/` directory:

```env
REACT_APP_BACKEND_URL=http://localhost:8000
```

Start the dev server:

```bash
yarn start
```

The app will be available at `http://localhost:3000`.

---

## Project Structure

```
signal-ai/
├── backend/
│   ├── server.py          # FastAPI app — routes, ingestion, scoring, clustering
│   └── requirements.txt   # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.js         # Main app with all pages and routing
│   │   └── components/ui/ # Shadcn/UI component library
│   ├── tailwind.config.js
│   └── package.json
├── memory/
│   └── PRD.md             # Product requirements document
└── tests/                 # Test suite
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/articles` | Fetch articles (supports hype score filtering) |
| `GET` | `/api/clusters` | Get story clusters |
| `GET` | `/api/digest` | Get today's digest |
| `GET` | `/api/blindspots` | Get underreported stories |
| `GET` | `/api/predictions` | Get tracked predictions |
| `POST` | `/api/check-url` | Analyze any article or YouTube URL |
| `POST` | `/api/subscribe` | Subscribe to the daily email digest |
| `POST` | `/api/unsubscribe` | Unsubscribe from emails |
| `POST` | `/api/ingest` | Manually trigger news ingestion |
| `POST` | `/api/cluster` | Manually trigger story clustering |
| `POST` | `/api/send-digest` | Manually trigger digest email |

---

## Hype Scale

| Score | Meaning |
|-------|---------|
| 1 | Pure signal — factual, measured, well-sourced |
| 2 | Mostly signal with minor speculation |
| 3 | Mixed — some useful info buried in hype |
| 4 | Mostly hype — sensational framing, thin on facts |
| 5 | Maximum hype — fear-mongering or pure speculation |

---

## License

MIT
