"""
Orchestrator Agent - MCP Integration

Updated to use MCP clients for calling sub-agents
instead of direct Python imports
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging
from datetime import datetime

from mcp_client import MCPClientPool, MCPServerType, initialize_client_pool

logger = logging.getLogger(__name__)


@dataclass
class WorkflowRequest:
    """User request to execute a workflow"""
    request_id: str
    goal: str
    description: str
    priority: str  # "low", "medium", "high", "critical"
    deadline: Optional[str]
    context: Dict[str, Any]
    created_at: str


class OrchestratorAgentMCP:
    """
    Orchestrator Agent using MCP for distributed agent communication
    
    Coordinates all sub-agents and oversees workflow execution via MCP servers:
    - Task Agent (port 8001)
    - Calendar Agent (port 8002)
    - Notes Agent (port 8003)
    - Critic Agent (port 8004)
    - Auditor Agent (port 8005)
    - Event Monitor (port 8006)
    """
    
    def __init__(self, llm_service, pubsub_service):
        """
        Initialize Orchestrator with MCP clients
        
        Args:
            llm_service: LLM service for planning and analysis
            pubsub_service: Pub/Sub service for event publishing
        """
        self.llm_service = llm_service
        self.pubsub = pubsub_service
        self.workflows: Dict[str, Dict] = {}
        self.client_pool: Optional[MCPClientPool] = None
        
        logger.info("Initialized OrchestratorAgentMCP")
    
    async def initialize(self) -> None:
        """Initialize MCP client pool"""
        self.client_pool = initialize_client_pool()
        logger.info("Orchestrator MCP client pool initialized")
    
    async def shutdown(self) -> None:
        """Shutdown and cleanup"""
        if self.client_pool:
            await self.client_pool.close_all()
    
    # ========================================================================
    # Task Management (Task Agent via MCP)
    # ========================================================================
    
    async def create_task(self, title: str, project_id: str, **kwargs) -> Dict[str, Any]:
        """
        Create a task via Task MCP server
        
        Args:
            title: Task title
            project_id: Project ID
            **kwargs: Additional arguments
            
        Returns:
            Created task
        """
        logger.info(f"Creating task: {title}")
        
        result = await self.client_pool.call_tool(
            MCPServerType.TASK,
            "create_task",
            {
                "title": title,
                "project_id": project_id,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    async def get_tasks(self, project_id: str, **kwargs) -> List[Dict[str, Any]]:
        """Get tasks from Task MCP server"""
        result = await self.client_pool.call_tool(
            MCPServerType.TASK,
            "get_tasks",
            {"project_id": project_id, **kwargs}
        )
        
        return result.get("result", {}).get("tasks", [])
    
    async def update_task(self, task_id: str, **updates) -> Dict[str, Any]:
        """Update a task via Task MCP server"""
        result = await self.client_pool.call_tool(
            MCPServerType.TASK,
            "update_task",
            {"task_id": task_id, **updates}
        )
        
        return result.get("result", {})
    
    async def complete_task(self, task_id: str, notes: str = "") -> Dict[str, Any]:
        """Complete a task via Task MCP server"""
        result = await self.client_pool.call_tool(
            MCPServerType.TASK,
            "complete_task",
            {"task_id": task_id, "notes": notes}
        )
        
        return result.get("result", {})
    
    # ========================================================================
    # Calendar Management (Calendar Agent via MCP)
    # ========================================================================
    
    async def create_event(self, title: str, start_time: str, end_time: str,
                          **kwargs) -> Dict[str, Any]:
        """Create a calendar event via Calendar MCP server"""
        logger.info(f"Creating calendar event: {title}")
        
        result = await self.client_pool.call_tool(
            MCPServerType.CALENDAR,
            "create_event",
            {
                "title": title,
                "start_time": start_time,
                "end_time": end_time,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    async def list_events(self, start_date: str, end_date: str, **kwargs) -> List[Dict[str, Any]]:
        """List calendar events"""
        result = await self.client_pool.call_tool(
            MCPServerType.CALENDAR,
            "list_events",
            {"start_date": start_date, "end_date": end_date, **kwargs}
        )
        
        return result.get("result", {}).get("events", [])
    
    async def find_available_slots(self, start_date: str, end_date: str,
                                   duration_minutes: int, **kwargs) -> List[Dict[str, Any]]:
        """Find available time slots"""
        result = await self.client_pool.call_tool(
            MCPServerType.CALENDAR,
            "find_available_slots",
            {
                "start_date": start_date,
                "end_date": end_date,
                "duration_minutes": duration_minutes,
                **kwargs
            }
        )
        
        return result.get("result", {}).get("available_slots", [])
    
    # ========================================================================
    # Notes/Knowledge Management (Notes Agent via MCP)
    # ========================================================================
    
    async def create_note(self, title: str, content: str, **kwargs) -> Dict[str, Any]:
        """Create a note via Notes MCP server"""
        logger.info(f"Creating note: {title}")
        
        result = await self.client_pool.call_tool(
            MCPServerType.NOTES,
            "create_note",
            {
                "title": title,
                "content": content,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    async def search_notes(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Search notes"""
        result = await self.client_pool.call_tool(
            MCPServerType.NOTES,
            "search_notes",
            {"query": query, **kwargs}
        )
        
        return result.get("result", {}).get("results", [])
    
    async def get_related_notes(self, note_id: str, **kwargs) -> List[Dict[str, Any]]:
        """Get related notes"""
        result = await self.client_pool.call_tool(
            MCPServerType.NOTES,
            "get_related_notes",
            {"note_id": note_id, **kwargs}
        )
        
        return result.get("result", {}).get("notes", [])
    
    # ========================================================================
    # Code Review (Critic Agent via MCP)
    # ========================================================================
    
    async def review_code(self, code: str, language: str, **kwargs) -> Dict[str, Any]:
        """
        Review code quality via Critic MCP server
        
        Args:
            code: Code to review
            language: Programming language
            **kwargs: Additional options
            
        Returns:
            Code review results
        """
        logger.info(f"Reviewing code ({language})")
        
        result = await self.client_pool.call_tool(
            MCPServerType.CRITIC,
            "review_code",
            {
                "code": code,
                "language": language,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    async def analyze_performance(self, code: str, language: str, **kwargs) -> Dict[str, Any]:
        """Analyze code performance"""
        result = await self.client_pool.call_tool(
            MCPServerType.CRITIC,
            "analyze_performance",
            {
                "code": code,
                "language": language,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    async def check_security(self, code: str, language: str, **kwargs) -> Dict[str, Any]:
        """Check code security"""
        result = await self.client_pool.call_tool(
            MCPServerType.CRITIC,
            "check_security",
            {
                "code": code,
                "language": language,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    # ========================================================================
    # Compliance & Audit (Auditor Agent via MCP)
    # ========================================================================
    
    async def audit_activity(self, start_time: str, end_time: str,
                            **kwargs) -> Dict[str, Any]:
        """Audit system activity"""
        result = await self.client_pool.call_tool(
            MCPServerType.AUDITOR,
            "audit_activity",
            {
                "start_time": start_time,
                "end_time": end_time,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    async def check_compliance(self, policy: str, **kwargs) -> Dict[str, Any]:
        """Check policy compliance"""
        result = await self.client_pool.call_tool(
            MCPServerType.AUDITOR,
            "check_compliance",
            {
                "policy": policy,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    async def generate_report(self, report_type: str, **kwargs) -> Dict[str, Any]:
        """Generate audit report"""
        result = await self.client_pool.call_tool(
            MCPServerType.AUDITOR,
            "generate_report",
            {
                "report_type": report_type,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    # ========================================================================
    # Event Monitoring (Event Monitor via MCP)
    # ========================================================================
    
    async def publish_event(self, topic: str, event_type: str, data: Dict[str, Any],
                           **kwargs) -> Dict[str, Any]:
        """Publish event via Event Monitor MCP server"""
        result = await self.client_pool.call_tool(
            MCPServerType.EVENT_MONITOR,
            "publish_event",
            {
                "topic": topic,
                "event_type": event_type,
                "data": data,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    async def monitor_health(self, **kwargs) -> Dict[str, Any]:
        """Monitor system health"""
        result = await self.client_pool.call_tool(
            MCPServerType.EVENT_MONITOR,
            "monitor_health",
            kwargs
        )
        
        return result.get("result", {})
    
    # ========================================================================
    # Research & Knowledge (Research Agent via MCP)
    # ========================================================================
    
    async def fetch_weekly_highlights(self, categories: Optional[List[str]] = None,
                                     sources: Optional[List[str]] = None,
                                     max_articles: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Fetch and summarize latest research articles for the week
        
        Args:
            categories: Research categories (e.g., AI, ML, robotics)
            sources: Specific sources to fetch from
            max_articles: Maximum number of articles to fetch
            **kwargs: Additional options
            
        Returns:
            Research articles with summaries
        """
        logger.info(f"Fetching weekly research highlights ({max_articles} articles)")
        
        result = await self.client_pool.call_tool(
            MCPServerType.RESEARCH,
            "fetch_weekly_highlights",
            {
                "categories": categories,
                "sources": sources,
                "max_articles": max_articles,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    async def get_article_summary(self, article_id: str, audio_format: str = "mp3",
                                 **kwargs) -> Dict[str, Any]:
        """
        Get summary of a specific research article with optional audio
        
        Args:
            article_id: Article ID from research database
            audio_format: Audio format preference (mp3, wav)
            **kwargs: Additional options
            
        Returns:
            Article summary with optional audio URL
        """
        logger.info(f"Getting summary for article: {article_id}")
        
        result = await self.client_pool.call_tool(
            MCPServerType.RESEARCH,
            "get_article_summary",
            {
                "article_id": article_id,
                "audio_format": audio_format,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    async def search_articles(self, query: str, category: Optional[str] = None,
                             days_back: int = 7, limit: int = 10,
                             **kwargs) -> Dict[str, Any]:
        """
        Search research articles by keyword or topic
        
        Args:
            query: Search query
            category: Filter by research category
            days_back: Search articles from last N days
            limit: Number of results
            **kwargs: Additional options
            
        Returns:
            Search results with matching articles
        """
        logger.info(f"Searching articles for: {query}")
        
        result = await self.client_pool.call_tool(
            MCPServerType.RESEARCH,
            "search_articles",
            {
                "query": query,
                "category": category,
                "days_back": days_back,
                "limit": limit,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    async def generate_audio(self, article_id: str, voice: str = "female",
                           language: str = "en-US", **kwargs) -> Dict[str, Any]:
        """
        Generate audio version of an article
        
        Args:
            article_id: Article ID
            voice: Voice preference (male, female)
            language: Language code (e.g., en-US)
            **kwargs: Additional options
            
        Returns:
            Audio generation result with URL
        """
        logger.info(f"Generating audio for article: {article_id}")
        
        result = await self.client_pool.call_tool(
            MCPServerType.RESEARCH,
            "generate_audio",
            {
                "article_id": article_id,
                "voice": voice,
                "language": language,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    async def get_weekly_digest(self, week_offset: int = 0, **kwargs) -> Dict[str, Any]:
        """
        Get complete weekly research digest
        
        Args:
            week_offset: Week offset (0=current, -1=last week)
            **kwargs: Additional options
            
        Returns:
            Weekly research digest organized by category
        """
        logger.info(f"Getting weekly digest (week offset: {week_offset})")
        
        result = await self.client_pool.call_tool(
            MCPServerType.RESEARCH,
            "get_weekly_digest",
            {
                "week_offset": week_offset,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    async def create_custom_summary(self, article_ids: List[str], title: str,
                                   focus_areas: Optional[List[str]] = None,
                                   **kwargs) -> Dict[str, Any]:
        """
        Create a custom summary from multiple articles
        
        Args:
            article_ids: List of article IDs to include
            title: Title for the custom summary
            focus_areas: Specific areas to focus on
            **kwargs: Additional options
            
        Returns:
            Custom summary with audio
        """
        logger.info(f"Creating custom summary: {title} ({len(article_ids)} articles)")
        
        result = await self.client_pool.call_tool(
            MCPServerType.RESEARCH,
            "create_custom_summary",
            {
                "article_ids": article_ids,
                "title": title,
                "focus_areas": focus_areas,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    async def get_trending_topics(self, category: Optional[str] = None,
                                 period_days: int = 7, **kwargs) -> Dict[str, Any]:
        """
        Get trending topics in research
        
        Args:
            category: Specific research category to analyze
            period_days: Analysis period in days
            **kwargs: Additional options
            
        Returns:
            List of trending topics with mention counts
        """
        logger.info(f"Getting trending topics for last {period_days} days")
        
        result = await self.client_pool.call_tool(
            MCPServerType.RESEARCH,
            "get_trending_topics",
            {
                "category": category,
                "period_days": period_days,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    # ========================================================================
    # News & Headlines (News Agent via MCP)
    # ========================================================================
    
    async def fetch_weekly_news(self, categories: Optional[List[str]] = None,
                               sources: Optional[List[str]] = None,
                               region: str = "both",
                               max_articles: int = 20, **kwargs) -> Dict[str, Any]:
        """
        Fetch and summarize latest news for the week
        
        Args:
            categories: News categories (politics, business, tech, etc.)
            sources: Specific news sources to fetch from
            region: "national", "world", or "both"
            max_articles: Maximum number of articles to fetch
            **kwargs: Additional options
            
        Returns:
            News articles with summaries
        """
        logger.info(f"Fetching weekly news ({max_articles} articles, region={region})")
        
        result = await self.client_pool.call_tool(
            MCPServerType.NEWS,
            "fetch_weekly_headlines",
            {
                "categories": categories,
                "sources": sources,
                "region": region,
                "max_articles": max_articles,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    async def get_news_summary(self, article_id: str, audio_format: str = "mp3",
                              **kwargs) -> Dict[str, Any]:
        """
        Get summary of a specific news article with optional audio
        
        Args:
            article_id: News article ID
            audio_format: Audio format preference (mp3, wav)
            **kwargs: Additional options
            
        Returns:
            Article summary with optional audio URL
        """
        logger.info(f"Getting news summary for article: {article_id}")
        
        result = await self.client_pool.call_tool(
            MCPServerType.NEWS,
            "get_news_summary",
            {
                "article_id": article_id,
                "audio_format": audio_format,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    async def search_news(self, query: str, category: Optional[str] = None,
                         region: str = "both", days_back: int = 7,
                         limit: int = 20, **kwargs) -> Dict[str, Any]:
        """
        Search news articles by keyword
        
        Args:
            query: Search query
            category: Filter by news category
            region: "national", "world", or "both"
            days_back: Search articles from last N days
            limit: Number of results
            **kwargs: Additional options
            
        Returns:
            Search results with matching articles
        """
        logger.info(f"Searching news for: {query} (region={region})")
        
        result = await self.client_pool.call_tool(
            MCPServerType.NEWS,
            "search_news",
            {
                "query": query,
                "category": category,
                "region": region,
                "days_back": days_back,
                "limit": limit,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    async def generate_news_audio(self, article_id: str, voice: str = "female",
                                 language: str = "en-US", **kwargs) -> Dict[str, Any]:
        """
        Generate audio version of a news article
        
        Args:
            article_id: News article ID
            voice: Voice preference (male, female)
            language: Language code (e.g., en-US)
            **kwargs: Additional options
            
        Returns:
            Audio generation result with URL
        """
        logger.info(f"Generating audio for news article: {article_id}")
        
        result = await self.client_pool.call_tool(
            MCPServerType.NEWS,
            "generate_audio",
            {
                "article_id": article_id,
                "voice": voice,
                "language": language,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    async def get_news_digest(self, week_offset: int = 0, region: str = "both",
                             **kwargs) -> Dict[str, Any]:
        """
        Get complete weekly news digest
        
        Args:
            week_offset: Week offset (0=current, -1=last week)
            region: "national", "world", or "both"
            **kwargs: Additional options
            
        Returns:
            Weekly news digest organized by category
        """
        logger.info(f"Getting news digest (week offset: {week_offset}, region={region})")
        
        result = await self.client_pool.call_tool(
            MCPServerType.NEWS,
            "get_weekly_digest",
            {
                "week_offset": week_offset,
                "region": region,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    async def create_news_summary(self, article_ids: List[str], title: str,
                                 focus_areas: Optional[List[str]] = None,
                                 **kwargs) -> Dict[str, Any]:
        """
        Create a custom news summary from selected articles
        
        Args:
            article_ids: List of article IDs to include
            title: Title for the custom summary
            focus_areas: Specific areas to focus on
            **kwargs: Additional options
            
        Returns:
            Custom news summary with optional audio
        """
        logger.info(f"Creating news summary: {title} ({len(article_ids)} articles)")
        
        result = await self.client_pool.call_tool(
            MCPServerType.NEWS,
            "create_custom_summary",
            {
                "article_ids": article_ids,
                "title": title,
                "focus_areas": focus_areas,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    async def get_news_trends(self, category: Optional[str] = None,
                             region: str = "both", period_days: int = 7,
                             **kwargs) -> Dict[str, Any]:
        """
        Get trending news topics
        
        Args:
            category: Specific news category to analyze
            region: "national", "world", or "both"
            period_days: Analysis period in days
            **kwargs: Additional options
            
        Returns:
            List of trending news topics with mention counts
        """
        logger.info(f"Getting news trends for last {period_days} days (region={region})")
        
        result = await self.client_pool.call_tool(
            MCPServerType.NEWS,
            "get_trending_topics",
            {
                "category": category,
                "region": region,
                "period_days": period_days,
                **kwargs
            }
        )
        
        return result.get("result", {})
    
    
    # ========================================================================
    # Workflow Management
    # ========================================================================
    
    async def process_user_request(self, request: WorkflowRequest) -> Dict[str, Any]:
        """
        Main entry point: Process a user request using MCP agents
        
        Args:
            request: WorkflowRequest
            
        Returns:
            Workflow result
        """
        logger.info(f"🎯 Orchestrator processing request: {request.goal}")
        
        workflow_id = request.request_id
        self.workflows[workflow_id] = {
            "request": request,
            "status": "planning",
            "started_at": datetime.now().isoformat()
        }
        
        try:
            # Publish workflow started event
            await self.publish_event(
                topic="workflows",
                event_type="workflow_started",
                data={
                    "workflow_id": workflow_id,
                    "goal": request.goal,
                    "priority": request.priority
                }
            )
            
            # Generate execution plan using LLM
            execution_plan = await self._generate_execution_plan(request)
            self.workflows[workflow_id]["plan"] = execution_plan
            
            logger.info(f"✅ Generated execution plan for {workflow_id}")
            
            # Execute the plan with MCP agents
            self.workflows[workflow_id]["status"] = "executing"
            result = await self._execute_plan(workflow_id, execution_plan)
            
            # Publish workflow completed event
            await self.publish_event(
                topic="workflows",
                event_type="workflow_completed",
                data={
                    "workflow_id": workflow_id,
                    "status": "success"
                }
            )
            
            self.workflows[workflow_id]["status"] = "completed"
            self.workflows[workflow_id]["result"] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing request {workflow_id}: {e}")
            self.workflows[workflow_id]["status"] = "failed"
            self.workflows[workflow_id]["error"] = str(e)
            
            # Publish workflow failed event
            await self.publish_event(
                topic="workflows",
                event_type="workflow_failed",
                data={
                    "workflow_id": workflow_id,
                    "error": str(e)
                }
            )
            
            raise
    
    async def _generate_execution_plan(self, request: WorkflowRequest) -> List[Dict[str, Any]]:
        """Generate execution plan from request using LLM"""
        # This would call the LLM service to break down the goal into steps
        logger.info(f"Generating execution plan for: {request.goal}")
        
        # Example: Return a simple plan structure
        return [
            {
                "step": 1,
                "action": "analyze_goal",
                "description": f"Understand the goal: {request.goal}"
            },
            {
                "step": 2,
                "action": "execute",
                "description": "Execute planned actions"
            }
        ]
    
    async def _execute_plan(self, workflow_id: str, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute the workflow plan"""
        logger.info(f"Executing plan with {len(plan)} steps")
        
        results = []
        for step in plan:
            logger.info(f"Executing step {step['step']}: {step['description']}")
            results.append({
                "step": step["step"],
                "status": "completed",
                "result": "Step executed successfully"
            })
        
        return {
            "workflow_id": workflow_id,
            "status": "success",
            "steps_executed": len(plan),
            "results": results
        }
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow status"""
        return self.workflows.get(workflow_id, {"status": "not_found"})


# Example usage
async def example_usage():
    """Example of using the Orchestrator with MCP"""
    
    # Initialize orchestrator
    from backend.services.llm_service import LLMService
    from backend.services.pubsub_service import PubSubService
    
    llm_service = LLMService()
    pubsub_service = PubSubService()
    
    orchestrator = OrchestratorAgentMCP(llm_service, pubsub_service)
    await orchestrator.initialize()
    
    try:
        # Create a task via Task MCP server
        task = await orchestrator.create_task(
            title="Build API",
            project_id="proj_123",
            priority="high"
        )
        print(f"Created task: {task}")
        
        # Create a calendar event via Calendar MCP server
        event = await orchestrator.create_event(
            title="Team standup",
            start_time="2024-01-15T10:00:00Z",
            end_time="2024-01-15T10:30:00Z"
        )
        print(f"Created event: {event}")
        
        # Review code via Critic MCP server
        review = await orchestrator.review_code(
            code="def hello(): print('world')",
            language="python"
        )
        print(f"Code review: {review}")
        
        # Monitor health
        health = await orchestrator.monitor_health()
        print(f"System health: {health}")
        
    finally:
        await orchestrator.shutdown()


if __name__ == "__main__":
    asyncio.run(example_usage())
