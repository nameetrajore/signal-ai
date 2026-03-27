from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import asyncio
import re
from collections import Counter
import math
import resend
from apscheduler.schedulers.asyncio import AsyncIOScheduler

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Resend setup
resend.api_key = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')

# Create the main app
app = FastAPI(title="SignalAI API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Scheduler for cron jobs
scheduler = AsyncIOScheduler()

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
    keywords: List[str] = []
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class Cluster(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    keywords: List[str] = []
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

class Subscriber(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class Claim(BaseModel):
    claim: str
    supported: bool

class CheckUrlRequest(BaseModel):
    url: str
    transcript: Optional[str] = None  # Optional: client can provide YouTube transcript

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

class SubscribeRequest(BaseModel):
    email: EmailStr

class BlindspotStory(BaseModel):
    cluster_id: str
    label: str
    total_sources: int
    covering_sources: List[str]
    missing_sources: List[str]
    coverage_ratio: float
    sample_article: Optional[Dict[str, Any]] = None

# ============= AI Relevance Scoring =============

AI_KEYWORDS = {
    # Core AI terms (high weight)
    'artificial intelligence': 3, 'machine learning': 3, 'deep learning': 3,
    'neural network': 3, 'neural networks': 3, 'large language model': 3,
    'llm': 3, 'llms': 3, 'gpt': 3, 'chatgpt': 3, 'openai': 3, 'anthropic': 3,
    'claude': 3, 'gemini': 3, 'copilot': 3, 'midjourney': 3, 'stable diffusion': 3,
    'dall-e': 3, 'sora': 3, 'transformer': 3, 'transformers': 3,
    
    # AI concepts (medium weight)
    'natural language processing': 2, 'nlp': 2, 'computer vision': 2,
    'generative ai': 2, 'gen ai': 2, 'genai': 2, 'foundation model': 2,
    'reinforcement learning': 2, 'supervised learning': 2, 'unsupervised learning': 2,
    'training data': 2, 'fine-tuning': 2, 'fine tuning': 2, 'prompt engineering': 2,
    'embedding': 2, 'embeddings': 2, 'vector database': 2, 'rag': 2,
    'retrieval augmented': 2, 'multimodal': 2, 'diffusion model': 2,
    'language model': 2, 'chatbot': 2, 'ai model': 2, 'ai models': 2,
    'ai system': 2, 'ai systems': 2, 'ai agent': 2, 'ai agents': 2,
    'autonomous ai': 2, 'agi': 2, 'artificial general intelligence': 2,
    
    # AI companies/labs (medium weight)
    'deepmind': 2, 'meta ai': 2, 'google ai': 2, 'microsoft ai': 2,
    'nvidia ai': 2, 'hugging face': 2, 'huggingface': 2, 'cohere': 2,
    'mistral': 2, 'stability ai': 2, 'inflection': 2, 'xai': 2,
    'perplexity': 2, 'character ai': 2, 'runway': 2, 'replicate': 2,
    
    # AI-related terms (low weight)
    'ai': 1, 'ml': 1, 'algorithm': 1, 'algorithms': 1, 'automation': 1,
    'robotics': 1, 'robot': 1, 'robots': 1, 'inference': 1, 'prediction': 1,
    'classification': 1, 'regression': 1, 'clustering': 1, 'dataset': 1,
    'datasets': 1, 'benchmark': 1, 'gpu': 1, 'gpus': 1, 'tensor': 1,
    'pytorch': 1, 'tensorflow': 1, 'model': 1, 'parameters': 1,
    'tokens': 1, 'tokenizer': 1, 'context window': 1, 'hallucination': 1,
    'bias': 1, 'alignment': 1, 'safety': 1, 'ethics': 1,
}

# Minimum score to be considered AI-related
AI_RELEVANCE_THRESHOLD = 6

def calculate_ai_relevance_score(text: str, title: str = "") -> int:
    """
    Calculate AI relevance score for an article.
    Returns score based on presence of AI-related keywords.
    Higher score = more AI-related.
    """
    combined_text = f"{title} {title} {text}".lower()  # Title weighted 2x
    score = 0
    matched_keywords = []
    
    for keyword, weight in AI_KEYWORDS.items():
        # Count occurrences (with word boundaries for short terms)
        if len(keyword) <= 3:
            # For short terms like 'ai', 'ml', 'llm', use word boundaries
            pattern = r'\b' + re.escape(keyword) + r'\b'
            count = len(re.findall(pattern, combined_text))
        else:
            count = combined_text.count(keyword)
        
        if count > 0:
            # Diminishing returns for repeated keywords
            keyword_score = weight * min(count, 3)
            score += keyword_score
            matched_keywords.append(keyword)
    
    return score

def is_ai_related(text: str, title: str = "") -> bool:
    """Check if article is AI-related based on keyword scoring"""
    score = calculate_ai_relevance_score(text, title)
    return score >= AI_RELEVANCE_THRESHOLD

# ============= TF-IDF Clustering =============

STOP_WORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
    'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
    'into', 'through', 'during', 'before', 'after', 'above', 'below',
    'between', 'under', 'again', 'further', 'then', 'once', 'here',
    'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more',
    'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
    'same', 'so', 'than', 'too', 'very', 'just', 'and', 'but', 'if', 'or',
    'because', 'until', 'while', 'about', 'against', 'both', 'any', 'that',
    'this', 'these', 'those', 'it', 'its', 'he', 'she', 'they', 'them',
    'his', 'her', 'their', 'what', 'which', 'who', 'whom', 'said', 'says',
    'according', 'also', 'new', 'like', 'get', 'make', 'made', 'year', 'years'
}

def tokenize(text: str) -> List[str]:
    """Tokenize text into words, removing stop words"""
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    return [w for w in words if w not in STOP_WORDS]

def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    """Extract top keywords from text using term frequency"""
    words = tokenize(text)
    if not words:
        return []
    counter = Counter(words)
    return [word for word, _ in counter.most_common(top_n)]

def compute_tfidf(documents: List[List[str]]) -> Dict[str, Dict[str, float]]:
    """Compute TF-IDF scores for documents"""
    # Document frequency
    df = Counter()
    for doc in documents:
        df.update(set(doc))
    
    n_docs = len(documents)
    tfidf_scores = {}
    
    for i, doc in enumerate(documents):
        doc_id = str(i)
        tf = Counter(doc)
        total_terms = len(doc)
        tfidf_scores[doc_id] = {}
        
        for term, count in tf.items():
            tf_score = count / total_terms if total_terms > 0 else 0
            idf_score = math.log(n_docs / (df[term] + 1)) + 1
            tfidf_scores[doc_id][term] = tf_score * idf_score
    
    return tfidf_scores

def cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
    """Compute cosine similarity between two TF-IDF vectors"""
    common_terms = set(vec1.keys()) & set(vec2.keys())
    if not common_terms:
        return 0.0
    
    dot_product = sum(vec1[t] * vec2[t] for t in common_terms)
    norm1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
    norm2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)

async def cluster_articles(similarity_threshold: float = 0.3):
    """Cluster articles based on TF-IDF similarity"""
    logger.info("Starting article clustering...")
    
    # Get all articles without cluster
    articles = await db.articles.find(
        {"cluster_id": None},
        {"_id": 0}
    ).to_list(500)
    
    if len(articles) < 2:
        logger.info("Not enough articles to cluster")
        return
    
    # Tokenize all articles
    documents = []
    for article in articles:
        text = f"{article.get('title', '')} {article.get('summary', '')} {article.get('raw_text', '')[:1000]}"
        tokens = tokenize(text)
        documents.append(tokens)
        # Update article keywords
        keywords = extract_keywords(text)
        await db.articles.update_one(
            {"id": article["id"]},
            {"$set": {"keywords": keywords}}
        )
    
    # Compute TF-IDF
    tfidf = compute_tfidf(documents)
    
    # Find similar articles and create clusters
    clustered = set()
    
    for i, article in enumerate(articles):
        if article["id"] in clustered:
            continue
        
        similar_articles = [article]
        clustered.add(article["id"])
        
        for j, other_article in enumerate(articles):
            if i >= j or other_article["id"] in clustered:
                continue
            
            similarity = cosine_similarity(tfidf[str(i)], tfidf[str(j)])
            
            if similarity >= similarity_threshold:
                similar_articles.append(other_article)
                clustered.add(other_article["id"])
        
        # Create cluster if we have multiple articles
        if len(similar_articles) >= 2:
            # Generate cluster label from common keywords
            all_keywords = []
            for a in similar_articles:
                text = f"{a.get('title', '')} {a.get('summary', '')}"
                all_keywords.extend(extract_keywords(text, 5))
            
            common_keywords = [w for w, c in Counter(all_keywords).most_common(5) if c > 1]
            label = " ".join(common_keywords[:3]).title() if common_keywords else similar_articles[0].get("title", "Story")[:50]
            
            cluster = Cluster(
                label=label,
                keywords=common_keywords,
                article_ids=[a["id"] for a in similar_articles]
            )
            
            await db.clusters.insert_one(cluster.model_dump())
            
            # Update articles with cluster_id
            for a in similar_articles:
                await db.articles.update_one(
                    {"id": a["id"]},
                    {"$set": {"cluster_id": cluster.id}}
                )
            
            logger.info(f"Created cluster '{label}' with {len(similar_articles)} articles")
    
    logger.info("Clustering complete")

# ============= LLM Service =============

async def call_claude(prompt: str, system_message: str = "You are a helpful AI assistant.") -> str:
    """Call Claude API using litellm"""
    try:
        import litellm

        api_key = os.environ.get('ANTHROPIC_API_KEY', os.environ.get('EMERGENT_LLM_KEY', ''))
        if not api_key:
            logger.error("No API key found (ANTHROPIC_API_KEY or EMERGENT_LLM_KEY)")
            return ""

        response = await litellm.acompletion(
            model="anthropic/claude-sonnet-4-5-20250929",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            api_key=api_key
        )
        return response.choices[0].message.content or ""
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
    """Get YouTube video transcript with proxy support"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        
        # Check if proxy is configured
        proxy_username = os.environ.get('WEBSHARE_PROXY_USERNAME')
        proxy_password = os.environ.get('WEBSHARE_PROXY_PASSWORD')
        
        if proxy_username and proxy_password:
            # Use Webshare residential proxy
            from youtube_transcript_api.proxies import WebshareProxyConfig
            
            ytt_api = YouTubeTranscriptApi(
                proxy_config=WebshareProxyConfig(
                    proxy_username=proxy_username,
                    proxy_password=proxy_password
                )
            )
            logger.info(f"Using Webshare proxy for YouTube transcript")
        else:
            # Try without proxy (may fail on cloud)
            ytt_api = YouTubeTranscriptApi()
        
        transcript = ytt_api.fetch(video_id)
        
        # Handle different response formats
        if hasattr(transcript, '__iter__'):
            text_parts = []
            for segment in transcript:
                if hasattr(segment, 'text'):
                    text_parts.append(segment.text)
                elif isinstance(segment, dict):
                    text_parts.append(segment.get('text', ''))
            return " ".join(text_parts)
        return str(transcript)
        
    except Exception as e:
        error_msg = str(e).lower()
        
        # Check if it's an IP blocking issue
        if 'blocked' in error_msg or 'ip' in error_msg or 'cloud' in error_msg:
            logger.warning(f"YouTube blocking IP for video {video_id}")
            raise Exception("YouTube is blocking requests. Configure WEBSHARE_PROXY_USERNAME and WEBSHARE_PROXY_PASSWORD in .env for proxy support.")
        
        logger.error(f"YouTube transcript error: {e}")
        return ""

async def extract_article_content(url: str) -> Dict[str, Any]:
    """Extract article content using newspaper3k with fallback to requests"""
    import requests
    from bs4 import BeautifulSoup
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    # First try requests + BeautifulSoup (most reliable)
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove scripts, styles, and other non-content elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript']):
            element.decompose()
        
        # Extract title
        title = ""
        if soup.title:
            title = soup.title.get_text(strip=True)
        elif soup.find('h1'):
            title = soup.find('h1').get_text(strip=True)
        
        # Try to find article content
        article_content = soup.find('article')
        if article_content:
            text_parts = []
            for p in article_content.find_all('p'):
                text = p.get_text(strip=True)
                if len(text) > 30:
                    text_parts.append(text)
            if text_parts:
                return {"title": title or "Article", "text": " ".join(text_parts), "source": url}
        
        # Fallback: get all paragraphs
        text_parts = []
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            if len(text) > 30:
                text_parts.append(text)
        
        if text_parts:
            return {"title": title or "Article", "text": " ".join(text_parts), "source": url}
        
    except Exception as e:
        logger.error(f"BeautifulSoup extraction error: {e}")
    
    # Fallback to newspaper3k
    try:
        from newspaper import Article as NewsArticle
        article = NewsArticle(url)
        article.download()
        article.parse()
        
        if article.text and len(article.text) > 50:
            return {
                "title": article.title or "Unknown Title",
                "text": article.text,
                "source": article.source_url or url
            }
    except Exception as e:
        logger.error(f"Newspaper3k extraction error: {e}")
    
    return {"title": "Unknown Title", "text": "", "source": url}

# ============= News Ingestion =============

# Curated AI news sources
CURATED_SOURCES = [
    "MIT Technology Review", "Ars Technica", "The Gradient", "Import AI",
    "Interconnects", "Stratechery", "VentureBeat", "Wired", "TechCrunch",
    "The Verge", "Reuters", "Bloomberg", "Nature", "Science", "arXiv"
]

async def fetch_news_from_api() -> List[Dict[str, Any]]:
    """Fetch AI news from NewsAPI"""
    import requests
    
    api_key = os.environ.get('NEWS_API_KEY')
    if not api_key:
        logger.error("NEWS_API_KEY not found")
        return []
    
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": "artificial intelligence OR AI OR machine learning OR LLM OR GPT",
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": 30,
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
        ("https://www.technologyreview.com/feed/", "MIT Technology Review"),
        ("https://arstechnica.com/feed/", "Ars Technica"),
        ("https://feeds.feedburner.com/venturebeat/SZYF", "VentureBeat"),
        ("https://www.wired.com/feed/tag/ai/latest/rss", "Wired"),
        ("https://techcrunch.com/tag/artificial-intelligence/feed/", "TechCrunch"),
        ("https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "The Verge"),
    ]
    
    articles = []
    for feed_url, source_name in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                articles.append({
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "source": {"name": source_name},
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
    title = article_data.get("title", content.get("title", ""))
    
    if not text or len(text) < 50:
        return None
    
    # Check AI relevance - skip non-AI articles
    ai_score = calculate_ai_relevance_score(text, title)
    if ai_score < AI_RELEVANCE_THRESHOLD:
        logger.info(f"Skipping non-AI article (score {ai_score}): {title[:50]}")
        return None
    
    # Score and summarize
    hype_result = await score_hype(text)
    summary = await summarize_article(text)
    
    # Extract keywords for clustering
    keywords = extract_keywords(f"{title} {text}")
    
    # Extract predictions
    predictions = await extract_predictions(text, url, title)
    
    # Store article
    article = Article(
        url=url,
        title=title or "Unknown",
        source_name=article_data.get("source", {}).get("name", "Unknown"),
        published_at=article_data.get("publishedAt", datetime.now(timezone.utc).isoformat()),
        raw_text=text[:5000],
        summary=summary,
        hype_score=hype_result.get("score"),
        hype_reason=hype_result.get("reason"),
        keywords=keywords
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
    for article_data in all_articles[:15]:  # Process more articles
        try:
            article_id = await process_and_store_article(article_data)
            if article_id:
                processed += 1
                await asyncio.sleep(1)  # Rate limiting
        except Exception as e:
            logger.error(f"Error processing article: {e}")
    
    logger.info(f"Processed {processed} articles")
    
    # Run clustering after ingestion
    await cluster_articles()

# ============= Email Service =============

def generate_digest_html(articles: List[Dict[str, Any]], date: str) -> str:
    """Generate HTML email for daily digest"""
    
    def get_hype_color(score: int) -> str:
        if score <= 2:
            return "#16a34a"  # green
        elif score == 3:
            return "#ca8a04"  # yellow
        return "#dc2626"  # red
    
    def get_hype_label(score: int) -> str:
        labels = {1: "Primary Source", 2: "Grounded", 3: "Opinion", 4: "Speculation", 5: "Clickbait"}
        return labels.get(score, "Unknown")
    
    articles_html = ""
    for i, article in enumerate(articles, 1):
        score = article.get("hype_score", 3)
        color = get_hype_color(score)
        label = get_hype_label(score)
        
        articles_html += f"""
        <tr>
            <td style="padding: 20px 0; border-bottom: 1px solid #e5e5e5;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td width="50" style="vertical-align: top; font-size: 36px; font-weight: bold; color: #e5e5e5;">{i}</td>
                        <td style="padding-left: 15px;">
                            <span style="display: inline-block; padding: 2px 8px; font-size: 11px; font-weight: bold; color: {color}; background: {color}22; border-radius: 3px; margin-bottom: 8px;">
                                {score} / {label}
                            </span>
                            <p style="margin: 0 0 5px 0; font-size: 11px; color: #666; text-transform: uppercase;">{article.get('source_name', 'Unknown')}</p>
                            <h3 style="margin: 0 0 10px 0; font-size: 18px; font-weight: bold;">
                                <a href="{article.get('url', '#')}" style="color: #111; text-decoration: none;">{article.get('title', 'Untitled')}</a>
                            </h3>
                            <p style="margin: 0; color: #444; line-height: 1.5;">{article.get('summary', '')}</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background: #f5f5f5; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background: #fff; border-radius: 8px; overflow: hidden;">
                        <!-- Header -->
                        <tr>
                            <td style="background: #111; padding: 30px; text-align: center;">
                                <h1 style="margin: 0; color: #fff; font-size: 28px; font-weight: bold;">SignalAI Daily Digest</h1>
                                <p style="margin: 10px 0 0 0; color: #999; font-size: 14px;">{date}</p>
                            </td>
                        </tr>
                        
                        <!-- Intro -->
                        <tr>
                            <td style="padding: 30px; border-bottom: 1px solid #e5e5e5;">
                                <p style="margin: 0; color: #666; line-height: 1.6;">
                                    Today's top AI developments, filtered for signal over noise. Only stories with hype scores of 1-2.
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Articles -->
                        <tr>
                            <td style="padding: 0 30px;">
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    {articles_html}
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 30px; background: #f9f9f9; text-align: center;">
                                <p style="margin: 0; color: #999; font-size: 12px;">
                                    You're receiving this because you subscribed to SignalAI Daily Digest.<br>
                                    <a href="#" style="color: #666;">Unsubscribe</a>
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    return html

async def send_digest_email(email: str, articles: List[Dict[str, Any]], date: str) -> bool:
    """Send daily digest email to a subscriber"""
    if not resend.api_key:
        logger.error("RESEND_API_KEY not configured")
        return False
    
    html_content = generate_digest_html(articles, date)
    
    params = {
        "from": SENDER_EMAIL,
        "to": [email],
        "subject": f"SignalAI Daily Digest - {date}",
        "html": html_content
    }
    
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Digest email sent to {email}, id: {result.get('id')}")
        return True
    except Exception as e:
        logger.error(f"Failed to send digest email to {email}: {e}")
        return False

async def send_daily_digest_to_all():
    """Send daily digest to all active subscribers"""
    logger.info("Sending daily digest to subscribers...")
    
    # Get low-hype articles
    articles = await db.articles.find(
        {"hype_score": {"$lte": 2}},
        {"_id": 0}
    ).sort("published_at", -1).limit(5).to_list(5)
    
    if not articles:
        logger.info("No low-hype articles for digest")
        return
    
    # Get active subscribers
    subscribers = await db.subscribers.find(
        {"active": True},
        {"_id": 0}
    ).to_list(1000)
    
    date = datetime.now(timezone.utc).strftime("%B %d, %Y")
    
    sent = 0
    for sub in subscribers:
        success = await send_digest_email(sub["email"], articles, date)
        if success:
            sent += 1
        await asyncio.sleep(0.5)  # Rate limiting
    
    logger.info(f"Sent digest to {sent}/{len(subscribers)} subscribers")

# ============= Blindspot Analysis =============

async def analyze_blindspots() -> List[BlindspotStory]:
    """Find stories that are being underreported by certain sources"""
    
    # Get all clusters with articles
    clusters = await db.clusters.find({}, {"_id": 0}).to_list(100)
    
    blindspots = []
    
    for cluster in clusters:
        # Get articles in this cluster
        articles = await db.articles.find(
            {"id": {"$in": cluster.get("article_ids", [])}},
            {"_id": 0}
        ).to_list(100)
        
        if len(articles) < 2:
            continue
        
        # Count sources covering this story
        covering_sources = list(set(a.get("source_name", "Unknown") for a in articles))
        
        # Find missing major sources
        missing_sources = [s for s in CURATED_SOURCES if s not in covering_sources]
        
        # Calculate coverage ratio
        coverage_ratio = len(covering_sources) / len(CURATED_SOURCES)
        
        # Only include as blindspot if significant sources are missing
        if len(missing_sources) >= len(CURATED_SOURCES) * 0.5:
            sample_article = articles[0] if articles else None
            
            blindspots.append(BlindspotStory(
                cluster_id=cluster["id"],
                label=cluster.get("label", "Unknown Story"),
                total_sources=len(CURATED_SOURCES),
                covering_sources=covering_sources,
                missing_sources=missing_sources[:10],  # Limit to top 10
                coverage_ratio=coverage_ratio,
                sample_article=sample_article
            ))
    
    # Sort by coverage ratio (lowest first = biggest blindspot)
    blindspots.sort(key=lambda x: x.coverage_ratio)
    
    return blindspots[:10]  # Return top 10 blindspots

# ============= Scheduled Jobs =============

async def scheduled_ingestion():
    """Scheduled job for news ingestion every 6 hours"""
    logger.info("Running scheduled news ingestion...")
    await ingest_news_background()

async def scheduled_digest():
    """Scheduled job for daily digest at 8 AM UTC"""
    logger.info("Running scheduled daily digest...")
    await send_daily_digest_to_all()

# ============= API Endpoints =============

@api_router.get("/")
async def root():
    return {"message": "SignalAI API", "version": "1.1.0"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "scheduler": scheduler.running}

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
            "keywords": cluster.get("keywords", []),
            "articles": articles,
            "article_count": len(articles),
            "created_at": cluster.get("created_at")
        })
    
    # Sort by article count
    result.sort(key=lambda x: x["article_count"], reverse=True)
    
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
        "keywords": cluster.get("keywords", []),
        "articles": articles,
        "article_count": len(articles),
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
    
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    # Validate URL format
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Determine source type
    youtube_id = extract_youtube_id(url)
    
    if youtube_id:
        # YouTube video - prefer client-provided transcript
        if request.transcript and len(request.transcript) > 50:
            text = request.transcript
            logger.info(f"Using client-provided transcript for YouTube video {youtube_id}")
        else:
            # Try server-side extraction (may fail on cloud)
            try:
                text = await get_youtube_transcript(youtube_id)
                if not text:
                    raise HTTPException(
                        status_code=400, 
                        detail="NEED_CLIENT_TRANSCRIPT"
                    )
            except Exception as e:
                error_msg = str(e)
                if "blocking" in error_msg.lower() or "cloud" in error_msg.lower() or "NEED_CLIENT_TRANSCRIPT" in error_msg:
                    raise HTTPException(
                        status_code=400, 
                        detail="NEED_CLIENT_TRANSCRIPT"
                    )
                raise HTTPException(status_code=400, detail=f"YouTube transcript error: {error_msg}")
        title = f"YouTube Video: {youtube_id}"
        source_type = "youtube"
    else:
        # Article
        content = await extract_article_content(url)
        text = content.get("text", "")
        title = content.get("title", "Unknown Title")
        source_type = "article"
        
        if not text or len(text) < 50:
            raise HTTPException(status_code=400, detail="Could not extract enough content from this URL. The page may be blocked, require login, or have no readable text.")
    
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

@api_router.post("/subscribe")
async def subscribe_to_digest(request: SubscribeRequest):
    """Subscribe to daily digest emails"""
    email = request.email.lower()
    
    # Check if already subscribed
    existing = await db.subscribers.find_one({"email": email}, {"_id": 0})
    if existing:
        if existing.get("active"):
            return {"message": "Already subscribed", "status": "existing"}
        else:
            # Reactivate subscription
            await db.subscribers.update_one(
                {"email": email},
                {"$set": {"active": True}}
            )
            return {"message": "Subscription reactivated", "status": "reactivated"}
    
    # Create new subscriber
    subscriber = Subscriber(email=email)
    await db.subscribers.insert_one(subscriber.model_dump())
    
    return {"message": "Successfully subscribed to daily digest", "status": "new"}

@api_router.post("/unsubscribe")
async def unsubscribe_from_digest(request: SubscribeRequest):
    """Unsubscribe from daily digest emails"""
    email = request.email.lower()
    
    result = await db.subscribers.update_one(
        {"email": email},
        {"$set": {"active": False}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    
    return {"message": "Successfully unsubscribed"}

@api_router.get("/subscribers/count")
async def get_subscriber_count():
    """Get count of active subscribers"""
    count = await db.subscribers.count_documents({"active": True})
    return {"count": count}

@api_router.get("/blindspots")
async def get_blindspots():
    """Get stories that are underreported by major sources"""
    blindspots = await analyze_blindspots()
    return {"blindspots": [b.model_dump() for b in blindspots]}

@api_router.post("/cluster")
async def trigger_clustering(background_tasks: BackgroundTasks):
    """Manually trigger article clustering"""
    background_tasks.add_task(cluster_articles)
    return {"message": "Clustering started"}

@api_router.post("/ingest")
async def trigger_ingestion(background_tasks: BackgroundTasks):
    """Manually trigger news ingestion"""
    background_tasks.add_task(ingest_news_background)
    return {"message": "News ingestion started"}

@api_router.post("/send-digest")
async def trigger_digest(background_tasks: BackgroundTasks):
    """Manually trigger sending daily digest"""
    background_tasks.add_task(send_daily_digest_to_all)
    return {"message": "Digest sending started"}

@api_router.post("/cleanup-non-ai")
async def cleanup_non_ai_articles():
    """Remove non-AI related articles from database"""
    logger.info("Starting cleanup of non-AI articles...")
    
    # Get all articles
    articles = await db.articles.find({}, {"_id": 0}).to_list(1000)
    
    removed_count = 0
    removed_titles = []
    kept_count = 0
    
    for article in articles:
        title = article.get("title", "")
        text = article.get("raw_text", "") or article.get("summary", "")
        
        ai_score = calculate_ai_relevance_score(text, title)
        
        if ai_score < AI_RELEVANCE_THRESHOLD:
            # Remove article
            await db.articles.delete_one({"id": article["id"]})
            
            # Remove from clusters
            await db.clusters.update_many(
                {},
                {"$pull": {"article_ids": article["id"]}}
            )
            
            # Remove associated predictions
            await db.predictions.delete_many({"article_id": article["id"]})
            
            removed_count += 1
            removed_titles.append(f"{title[:50]}... (score: {ai_score})")
        else:
            kept_count += 1
    
    # Clean up empty clusters
    empty_clusters = await db.clusters.delete_many({"article_ids": {"$size": 0}})
    
    logger.info(f"Cleanup complete: removed {removed_count} articles, kept {kept_count}")
    
    return {
        "message": "Cleanup complete",
        "removed_count": removed_count,
        "kept_count": kept_count,
        "removed_articles": removed_titles[:20],  # Show first 20
        "empty_clusters_removed": empty_clusters.deleted_count
    }

@api_router.get("/stats")
async def get_stats():
    """Get platform statistics"""
    article_count = await db.articles.count_documents({})
    prediction_count = await db.predictions.count_documents({})
    cluster_count = await db.clusters.count_documents({})
    subscriber_count = await db.subscribers.count_documents({"active": True})
    
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
        "subscribers": subscriber_count,
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
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Start the scheduler on app startup"""
    # Schedule news ingestion every 6 hours
    scheduler.add_job(scheduled_ingestion, 'interval', hours=6, id='news_ingestion')
    
    # Schedule daily digest at 8 AM UTC
    scheduler.add_job(scheduled_digest, 'cron', hour=8, minute=0, id='daily_digest')
    
    scheduler.start()
    logger.info("Scheduler started with jobs: news_ingestion (6h), daily_digest (8AM UTC)")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    scheduler.shutdown()
    client.close()
