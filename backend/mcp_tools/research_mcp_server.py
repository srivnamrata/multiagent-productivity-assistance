"""
Research Agent MCP Server
Fetches top AI, ML, and robotics articles from various sources,
generates summaries, and provides text/audio options
"""

from enum import Enum
from typing import Optional
from datetime import datetime, timedelta
import asyncio
import logging

from backend.mcp_tools.base_mcp_server import BaseMCPServer
from backend.services.llm_service import LLMService
from backend.services.firestore_adapter import FirestoreAdapter
from backend.services.pubsub_service import PubSubService

logger = logging.getLogger(__name__)


class ResearchSource(str, Enum):
    """Supported research sources"""
    TOWARDS_DATA_SCIENCE = "towards_data_science"
    ARXIV = "arxiv"
    MEDIUM = "medium"
    HACKER_NEWS = "hacker_news"
    REDDIT_ML = "reddit_ml"
    GOOGLE_RESEARCH = "google_research"


class ResearchCategory(str, Enum):
    """Research categories"""
    AI = "artificial_intelligence"
    ML = "machine_learning"
    ROBOTICS = "robotics"
    DEEP_LEARNING = "deep_learning"
    NLP = "nlp"
    COMPUTER_VISION = "computer_vision"
    REINFORCEMENT_LEARNING = "reinforcement_learning"
    DATA_SCIENCE = "data_science"


class ResearchAgentMCP(BaseMCPServer):
    """Research Agent MCP Server"""

    def __init__(self, port: int = 8007):
        super().__init__(
            name="ResearchAgent",
            description="Fetches and summarizes latest AI/ML/Robotics research articles",
            port=port
        )
        self.llm_service = None
        self.firestore = None
        self.pubsub = None

    async def initialize(self):
        """Initialize services"""
        await super().initialize()
        self.llm_service = LLMService()
        self.firestore = FirestoreAdapter()
        self.pubsub = PubSubService()

        # Register MCP tools
        self.register_tool(
            name="fetch_weekly_highlights",
            description="Fetch and summarize latest research from all sources",
            handler=self.fetch_weekly_highlights,
            input_schema={
                "type": "object",
                "properties": {
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Research categories (ai, ml, robotics, etc.)"
                    },
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific sources to fetch from"
                    },
                    "max_articles": {
                        "type": "integer",
                        "description": "Maximum articles to fetch (default: 10)"
                    }
                }
            }
        )

        self.register_tool(
            name="get_article_summary",
            description="Get summary of a specific article",
            handler=self.get_article_summary,
            input_schema={
                "type": "object",
                "properties": {
                    "article_id": {
                        "type": "string",
                        "description": "Article ID from research database"
                    },
                    "audio_format": {
                        "type": "string",
                        "enum": ["mp3", "wav"],
                        "description": "Audio format preference"
                    }
                },
                "required": ["article_id"]
            }
        )

        self.register_tool(
            name="search_articles",
            description="Search articles by keyword or topic",
            handler=self.search_articles,
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by category"
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Search articles from last N days (default: 7)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results (default: 10)"
                    }
                },
                "required": ["query"]
            }
        )

        self.register_tool(
            name="generate_audio",
            description="Generate audio version of article summary",
            handler=self.generate_audio,
            input_schema={
                "type": "object",
                "properties": {
                    "article_id": {
                        "type": "string",
                        "description": "Article ID"
                    },
                    "voice": {
                        "type": "string",
                        "enum": ["male", "female"],
                        "description": "Voice preference"
                    },
                    "language": {
                        "type": "string",
                        "description": "Language code (e.g., 'en-US')"
                    }
                },
                "required": ["article_id"]
            }
        )

        self.register_tool(
            name="get_weekly_digest",
            description="Get complete weekly research digest",
            handler=self.get_weekly_digest,
            input_schema={
                "type": "object",
                "properties": {
                    "week_offset": {
                        "type": "integer",
                        "description": "Week offset (0=current, -1=last week, etc.)"
                    }
                }
            }
        )

        self.register_tool(
            name="create_custom_summary",
            description="Create custom summary from multiple articles",
            handler=self.create_custom_summary,
            input_schema={
                "type": "object",
                "properties": {
                    "article_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Article IDs to include"
                    },
                    "title": {
                        "type": "string",
                        "description": "Custom summary title"
                    },
                    "focus_areas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific areas to focus on"
                    }
                },
                "required": ["article_ids", "title"]
            }
        )

        self.register_tool(
            name="get_trending_topics",
            description="Get trending topics in AI/ML/Robotics",
            handler=self.get_trending_topics,
            input_schema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Specific category to analyze"
                    },
                    "period_days": {
                        "type": "integer",
                        "description": "Analysis period in days (default: 7)"
                    }
                }
            }
        )

        logger.info("Research Agent MCP initialized")

    async def fetch_weekly_highlights(
        self,
        categories: Optional[list] = None,
        sources: Optional[list] = None,
        max_articles: int = 10
    ) -> dict:
        """Fetch and summarize top articles from the week"""
        try:
            if categories is None:
                categories = [c.value for c in ResearchCategory]
            if sources is None:
                sources = [s.value for s in ResearchSource]

            logger.info(f"Fetching highlights for {len(categories)} categories from {len(sources)} sources")

            # Mock implementation - in production, would call actual APIs
            articles = await self._fetch_articles_from_sources(
                categories=categories,
                sources=sources,
                limit=max_articles
            )

            # Summarize articles
            summaries = []
            for article in articles:
                summary = await self._summarize_article(article)
                summaries.append({
                    "id": article.get("id"),
                    "title": article.get("title"),
                    "source": article.get("source"),
                    "summary": summary,
                    "url": article.get("url"),
                    "published_date": article.get("published_date"),
                    "category": article.get("category")
                })

            # Store in Firestore
            for summary in summaries:
                await self.firestore.create_document(
                    collection="research_articles",
                    data={
                        **summary,
                        "created_at": datetime.utcnow(),
                        "week": self._get_week_number(),
                        "has_audio": False
                    }
                )

            # Publish event
            await self.pubsub.publish("research-articles-fetched", {
                "count": len(summaries),
                "categories": categories,
                "sources": sources,
                "timestamp": datetime.utcnow().isoformat()
            })

            return {
                "status": "success",
                "articles_fetched": len(summaries),
                "articles": summaries
            }

        except Exception as e:
            logger.error(f"Error fetching highlights: {e}")
            return {"status": "error", "message": str(e)}

    async def get_article_summary(
        self,
        article_id: str,
        audio_format: str = "mp3"
    ) -> dict:
        """Get summary of specific article with optional audio"""
        try:
            # Fetch from Firestore
            doc = await self.firestore.get_document(
                collection="research_articles",
                doc_id=article_id
            )

            if not doc:
                return {"status": "error", "message": "Article not found"}

            result = {
                "id": article_id,
                "title": doc.get("title"),
                "source": doc.get("source"),
                "summary": doc.get("summary"),
                "url": doc.get("url"),
                "published_date": doc.get("published_date"),
                "category": doc.get("category")
            }

            # Generate audio if requested and not already generated
            if not doc.get("has_audio"):
                audio_url = await self._generate_text_to_speech(
                    text=doc.get("summary"),
                    article_id=article_id,
                    format=audio_format
                )
                result["audio_url"] = audio_url

                # Update document
                await self.firestore.update_document(
                    collection="research_articles",
                    doc_id=article_id,
                    data={"has_audio": True, "audio_url": audio_url}
                )
            else:
                result["audio_url"] = doc.get("audio_url")

            return {
                "status": "success",
                "article": result
            }

        except Exception as e:
            logger.error(f"Error getting article summary: {e}")
            return {"status": "error", "message": str(e)}

    async def search_articles(
        self,
        query: str,
        category: Optional[str] = None,
        days_back: int = 7,
        limit: int = 10
    ) -> dict:
        """Search articles by keyword"""
        try:
            logger.info(f"Searching articles for query: {query}")

            # Build Firestore query
            filters = {
                "published_date": {
                    "$gte": datetime.utcnow() - timedelta(days=days_back)
                }
            }

            if category:
                filters["category"] = category

            # Search in Firestore
            results = await self.firestore.search_documents(
                collection="research_articles",
                query=query,
                filters=filters,
                limit=limit
            )

            return {
                "status": "success",
                "query": query,
                "results_count": len(results),
                "articles": results
            }

        except Exception as e:
            logger.error(f"Error searching articles: {e}")
            return {"status": "error", "message": str(e)}

    async def generate_audio(
        self,
        article_id: str,
        voice: str = "female",
        language: str = "en-US"
    ) -> dict:
        """Generate audio version of article"""
        try:
            # Fetch article
            doc = await self.firestore.get_document(
                collection="research_articles",
                doc_id=article_id
            )

            if not doc:
                return {"status": "error", "message": "Article not found"}

            # Generate audio
            audio_url = await self._generate_text_to_speech(
                text=doc.get("summary"),
                article_id=article_id,
                voice=voice,
                language=language
            )

            # Update document
            await self.firestore.update_document(
                collection="research_articles",
                doc_id=article_id,
                data={
                    "has_audio": True,
                    "audio_url": audio_url,
                    "voice": voice,
                    "audio_language": language
                }
            )

            return {
                "status": "success",
                "article_id": article_id,
                "audio_url": audio_url,
                "voice": voice,
                "language": language
            }

        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            return {"status": "error", "message": str(e)}

    async def get_weekly_digest(self, week_offset: int = 0) -> dict:
        """Get complete weekly research digest"""
        try:
            # Calculate week number
            target_date = datetime.utcnow() - timedelta(weeks=week_offset)
            week_number = target_date.isocalendar()[1]
            year = target_date.isocalendar()[0]

            logger.info(f"Fetching digest for week {week_number}/{year}")

            # Query articles from that week
            articles = await self.firestore.query_documents(
                collection="research_articles",
                filters={"week": week_number, "year": year}
            )

            # Organize by category
            by_category = {}
            for article in articles:
                cat = article.get("category", "uncategorized")
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(article)

            # Generate digest summary
            digest = {
                "week": week_number,
                "year": year,
                "total_articles": len(articles),
                "categories": by_category,
                "generated_at": datetime.utcnow().isoformat()
            }

            return {
                "status": "success",
                "digest": digest
            }

        except Exception as e:
            logger.error(f"Error getting weekly digest: {e}")
            return {"status": "error", "message": str(e)}

    async def create_custom_summary(
        self,
        article_ids: list,
        title: str,
        focus_areas: Optional[list] = None
    ) -> dict:
        """Create custom summary from multiple articles"""
        try:
            # Fetch articles
            articles = []
            for article_id in article_ids:
                doc = await self.firestore.get_document(
                    collection="research_articles",
                    doc_id=article_id
                )
                if doc:
                    articles.append(doc)

            if not articles:
                return {"status": "error", "message": "No articles found"}

            # Create combined text
            combined_text = f"Title: {title}\n\n"
            combined_text += "Articles:\n"
            for article in articles:
                combined_text += f"\n{article.get('title')}\n{article.get('summary')}\n"

            # Generate custom summary
            custom_summary = await self.llm_service.generate_summary(
                text=combined_text,
                max_length=1000
            )

            # Generate audio
            audio_url = await self._generate_text_to_speech(
                text=custom_summary,
                article_id=None
            )

            # Store custom summary
            summary_id = await self.firestore.create_document(
                collection="custom_research_summaries",
                data={
                    "title": title,
                    "summary": custom_summary,
                    "article_ids": article_ids,
                    "focus_areas": focus_areas or [],
                    "audio_url": audio_url,
                    "created_at": datetime.utcnow()
                }
            )

            return {
                "status": "success",
                "summary_id": summary_id,
                "title": title,
                "summary": custom_summary,
                "audio_url": audio_url
            }

        except Exception as e:
            logger.error(f"Error creating custom summary: {e}")
            return {"status": "error", "message": str(e)}

    async def get_trending_topics(
        self,
        category: Optional[str] = None,
        period_days: int = 7
    ) -> dict:
        """Get trending topics in research"""
        try:
            # Query articles from period
            cutoff_date = datetime.utcnow() - timedelta(days=period_days)
            articles = await self.firestore.query_documents(
                collection="research_articles",
                filters={"published_date": {"$gte": cutoff_date}}
            )

            if category:
                articles = [a for a in articles if a.get("category") == category]

            # Extract keywords/topics from summaries
            topics = {}
            for article in articles:
                summary = article.get("summary", "")
                # Simple keyword extraction - in production use NLP
                words = summary.split()
                for word in words:
                    if len(word) > 5:  # Filter short words
                        topics[word] = topics.get(word, 0) + 1

            # Sort by frequency
            trending = sorted(
                topics.items(),
                key=lambda x: x[1],
                reverse=True
            )[:20]

            return {
                "status": "success",
                "period_days": period_days,
                "category": category or "all",
                "article_count": len(articles),
                "trending_topics": [{"topic": t[0], "mentions": t[1]} for t in trending]
            }

        except Exception as e:
            logger.error(f"Error getting trending topics: {e}")
            return {"status": "error", "message": str(e)}

    # Private helper methods

    async def _fetch_articles_from_sources(
        self,
        categories: list,
        sources: list,
        limit: int
    ) -> list:
        """Fetch articles from various sources"""
        articles = []

        # In production, implement actual API calls to:
        # - Towards Data Science (Medium API)
        # - ArXiv (ArXiv API)
        # - Reddit (PRAW)
        # - Hacker News (HN API)
        # - Google Research Blog (RSS)

        # Mock data for demonstration
        mock_articles = [
            {
                "id": f"article_{i}",
                "title": f"Sample AI Article {i}",
                "source": "towards_data_science",
                "url": f"https://example.com/article-{i}",
                "published_date": datetime.utcnow() - timedelta(days=i),
                "category": "artificial_intelligence",
                "content": f"This is a sample article about AI topic {i}..."
            }
            for i in range(min(limit, 5))
        ]

        return mock_articles

    async def _summarize_article(self, article: dict) -> str:
        """Summarize article using LLM"""
        try:
            content = article.get("content", "")
            if not content:
                return "No content available for summarization"

            summary = await self.llm_service.generate_summary(
                text=content,
                max_length=500
            )
            return summary
        except Exception as e:
            logger.error(f"Error summarizing article: {e}")
            return "Summary generation failed"

    async def _generate_text_to_speech(
        self,
        text: str,
        article_id: Optional[str] = None,
        voice: str = "female",
        format: str = "mp3",
        language: str = "en-US"
    ) -> str:
        """Generate audio from text using Google Cloud TTS"""
        try:
            # In production, use Google Cloud Text-to-Speech API
            # For now, return mock URL
            filename = f"research_{article_id or 'custom'}_{voice}.{format}"
            audio_url = f"gs://multi-agent-storage/audio/{filename}"
            logger.info(f"Generated audio URL: {audio_url}")
            return audio_url
        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            raise

    def _get_week_number(self) -> int:
        """Get current ISO week number"""
        return datetime.utcnow().isocalendar()[1]


async def create_and_start_research_server(port: int = 8007):
    """Factory function to create and start research server"""
    server = ResearchAgentMCP(port=port)
    await server.initialize()
    await server.start()
    return server


if __name__ == "__main__":
    import asyncio

    async def main():
        server = await create_and_start_research_server()
        logger.info(f"Research Agent MCP Server running on port 8007")
        await asyncio.Event().wait()

    asyncio.run(main())
