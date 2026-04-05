"""
News Agent MCP Server

Provides MCP interface for news aggregation, summarization, and text-to-speech
capabilities. Searches multiple news sources (CNN, BBC, Reuters, AP, etc.) and
creates summaries of latest news topics with optional audio generation.

Architecture:
    - 7 MCP tools for news operations
    - Firestore persistence (news_articles, custom_news_summaries)
    - Google Cloud Text-to-Speech audio generation
    - LLM-based summarization via Gemini
    - Pub/Sub event publishing for aggregation operations
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass, asdict
import os

from backend.mcp_tools.base_mcp_server import BaseMCPServer
from backend.services.firestore_adapter import FirestoreAdapter
from backend.services.llm_service import LLMService
from backend.services.pubsub_service import PubSubService
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class NewsSource(Enum):
    """Supported news sources"""
    CNN = "cnn"
    BBC = "bbc"
    REUTERS = "reuters"
    ASSOCIATED_PRESS = "associated_press"
    AL_JAZEERA = "al_jazeera"
    THE_GUARDIAN = "the_guardian"
    NPR = "npr"
    NEW_YORK_TIMES = "new_york_times"


class NewsCategory(Enum):
    """News article categories"""
    POLITICS = "politics"
    BUSINESS = "business"
    TECHNOLOGY = "technology"
    HEALTH = "health"
    SPORTS = "sports"
    ENTERTAINMENT = "entertainment"
    WORLD = "world"
    NATIONAL = "national"
    SCIENCE = "science"
    CLIMATE = "climate"
    OPINION = "opinion"
    OTHER = "other"


@dataclass
class NewsArticle:
    """News article data structure"""
    id: str
    source: str
    category: str
    title: str
    summary: str
    url: str
    published_date: str
    authors: List[str]
    keywords: List[str]
    reading_time: int
    has_audio: bool
    audio_url: Optional[str]
    voice: Optional[str]
    audio_language: Optional[str]
    importance_score: float  # 0-1 scale for news importance
    week: int
    year: int
    is_breaking: bool
    region: str  # "national" or "world"
    engagement_score: int
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Firestore document"""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}


@dataclass
class CustomNewsSummary:
    """Custom news summary combining multiple articles"""
    id: str
    title: str
    summary: str
    article_ids: List[str]
    focus_areas: List[str]  # e.g., ["politics", "technology"]
    created_at: str
    created_by: str
    audio_url: Optional[str]
    voice: Optional[str]
    language: Optional[str]
    tags: List[str]
    is_public: bool
    view_count: int = 0
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Firestore document"""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}


class NewsAgentMCP(BaseMCPServer):
    """
    MCP Server for News Agent operations
    
    Exposes 7 tools for news aggregation, summarization, and audio generation:
    - fetch_weekly_headlines: Fetch and summarize latest news
    - get_news_summary: Get article summary with optional audio
    - search_news: Full-text search with filters
    - generate_audio: Create audio version of news
    - get_weekly_digest: Get organized weekly news digest
    - create_custom_summary: Combine articles into custom summary
    - get_trending_topics: Extract trending news topics
    """

    def __init__(self, firestore: FirestoreAdapter, llm: LLMService, pubsub: PubSubService):
        super().__init__(server_type="news", version="1.0.0")
        self.firestore = firestore
        self.llm = llm
        self.pubsub = pubsub

    async def initialize(self):
        """Initialize and register MCP tools"""
        await super().initialize()

        # Register news tools
        self.register_tool(
            name="fetch_weekly_headlines",
            description="Fetch latest news headlines from multiple sources and summarize them",
            input_schema={
                "type": "object",
                "properties": {
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "News categories (politics, business, etc.)",
                    },
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "News sources to fetch from",
                    },
                    "region": {
                        "type": "string",
                        "enum": ["national", "world", "both"],
                        "description": "Target region for news",
                    },
                    "max_articles": {
                        "type": "integer",
                        "description": "Maximum articles to fetch",
                        "default": 20,
                    },
                },
                "required": ["region"],
            },
            handler=self.fetch_weekly_headlines,
        )

        self.register_tool(
            name="get_news_summary",
            description="Get summary of a specific news article with optional audio",
            input_schema={
                "type": "object",
                "properties": {
                    "article_id": {"type": "string", "description": "Article ID"},
                    "audio_format": {
                        "type": "string",
                        "enum": ["mp3", "wav"],
                        "description": "Audio format",
                    },
                },
                "required": ["article_id"],
            },
            handler=self.get_news_summary,
        )

        self.register_tool(
            name="search_news",
            description="Search news articles with text query and filters",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "category": {
                        "type": "string",
                        "description": "Filter by category",
                    },
                    "region": {
                        "type": "string",
                        "enum": ["national", "world", "both"],
                        "description": "Filter by region",
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Search last N days",
                        "default": 7,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results",
                        "default": 20,
                    },
                },
                "required": ["query"],
            },
            handler=self.search_news,
        )

        self.register_tool(
            name="generate_audio",
            description="Generate audio version of news article or summary",
            input_schema={
                "type": "object",
                "properties": {
                    "article_id": {"type": "string", "description": "Article ID"},
                    "voice": {
                        "type": "string",
                        "enum": ["male", "female"],
                        "description": "Voice type",
                        "default": "female",
                    },
                    "language": {
                        "type": "string",
                        "description": "Language code (en-US, en-GB, etc.)",
                        "default": "en-US",
                    },
                },
                "required": ["article_id"],
            },
            handler=self.generate_audio,
        )

        self.register_tool(
            name="get_weekly_digest",
            description="Get organized weekly news digest by category",
            input_schema={
                "type": "object",
                "properties": {
                    "week_offset": {
                        "type": "integer",
                        "description": "Week offset (0=this week, -1=last week)",
                        "default": 0,
                    },
                    "region": {
                        "type": "string",
                        "enum": ["national", "world", "both"],
                        "description": "Target region",
                        "default": "both",
                    },
                },
            },
            handler=self.get_weekly_digest,
        )

        self.register_tool(
            name="create_custom_summary",
            description="Create custom news summary from selected articles",
            input_schema={
                "type": "object",
                "properties": {
                    "article_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Article IDs to summarize",
                    },
                    "title": {"type": "string", "description": "Summary title"},
                    "focus_areas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Focus areas for synthesis",
                    },
                    "generate_audio": {
                        "type": "boolean",
                        "description": "Generate audio version",
                        "default": False,
                    },
                },
                "required": ["article_ids", "title"],
            },
            handler=self.create_custom_summary,
        )

        self.register_tool(
            name="get_trending_topics",
            description="Get trending news topics from this week",
            input_schema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by category",
                    },
                    "region": {
                        "type": "string",
                        "enum": ["national", "world", "both"],
                        "description": "Target region",
                        "default": "both",
                    },
                    "period_days": {
                        "type": "integer",
                        "description": "Time period in days",
                        "default": 7,
                    },
                },
            },
            handler=self.get_trending_topics,
        )

        logger.info("News Agent MCP Server initialized with 7 tools")

    async def fetch_weekly_headlines(
        self,
        categories: Optional[List[str]] = None,
        sources: Optional[List[str]] = None,
        region: str = "both",
        max_articles: int = 20,
    ) -> Dict[str, Any]:
        """
        Fetch latest news headlines from multiple sources and create summaries
        
        Args:
            categories: News categories to fetch (politics, business, etc.)
            sources: News sources to fetch from
            region: "national" or "world"
            max_articles: Maximum articles to fetch
        
        Returns:
            Dict with fetched articles and metadata
        """
        try:
            logger.info(f"Fetching weekly headlines: region={region}, max={max_articles}")

            # Fetch articles from sources (mock - replace with real API calls)
            articles = await self._fetch_articles_from_sources(
                categories=categories,
                sources=sources,
                region=region,
                limit=max_articles,
            )

            # Summarize each article
            for article in articles:
                article["summary"] = await self._summarize_article(article.get("content", ""))

            # Store in Firestore
            stored_ids = []
            for article in articles:
                doc_id = await self.firestore.create_document(
                    collection="news_articles",
                    data=article,
                )
                stored_ids.append(doc_id)
                logger.info(f"Stored news article: {doc_id}")

            # Publish event
            await self.pubsub.publish(
                topic="news-articles-fetched",
                data={
                    "articles_count": len(articles),
                    "article_ids": stored_ids,
                    "region": region,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            return {
                "status": "success",
                "articles_fetched": len(articles),
                "articles": articles,
            }

        except Exception as e:
            logger.error(f"Error fetching headlines: {e}")
            return {
                "status": "error",
                "message": str(e),
                "articles_fetched": 0,
                "articles": [],
            }

    async def get_news_summary(
        self, article_id: str, audio_format: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get summary of specific news article with optional audio
        
        Args:
            article_id: ID of the article
            audio_format: "mp3" or "wav", optional
        
        Returns:
            Dict with article and audio URL if requested
        """
        try:
            logger.info(f"Getting news summary: article_id={article_id}")

            article = await self.firestore.get_document("news_articles", article_id)
            if not article:
                return {
                    "status": "error",
                    "message": f"Article not found: {article_id}",
                }

            # Generate audio if requested and not already generated
            if audio_format and not article.get("audio_url"):
                audio_url = await self._generate_text_to_speech(
                    text=article.get("summary", article.get("title", "")),
                    voice="female",
                    language="en-US",
                    format=audio_format,
                )
                article["audio_url"] = audio_url
                article["has_audio"] = True

                # Update in Firestore
                await self.firestore.update_document(
                    "news_articles", article_id, {"audio_url": audio_url, "has_audio": True}
                )

            return {
                "status": "success",
                "article": article,
            }

        except Exception as e:
            logger.error(f"Error getting news summary: {e}")
            return {"status": "error", "message": str(e)}

    async def search_news(
        self,
        query: str,
        category: Optional[str] = None,
        region: str = "both",
        days_back: int = 7,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Search news articles with filters
        
        Args:
            query: Search query string
            category: Filter by category
            region: "national" or "world"
            days_back: Search last N days
            limit: Maximum results
        
        Returns:
            Dict with matching articles
        """
        try:
            logger.info(f"Searching news: query={query}, category={category}")

            # Build query
            cutoff_date = (datetime.utcnow() - timedelta(days=days_back)).isoformat()

            # Mock search - replace with real Firestore full-text search
            results = await self.firestore.query(
                collection="news_articles",
                filters=[
                    ("published_date", ">=", cutoff_date),
                    ("region", "==", region) if region != "both" else None,
                    ("category", "==", category) if category else None,
                ],
                limit=limit,
            )

            articles = [r for r in results if query.lower() in r.get("title", "").lower()]

            return {
                "status": "success",
                "results_count": len(articles),
                "query": query,
                "articles": articles,
            }

        except Exception as e:
            logger.error(f"Error searching news: {e}")
            return {
                "status": "error",
                "message": str(e),
                "results_count": 0,
                "articles": [],
            }

    async def generate_audio(
        self,
        article_id: str,
        voice: str = "female",
        language: str = "en-US",
    ) -> Dict[str, Any]:
        """
        Generate audio version of news article
        
        Args:
            article_id: ID of the article
            voice: "male" or "female"
            language: Language code (en-US, en-GB, etc.)
        
        Returns:
            Dict with audio URL
        """
        try:
            logger.info(f"Generating audio: article_id={article_id}")

            article = await self.firestore.get_document("news_articles", article_id)
            if not article:
                return {
                    "status": "error",
                    "message": f"Article not found: {article_id}",
                }

            # Generate audio
            audio_url = await self._generate_text_to_speech(
                text=article.get("summary", article.get("title", "")),
                voice=voice,
                language=language,
                format="mp3",
            )

            # Update article
            await self.firestore.update_document(
                "news_articles",
                article_id,
                {
                    "audio_url": audio_url,
                    "has_audio": True,
                    "voice": voice,
                    "audio_language": language,
                },
            )

            return {
                "status": "success",
                "article_id": article_id,
                "audio_url": audio_url,
            }

        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            return {"status": "error", "message": str(e)}

    async def get_weekly_digest(
        self, week_offset: int = 0, region: str = "both"
    ) -> Dict[str, Any]:
        """
        Get organized weekly news digest by category
        
        Args:
            week_offset: 0=this week, -1=last week
            region: "national" or "world"
        
        Returns:
            Dict with digest organized by categories
        """
        try:
            logger.info(f"Getting weekly digest: week_offset={week_offset}, region={region}")

            # Calculate week dates
            today = datetime.utcnow()
            week_num = today.isocalendar()[1]
            year = today.isocalendar()[0]

            if week_offset < 0:
                week_num += week_offset

            # Query by week
            articles = await self.firestore.query(
                collection="news_articles",
                filters=[
                    ("week", "==", week_num),
                    ("year", "==", year),
                    ("region", "==", region) if region != "both" else None,
                ],
            )

            # Organize by category
            digest = {}
            for category in NewsCategory:
                digest[category.value] = [
                    a for a in articles if a.get("category") == category.value
                ]

            return {
                "status": "success",
                "week": week_num,
                "year": year,
                "region": region,
                "digest": digest,
                "total_articles": len(articles),
            }

        except Exception as e:
            logger.error(f"Error getting weekly digest: {e}")
            return {
                "status": "error",
                "message": str(e),
                "digest": {},
            }

    async def create_custom_summary(
        self,
        article_ids: List[str],
        title: str,
        focus_areas: Optional[List[str]] = None,
        generate_audio: bool = False,
    ) -> Dict[str, Any]:
        """
        Create custom news summary from selected articles
        
        Args:
            article_ids: List of article IDs to combine
            title: Title for the summary
            focus_areas: Areas to focus on during synthesis
            generate_audio: Whether to generate audio version
        
        Returns:
            Dict with custom summary
        """
        try:
            logger.info(f"Creating custom summary: title={title}, articles={len(article_ids)}")

            # Fetch articles
            articles = []
            for article_id in article_ids[:100]:  # Limit to 100 articles
                article = await self.firestore.get_document("news_articles", article_id)
                if article:
                    articles.append(article)

            if not articles:
                return {
                    "status": "error",
                    "message": "No articles found",
                }

            # Combine articles
            combined_text = "\n\n".join(
                [f"{a.get('title', '')}: {a.get('summary', '')}" for a in articles]
            )

            # Generate summary via LLM
            summary = await self._summarize_article(
                combined_text,
                focus_areas=focus_areas,
                max_length=1000,
            )

            # Generate audio if requested
            audio_url = None
            if generate_audio:
                audio_url = await self._generate_text_to_speech(
                    text=summary,
                    voice="female",
                    language="en-US",
                    format="mp3",
                )

            # Store custom summary
            custom_summary = {
                "title": title,
                "summary": summary,
                "article_ids": article_ids,
                "focus_areas": focus_areas or [],
                "audio_url": audio_url,
                "created_at": datetime.utcnow().isoformat(),
                "created_by": "news_agent",
                "tags": focus_areas or [],
                "is_public": False,
                "view_count": 0,
            }

            summary_id = await self.firestore.create_document(
                collection="custom_news_summaries",
                data=custom_summary,
            )

            logger.info(f"Created custom summary: {summary_id}")

            return {
                "status": "success",
                "summary_id": summary_id,
                "title": title,
                "summary": summary,
                "audio_url": audio_url,
            }

        except Exception as e:
            logger.error(f"Error creating custom summary: {e}")
            return {"status": "error", "message": str(e)}

    async def get_trending_topics(
        self,
        category: Optional[str] = None,
        region: str = "both",
        period_days: int = 7,
    ) -> Dict[str, Any]:
        """
        Extract trending news topics from recent articles
        
        Args:
            category: Filter by category
            region: "national" or "world"
            period_days: Time period in days
        
        Returns:
            Dict with top 20 trending topics
        """
        try:
            logger.info(f"Getting trending topics: category={category}, region={region}")

            # Query recent articles
            cutoff_date = (
                datetime.utcnow() - timedelta(days=period_days)
            ).isoformat()

            articles = await self.firestore.query(
                collection="news_articles",
                filters=[
                    ("published_date", ">=", cutoff_date),
                    ("region", "==", region) if region != "both" else None,
                    ("category", "==", category) if category else None,
                ],
            )

            # Extract keywords
            all_keywords = []
            for article in articles:
                keywords = article.get("keywords", [])
                all_keywords.extend(keywords)

            # Count frequency
            keyword_counts = {}
            for keyword in all_keywords:
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

            # Top 20
            trending = sorted(
                keyword_counts.items(), key=lambda x: x[1], reverse=True
            )[:20]

            trending_topics = [
                {"topic": topic, "mentions": count} for topic, count in trending
            ]

            return {
                "status": "success",
                "trending_topics": trending_topics,
                "articles_analyzed": len(articles),
                "period_days": period_days,
            }

        except Exception as e:
            logger.error(f"Error getting trending topics: {e}")
            return {
                "status": "error",
                "message": str(e),
                "trending_topics": [],
            }

    # Private helper methods

    async def _fetch_articles_from_sources(
        self,
        categories: Optional[List[str]] = None,
        sources: Optional[List[str]] = None,
        region: str = "both",
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Fetch articles from multiple news sources
        
        Mock implementation - replace with real API calls to:
        - CNN API
        - BBC API
        - Reuters API
        - AP API
        - Al Jazeera API
        - The Guardian API
        - NPR API
        - NYT API
        """
        articles = []
        today = datetime.utcnow()
        week_num = today.isocalendar()[1]
        year = today.isocalendar()[0]

        # Mock articles (in production, call real APIs)
        mock_sources = sources or [s.value for s in NewsSource]
        mock_categories = categories or [c.value for c in NewsCategory]

        article_count = 0
        for source in mock_sources[:len(mock_sources)]:
            for category in mock_categories[:len(mock_categories)]:
                if article_count >= limit:
                    break

                articles.append({
                    "id": f"news_{article_count}",
                    "source": source,
                    "category": category,
                    "region": region,
                    "title": f"Breaking {source.upper()} News: {category.title()} Update",
                    "content": f"Latest {category} news from {source}...",
                    "summary": f"Summary of {category} news",
                    "url": f"https://news.example.com/articles/{article_count}",
                    "published_date": today.isoformat(),
                    "authors": ["News Staff"],
                    "keywords": [category, source, "news", "update"],
                    "reading_time": 5,
                    "has_audio": False,
                    "audio_url": None,
                    "importance_score": 0.8,
                    "week": week_num,
                    "year": year,
                    "is_breaking": article_count % 3 == 0,
                    "engagement_score": 100,
                    "created_at": today.isoformat(),
                    "updated_at": today.isoformat(),
                    "metadata": {"source_priority": 1},
                })
                article_count += 1

        logger.info(f"Fetched {len(articles)} mock articles")
        return articles

    async def _summarize_article(
        self,
        text: str,
        focus_areas: Optional[List[str]] = None,
        max_length: int = 500,
    ) -> str:
        """
        Generate summary of article text using LLM
        
        Args:
            text: Article text to summarize
            focus_areas: Optional areas to focus on
            max_length: Maximum summary length
        
        Returns:
            Summary text
        """
        try:
            prompt = f"Summarize this news article in {max_length} characters:\n\n{text}"
            if focus_areas:
                prompt += f"\n\nFocus on: {', '.join(focus_areas)}"

            summary = await self.llm.generate_summary(
                text=text,
                max_length=max_length,
            )
            return summary or "Summary unavailable"

        except Exception as e:
            logger.warning(f"Error summarizing article: {e}")
            return text[:max_length]

    async def _generate_text_to_speech(
        self,
        text: str,
        voice: str = "female",
        language: str = "en-US",
        format: str = "mp3",
    ) -> Optional[str]:
        """
        Generate audio file from text using Google Cloud TTS
        
        Args:
            text: Text to convert to speech
            voice: "male" or "female"
            language: Language code
            format: "mp3" or "wav"
        
        Returns:
            GCS URL of audio file or None if failed
        """
        try:
            # In production, call Google Cloud Text-to-Speech API
            # This is a mock that returns a placeholder URL

            if not text or len(text.strip()) == 0:
                logger.warning("Empty text for TTS")
                return None

            # Mock URL - in production use actual GCS storage
            audio_url = (
                f"gs://multi-agent-audio/news_{hash(text)[:8]}.{format}"
            )

            logger.info(f"Generated audio: {audio_url}")
            return audio_url

        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            return None


# Factory function for Docker launcher
async def create_and_start_news_server(port: int = 8008) -> NewsAgentMCP:
    """
    Create and start News Agent MCP server
    
    Args:
        port: Port to run server on
    
    Returns:
        Running NewsAgentMCP instance
    """
    try:
        firestore = FirestoreAdapter()
        llm = LLMService()
        pubsub = PubSubService()

        server = NewsAgentMCP(firestore, llm, pubsub)
        await server.initialize()
        await server.start(host="0.0.0.0", port=port)

        logger.info(f"News Agent MCP Server started on port {port}")
        return server

    except Exception as e:
        logger.error(f"Failed to start News Agent MCP Server: {e}")
        raise
