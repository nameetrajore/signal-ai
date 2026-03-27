from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import asyncio
import re

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="SignalAI API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============= Models =============

class Article(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    title: str
    source_name: str
    published_at: str
    raw_text: Optional[str] = None
    summary: Optional[str] = None
    hype_score: Optional[int] = None
    hype_reason: Optional[str] = None
    cluster_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class Cluster(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    article_ids: List[str] = []
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class Prediction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    article_id: Optional[str] = None
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    claim: str
    predicted_timeframe: str
    status: str = "pending"  # pending, true, false
    resolved_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class Claim(BaseModel):
    claim: str
    supported: bool

class CheckUrlRequest(BaseModel):
    url: str

class CheckUrlResponse(BaseModel):
    url: str
    title: str
    source_type: str  # article, youtube
    hype_score: int
    hype_reason: str
    summary: str
    claims: List[Claim]
    predictions: List[Dict[str, Any]]

class ArticleResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    url: str
    title: str
    source_name: str
    published_at: str
    summary: Optional[str] = None
    hype_score: Optional[int] = None
    hype_reason: Optional[str] = None
    cluster_id: Optional[str] = None

class DigestArticle(BaseModel):
    title: str
    summary: str
    source_name: str
    hype_score: int
    url: str

class DailyDigestResponse(BaseModel):
    date: str
    articles: List[DigestArticle]

# ============= LLM Service =============

async def call_claude(prompt: str, system_message: str = "You are a helpful AI assistant.") -> str:
    """Call Claude API using emergentintegrations"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            logger.error("EMERGENT_LLM_KEY not found")
            return ""
        
        chat = LlmChat(
            api_key=api_key,
            session_id=str(uuid.uuid4()),
            system_message=system_message
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        return response
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return ""

async def score_hype(text: str) -> Dict[str, Any]:
    """Score article hype level 1-5"""
    prompt = f"""Rate this article 1-5 on factual grounding. 
1 = primary source or peer-reviewed research
2 = grounded reporting with named sources
3 = opinion/analysis
4 = speculation without evidence
5 = fear mongering or clickbait

Return ONLY valid JSON: {{"score": <int 1-5>, "reason": "<one sentence>"}}

Article: {text[:4000]}"""
    
    response = await call_claude(prompt, "You are a media analysis expert. Return only valid JSON.")
    try:
        import json
        # Clean response - extract JSON
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        result = json.loads(response.strip())
        return {"score": int(result.get("score", 3)), "reason": result.get("reason", "")}
    except:
        return {"score": 3, "reason": "Unable to determine hype level"}

async def summarize_article(text: str) -> str:
    """Generate 2-sentence summary"""
    prompt = f"""Summarize this article in exactly 2 sentences. Be factual, neutral, and avoid hype.

Article: {text[:4000]}"""
    
    response = await call_claude(prompt, "You are a neutral news summarizer. Be concise and factual.")
    return response.strip()

async def extract_predictions(text: str, source_url: str = "", source_title: str = "") -> List[Dict[str, Any]]:
    """Extract falsifiable predictions from text"""
    prompt = f"""Does this article make any falsifiable predictions about the future? 
If yes, return JSON: {{"has_prediction": true, "predictions": [{{"claim": "<string>", "timeframe": "<string>"}}]}}
If no, return {{"has_prediction": false, "predictions": []}}

Return ONLY valid JSON.

Article: {text[:4000]}"""
    
    response = await call_claude(prompt, "You are an expert at identifying predictions and claims about the future. Return only valid JSON.")
    try:
        import json
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        result = json.loads(response.strip())
        if result.get("has_prediction"):
            predictions = []
            for p in result.get("predictions", []):
                predictions.append({
                    "claim": p.get("claim", ""),
                    "timeframe": p.get("timeframe", "Unknown"),
                    "source_url": source_url,
                    "source_title": source_title
                })
            return predictions
        return []
    except:
        return []

async def extract_claims(text: str) -> List[Dict[str, Any]]:
    """Extract factual claims from text"""
    prompt = f"""List all factual claims made in this content. For each claim, note whether it is supported by evidence in the text or stated without backing.
Return ONLY valid JSON: {{"claims": [{{"claim": "<string>", "supported": <boolean>}}]}}

Content: {text[:4000]}"""
    
    response = await call_claude(prompt, "You are an expert fact-checker. Identify claims and whether they have supporting evidence. Return only valid JSON.")
    try:
        import json
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        result = json.loads(response.strip())
        return result.get("claims", [])
    except:
        return []

# ============= Content Extraction =============

def extract_youtube_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/shorts\/([^&\n?#]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

async def get_youtube_transcript(video_id: str) -> str:
    """Get YouTube video transcript"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t['text'] for t in transcript_list])
    except Exception as e:
        logger.error(f"YouTube transcript error: {e}")
        return ""

async def extract_article_content(url: str) -> Dict[str, Any]:
    """Extract article content using newspaper3k"""
    try:
        from newspaper import Article as NewsArticle
        article = NewsArticle(url)
        article.download()
        article.parse()
        return {
            "title": article.title or "Unknown Title",
            "text": article.text or "",
            "source": article.source_url or url
        }
    except Exception as e:
        logger.error(f"Article extraction error: {e}")
        return {"title": "Unknown Title", "text": "", "source": url}

# ============= News Ingestion =============

async def fetch_news_from_api() -> List[Dict[str, Any]]:
    """Fetch AI news from NewsAPI"""
    import requests
    
    api_key = os.environ.get('NEWS_API_KEY')
    if not api_key:
        logger.error("NEWS_API_KEY not found")
        return []
    
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": "artificial intelligence OR AI OR machine learning",
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": 20,
        "apiKey": api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("articles", [])
    except Exception as e:
        logger.error(f"NewsAPI error: {e}")
        return []

async def fetch_rss_feeds() -> List[Dict[str, Any]]:
    """Fetch from curated RSS feeds"""
    import feedparser
    
    feeds = [
        "https://www.technologyreview.com/feed/",
        "https://arstechnica.com/feed/",
        "https://feeds.feedburner.com/venturebeat/SZYF",
        "https://www.wired.com/feed/tag/ai/latest/rss"
    ]
    
    articles = []
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                articles.append({
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "source": {"name": feed.feed.get("title", "Unknown")},
                    "publishedAt": entry.get("published", datetime.now(timezone.utc).isoformat()),
                    "description": entry.get("summary", "")
                })
        except Exception as e:
            logger.error(f"RSS feed error for {feed_url}: {e}")
    
    return articles

async def process_and_store_article(article_data: Dict[str, Any]) -> Optional[str]:
    """Process a single article and store in DB"""
    url = article_data.get("url", "")
    if not url:
        return None
    
    # Check if already exists
    existing = await db.articles.find_one({"url": url}, {"_id": 0})
    if existing:
        return existing.get("id")
    
    # Extract full content
    content = await extract_article_content(url)
    text = content.get("text", article_data.get("description", ""))
    
    if not text:
        return None
    
    # Score and summarize
    hype_result = await score_hype(text)
    summary = await summarize_article(text)
    
    # Extract predictions
    predictions = await extract_predictions(text, url, article_data.get("title", ""))
    
    # Store article
    article = Article(
        url=url,
        title=article_data.get("title", content.get("title", "Unknown")),
        source_name=article_data.get("source", {}).get("name", "Unknown"),
        published_at=article_data.get("publishedAt", datetime.now(timezone.utc).isoformat()),
        raw_text=text[:5000],
        summary=summary,
        hype_score=hype_result.get("score"),
        hype_reason=hype_result.get("reason")
    )
    
    await db.articles.insert_one(article.model_dump())
    
    # Store predictions
    for pred in predictions:
        prediction = Prediction(
            article_id=article.id,
            source_url=url,
            source_title=article.title,
            claim=pred.get("claim", ""),
            predicted_timeframe=pred.get("timeframe", "Unknown")
        )
        await db.predictions.insert_one(prediction.model_dump())
    
    return article.id

async def ingest_news_background():
    """Background task to ingest news"""
    logger.info("Starting news ingestion...")
    
    # Fetch from NewsAPI
    news_articles = await fetch_news_from_api()
    logger.info(f"Fetched {len(news_articles)} from NewsAPI")
    
    # Fetch from RSS
    rss_articles = await fetch_rss_feeds()
    logger.info(f"Fetched {len(rss_articles)} from RSS feeds")
    
    all_articles = news_articles + rss_articles
    
    processed = 0
    for article_data in all_articles[:10]:  # Limit for MVP
        try:
            article_id = await process_and_store_article(article_data)
            if article_id:
                processed += 1
                await asyncio.sleep(1)  # Rate limiting
        except Exception as e:
            logger.error(f"Error processing article: {e}")
    
    logger.info(f"Processed {processed} articles")

# ============= API Endpoints =============

@api_router.get("/")
async def root():
    return {"message": "SignalAI API", "version": "1.0.0"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy"}

@api_router.get("/articles", response_model=List[ArticleResponse])
async def get_articles(
    hype_min: Optional[int] = None,
    hype_max: Optional[int] = None,
    limit: int = 50,
    skip: int = 0
):
    """Get articles with optional hype score filtering"""
    query = {}
    if hype_min is not None or hype_max is not None:
        query["hype_score"] = {}
        if hype_min is not None:
            query["hype_score"]["$gte"] = hype_min
        if hype_max is not None:
            query["hype_score"]["$lte"] = hype_max
        if not query["hype_score"]:
            del query["hype_score"]
    
    articles = await db.articles.find(query, {"_id": 0}).sort("published_at", -1).skip(skip).limit(limit).to_list(limit)
    return articles

@api_router.get("/articles/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: str):
    """Get single article by ID"""
    article = await db.articles.find_one({"id": article_id}, {"_id": 0})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article

@api_router.get("/clusters")
async def get_clusters():
    """Get all story clusters with their articles"""
    clusters = await db.clusters.find({}, {"_id": 0}).to_list(100)
    
    result = []
    for cluster in clusters:
        articles = await db.articles.find(
            {"id": {"$in": cluster.get("article_ids", [])}},
            {"_id": 0}
        ).to_list(100)
        result.append({
            "id": cluster.get("id"),
            "label": cluster.get("label"),
            "articles": articles,
            "created_at": cluster.get("created_at")
        })
    
    return result

@api_router.get("/clusters/{cluster_id}")
async def get_cluster(cluster_id: str):
    """Get single cluster with articles"""
    cluster = await db.clusters.find_one({"id": cluster_id}, {"_id": 0})
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    articles = await db.articles.find(
        {"id": {"$in": cluster.get("article_ids", [])}},
        {"_id": 0}
    ).to_list(100)
    
    return {
        "id": cluster.get("id"),
        "label": cluster.get("label"),
        "articles": articles,
        "created_at": cluster.get("created_at")
    }

@api_router.get("/predictions")
async def get_predictions(status: Optional[str] = None, limit: int = 100, skip: int = 0):
    """Get predictions with optional status filter"""
    query = {}
    if status:
        query["status"] = status
    
    predictions = await db.predictions.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return predictions

@api_router.patch("/predictions/{prediction_id}")
async def update_prediction_status(prediction_id: str, status: str):
    """Update prediction status (pending, true, false)"""
    if status not in ["pending", "true", "false"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    resolved_at = datetime.now(timezone.utc).isoformat() if status != "pending" else None
    
    result = await db.predictions.update_one(
        {"id": prediction_id},
        {"$set": {"status": status, "resolved_at": resolved_at}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Prediction not found")
    
    return {"message": "Prediction updated"}

@api_router.post("/check-url", response_model=CheckUrlResponse)
async def check_url(request: CheckUrlRequest):
    """Check any URL for hype, claims, and predictions"""
    url = request.url.strip()
    
    # Determine source type
    youtube_id = extract_youtube_id(url)
    
    if youtube_id:
        # YouTube video
        text = await get_youtube_transcript(youtube_id)
        if not text:
            raise HTTPException(status_code=400, detail="Could not extract YouTube transcript")
        title = f"YouTube Video: {youtube_id}"
        source_type = "youtube"
    else:
        # Article
        content = await extract_article_content(url)
        text = content.get("text", "")
        title = content.get("title", "Unknown Title")
        source_type = "article"
        
        if not text:
            raise HTTPException(status_code=400, detail="Could not extract article content")
    
    # Analyze content
    hype_result = await score_hype(text)
    summary = await summarize_article(text)
    claims = await extract_claims(text)
    predictions = await extract_predictions(text, url, title)
    
    # Store predictions in database
    for pred in predictions:
        prediction = Prediction(
            source_url=url,
            source_title=title,
            claim=pred.get("claim", ""),
            predicted_timeframe=pred.get("timeframe", "Unknown")
        )
        await db.predictions.insert_one(prediction.model_dump())
    
    return CheckUrlResponse(
        url=url,
        title=title,
        source_type=source_type,
        hype_score=hype_result.get("score", 3),
        hype_reason=hype_result.get("reason", ""),
        summary=summary,
        claims=[Claim(claim=c.get("claim", ""), supported=c.get("supported", False)) for c in claims],
        predictions=predictions
    )

@api_router.get("/digest", response_model=DailyDigestResponse)
async def get_daily_digest():
    """Get today's top 5 low-hype AI developments"""
    today = datetime.now(timezone.utc).date().isoformat()
    
    # Get articles with low hype scores (1-2)
    articles = await db.articles.find(
        {"hype_score": {"$lte": 2}},
        {"_id": 0}
    ).sort("published_at", -1).limit(5).to_list(5)
    
    digest_articles = [
        DigestArticle(
            title=a.get("title", ""),
            summary=a.get("summary", ""),
            source_name=a.get("source_name", ""),
            hype_score=a.get("hype_score", 0),
            url=a.get("url", "")
        )
        for a in articles
    ]
    
    return DailyDigestResponse(date=today, articles=digest_articles)

@api_router.post("/ingest")
async def trigger_ingestion(background_tasks: BackgroundTasks):
    """Manually trigger news ingestion"""
    background_tasks.add_task(ingest_news_background)
    return {"message": "News ingestion started"}

@api_router.get("/stats")
async def get_stats():
    """Get platform statistics"""
    article_count = await db.articles.count_documents({})
    prediction_count = await db.predictions.count_documents({})
    cluster_count = await db.clusters.count_documents({})
    
    pending_predictions = await db.predictions.count_documents({"status": "pending"})
    true_predictions = await db.predictions.count_documents({"status": "true"})
    false_predictions = await db.predictions.count_documents({"status": "false"})
    
    hype_distribution = {}
    for score in range(1, 6):
        hype_distribution[str(score)] = await db.articles.count_documents({"hype_score": score})
    
    return {
        "articles": article_count,
        "predictions": prediction_count,
        "clusters": cluster_count,
        "prediction_status": {
            "pending": pending_predictions,
            "true": true_predictions,
            "false": false_predictions
        },
        "hype_distribution": hype_distribution
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
