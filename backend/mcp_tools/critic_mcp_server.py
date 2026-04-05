"""
Critic Agent MCP Server

Wraps the CriticAgent in an MCP server for distributed processing
Exposes code review and optimization operations as MCP tools
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any

from base_mcp_server import BaseMCPServer, MCPServerConfig
from utils import log_operation

# Import the existing CriticAgent
import sys
sys.path.insert(0, '../agents')
from critic_agent import CriticAgent

logger = logging.getLogger(__name__)


class CriticMCPServer(BaseMCPServer):
    """
    MCP server for Critic Agent
    Provides distributed code review and optimization capabilities
    """

    def __init__(self, config: Optional[MCPServerConfig] = None):
        """Initialize Critic MCP server"""
        if config is None:
            config = MCPServerConfig(
                name="Critic MCP Server",
                description="Code review and optimization system",
                version="1.0.0",
                port=8004
            )
        
        super().__init__(config)
        self.agent: Optional[CriticAgent] = None

    async def initialize(self) -> None:
        """Initialize critic agent and register tools"""
        logger.info("Initializing Critic Agent...")
        
        # Initialize the agent
        self.agent = CriticAgent()
        
        # Register tools that expose agent methods
        await self._register_tools()
        
        logger.info("Critic Agent initialized successfully")

    async def _register_tools(self) -> None:
        """Register code review tools"""
        
        # Review Code
        self.register_tool(
            name="review_code",
            description="Review code for quality and best practices",
            handler=self._review_code,
            input_schema={
                "properties": {
                    "code": {"type": "string", "description": "Code to review"},
                    "language": {"type": "string", "description": "Programming language"},
                    "style_guide": {"type": "string", "description": "Style guide to follow"}
                }
            },
            required_fields=["code", "language"]
        )
        
        # Analyze Performance
        self.register_tool(
            name="analyze_performance",
            description="Analyze code for performance issues",
            handler=self._analyze_performance,
            input_schema={
                "properties": {
                    "code": {"type": "string", "description": "Code to analyze"},
                    "language": {"type": "string", "description": "Programming language"},
                    "context": {"type": "string", "description": "Additional context"}
                }
            },
            required_fields=["code", "language"]
        )
        
        # Suggest Improvements
        self.register_tool(
            name="suggest_improvements",
            description="Suggest improvements for code",
            handler=self._suggest_improvements,
            input_schema={
                "properties": {
                    "code": {"type": "string", "description": "Code to improve"},
                    "focus_areas": {"type": "array", "items": {"type": "string"}, "description": "Areas to focus on"},
                    "constraints": {"type": "string", "description": "Constraints to consider"}
                }
            },
            required_fields=["code"]
        )
        
        # Check Security
        self.register_tool(
            name="check_security",
            description="Check code for security vulnerabilities",
            handler=self._check_security,
            input_schema={
                "properties": {
                    "code": {"type": "string", "description": "Code to check"},
                    "language": {"type": "string", "description": "Programming language"},
                    "severity": {"type": "string", "enum": ["all", "high", "critical"]}
                }
            },
            required_fields=["code", "language"]
        )
        
        # Review Test Coverage
        self.register_tool(
            name="review_test_coverage",
            description="Review test coverage and suggest missing tests",
            handler=self._review_test_coverage,
            input_schema={
                "properties": {
                    "code": {"type": "string", "description": "Code to analyze"},
                    "tests": {"type": "string", "description": "Existing tests"},
                    "coverage_target": {"type": "integer", "description": "Target coverage percentage"}
                }
            },
            required_fields=["code"]
        )

    async def _review_code(self, code: str, language: str, style_guide: str = None) -> Dict[str, Any]:
        """Review code quality"""
        try:
            log_operation("review_code", self.config.name, "started", {"language": language})
            
            review = await self.agent.review_code(
                code=code,
                language=language,
                style_guide=style_guide or "default"
            )
            
            log_operation("review_code", self.config.name, "completed", {})
            return review
            
        except Exception as e:
            logger.error(f"Error reviewing code: {e}")
            self.log_error(e, {"operation": "review_code"})
            raise

    async def _analyze_performance(self, code: str, language: str, context: str = None) -> Dict[str, Any]:
        """Analyze performance"""
        try:
            log_operation("analyze_performance", self.config.name, "started", {"language": language})
            
            analysis = await self.agent.analyze_performance(
                code=code,
                language=language,
                context=context or ""
            )
            
            log_operation("analyze_performance", self.config.name, "completed", {})
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing performance: {e}")
            self.log_error(e, {"operation": "analyze_performance"})
            raise

    async def _suggest_improvements(self, code: str, focus_areas: List[str] = None,
                                   constraints: str = None) -> Dict[str, Any]:
        """Suggest improvements"""
        try:
            log_operation("suggest_improvements", self.config.name, "started", {})
            
            suggestions = await self.agent.suggest_improvements(
                code=code,
                focus_areas=focus_areas or [],
                constraints=constraints or ""
            )
            
            log_operation("suggest_improvements", self.config.name, "completed", {})
            return suggestions
            
        except Exception as e:
            logger.error(f"Error suggesting improvements: {e}")
            self.log_error(e, {"operation": "suggest_improvements"})
            raise

    async def _check_security(self, code: str, language: str, severity: str = "all") -> Dict[str, Any]:
        """Check security"""
        try:
            log_operation("check_security", self.config.name, "started", {"language": language})
            
            vulnerabilities = await self.agent.check_security(
                code=code,
                language=language,
                severity=severity
            )
            
            log_operation("check_security", self.config.name, "completed", {})
            return vulnerabilities
            
        except Exception as e:
            logger.error(f"Error checking security: {e}")
            self.log_error(e, {"operation": "check_security"})
            raise

    async def _review_test_coverage(self, code: str, tests: str = None,
                                   coverage_target: int = 80) -> Dict[str, Any]:
        """Review test coverage"""
        try:
            log_operation("review_test_coverage", self.config.name, "started", {"coverage_target": coverage_target})
            
            coverage_review = await self.agent.review_test_coverage(
                code=code,
                tests=tests or "",
                coverage_target=coverage_target
            )
            
            log_operation("review_test_coverage", self.config.name, "completed", {})
            return coverage_review
            
        except Exception as e:
            logger.error(f"Error reviewing test coverage: {e}")
            self.log_error(e, {"operation": "review_test_coverage"})
            raise


async def create_and_start_critic_server(port: int = 8004) -> CriticMCPServer:
    """
    Factory function to create and start Critic MCP server
    
    Args:
        port: Port to run server on
        
    Returns:
        Started CriticMCPServer instance
    """
    config = MCPServerConfig(
        name="Critic MCP Server",
        description="Code review via MCP",
        version="1.0.0",
        port=port
    )
    
    server = CriticMCPServer(config)
    await server.initialize()
    await server.start(port)
    
    return server


if __name__ == "__main__":
    # For local testing
    import asyncio
    
    async def main():
        server = await create_and_start_critic_server()
        print(f"Critic MCP Server running on port {server.config.port}")
        print(f"Available tools: {len(server.list_tools())}")
        for tool in server.list_tools():
            print(f"  - {tool['name']}: {tool['description']}")
    
    asyncio.run(main())
