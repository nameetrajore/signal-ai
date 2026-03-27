# SignalAI Product Requirements Document

## Original Problem Statement
SignalAI is an AI news curator that cuts through hype, fear mongering, and speculation. It aggregates AI news from curated sources, scores each article on a hype scale (1-5), groups the same story from multiple perspectives, and tracks predictions that journalists and executives make.

## Architecture
- **Backend**: FastAPI + MongoDB
- **Frontend**: React + Tailwind CSS + Shadcn/UI
- **LLM**: Claude Sonnet 4.5 via Emergent LLM Key
- **News Sources**: NewsAPI + RSS feeds
- **Content Extraction**: newspaper3k + BeautifulSoup fallback
- **YouTube**: youtube-transcript-api

## User Personas
1. **AI Researcher**: Wants factual, low-hype coverage of AI developments
2. **Tech Professional**: Needs to separate signal from noise in AI news
3. **Skeptical Reader**: Wants to verify claims and track predictions

## Core Requirements (Implemented)
### MVP Features:
- [x] **Check This** - URL analyzer for articles and YouTube
- [x] **News Feed** - Chronological AI news with hype scores
- [x] **Hype Scoring** - 1-5 scale with color-coded badges
- [x] **Prediction Graveyard** - Track and verify predictions
- [x] **Daily Digest** - Top 5 low-hype articles
- [x] **Claims Extraction** - Identify supported/unsupported claims
- [x] **News Ingestion** - NewsAPI + RSS feeds pipeline

### Hype Score System:
- 1 (Green) - Primary source / peer-reviewed
- 2 (Green) - Grounded reporting with named sources
- 3 (Yellow) - Opinion / analysis
- 4 (Red) - Speculation without evidence
- 5 (Red) - Fear mongering / clickbait

## What's Been Implemented (March 27, 2026)
1. Backend API with Claude integration for hype scoring, summarization, prediction/claim extraction
2. Check This feature for article and YouTube URL analysis
3. News feed with hype filtering (All, Low Hype, Opinion, High Hype)
4. Prediction Graveyard with status tracking (Pending, True, False)
5. Daily Digest showing only low-hype articles
6. Statistics dashboard with hype distribution
7. Ground News-inspired clean UI design

## Prioritized Backlog
### P0 (Critical):
- [x] MVP completed

### P1 (Next Sprint):
- [ ] Story clustering (group same event from multiple sources)
- [ ] Email digest subscription
- [ ] Automated cron job for 6-hour ingestion

### P2 (Future):
- [ ] Search functionality
- [ ] Source credibility ratings
- [ ] User accounts and saved articles
- [ ] API rate limiting and caching

## Next Tasks
1. Implement story clustering using text embeddings
2. Add email subscription for daily digest
3. Set up automated news ingestion cron job
4. Add more curated RSS sources
