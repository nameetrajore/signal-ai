# SignalAI Product Requirements Document

## Original Problem Statement
SignalAI is an AI news curator that cuts through hype, fear mongering, and speculation. It aggregates AI news from curated sources, scores each article on a hype scale (1-5), groups the same story from multiple perspectives, and tracks predictions that journalists and executives make.

## Architecture
- **Backend**: FastAPI + MongoDB + APScheduler (cron jobs)
- **Frontend**: React + Tailwind CSS + Shadcn/UI
- **LLM**: Claude Sonnet 4.5 via Emergent LLM Key
- **News Sources**: NewsAPI + RSS feeds (MIT Tech Review, Ars Technica, VentureBeat, Wired, TechCrunch, The Verge)
- **Content Extraction**: newspaper3k + BeautifulSoup + youtube-transcript-api
- **Email**: Resend
- **Clustering**: TF-IDF + Cosine Similarity

## User Personas
1. **AI Researcher**: Wants factual, low-hype coverage of AI developments
2. **Tech Professional**: Needs to separate signal from noise in AI news
3. **Skeptical Reader**: Wants to verify claims and track predictions

## Core Requirements

### MVP (Phase 1) - COMPLETED
- [x] **Check This** - URL analyzer for articles and YouTube
- [x] **News Feed** - Chronological AI news with hype scores
- [x] **Hype Scoring** - 1-5 scale with color-coded badges
- [x] **Prediction Graveyard** - Track and verify predictions
- [x] **Daily Digest** - Top 5 low-hype articles
- [x] **Claims Extraction** - Identify supported/unsupported claims

### Phase 2 - COMPLETED (March 27, 2026)
- [x] **Story Clustering** - TF-IDF based grouping of related articles
- [x] **Email Subscription** - Daily digest via Resend
- [x] **Automated Cron Jobs** - 6-hour news ingestion, 8AM UTC digest
- [x] **Blindspot Feature** - Stories underreported by major sources

## What's Been Implemented

### Backend Features
1. TF-IDF clustering with cosine similarity (threshold 0.3)
2. Keyword extraction for cluster labels
3. APScheduler with two jobs:
   - News ingestion every 6 hours
   - Daily digest email at 8 AM UTC
4. Resend integration for HTML digest emails
5. Blindspot analysis comparing 15 curated AI sources
6. Subscriber management (subscribe/unsubscribe)

### Frontend Pages
1. **Feed** - News feed with hype filters, stats sidebar, email subscribe widget
2. **Stories** - Cluster view with side-by-side source comparison
3. **Blindspots** - Underreported stories with coverage analysis
4. **Graveyard** - Prediction tracking with status updates
5. **Digest** - Daily low-hype summary with inline subscription

## Hype Score System
- 1 (Green) - Primary source / peer-reviewed
- 2 (Green) - Grounded reporting with named sources
- 3 (Yellow) - Opinion / analysis
- 4 (Red) - Speculation without evidence
- 5 (Red) - Fear mongering / clickbait

## API Endpoints
- GET /api/articles - Articles with hype filtering
- GET /api/clusters - Story clusters with articles
- GET /api/blindspots - Underreported stories
- GET /api/predictions - Tracked predictions
- GET /api/digest - Daily digest content
- POST /api/check-url - Analyze any URL
- POST /api/subscribe - Email subscription
- POST /api/ingest - Trigger news ingestion
- POST /api/cluster - Trigger clustering
- POST /api/send-digest - Trigger digest emails

## Prioritized Backlog
### P1 (Next Sprint):
- [ ] Search functionality across articles
- [ ] User accounts and saved articles
- [ ] Custom email digest frequency

### P2 (Future):
- [ ] Source credibility ratings
- [ ] API rate limiting and caching
- [ ] Mobile app
- [ ] RSS feed export
