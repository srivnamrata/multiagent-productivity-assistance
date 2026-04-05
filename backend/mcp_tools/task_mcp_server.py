"""
Task Agent MCP Server

Wraps the TaskAgent in an MCP server for distributed processing
Exposes task management operations as MCP tools
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any

from base_mcp_server import BaseMCPServer, MCPServerConfig
from utils import log_operation

# Import the existing TaskAgent
import sys
sys.path.insert(0, '../agents')
from task_agent import TaskAgent

logger = logging.getLogger(__name__)


class TaskMCPServer(BaseMCPServer):
    """
    MCP server for Task Agent
    Provides distributed task management capabilities
    """

    def __init__(self, config: Optional[MCPServerConfig] = None):
        """Initialize Task MCP server"""
        if config is None:
            config = MCPServerConfig(
                name="Task MCP Server",
                description="Manages tasks and todos across projects",
                version="1.0.0",
                port=8001
            )
        
        super().__init__(config)
        self.agent: Optional[TaskAgent] = None

    async def initialize(self) -> None:
        """Initialize task agent and register tools"""
        logger.info("Initializing Task Agent...")
        
        # Initialize the agent
        self.agent = TaskAgent()
        
        # Register tools that expose agent methods
        await self._register_tools()
        
        logger.info("Task Agent initialized successfully")

    async def _register_tools(self) -> None:
        """Register task management tools"""
        
        # Create Task
        self.register_tool(
            name="create_task",
            description="Create a new task",
            handler=self._create_task,
            input_schema={
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "description": {"type": "string", "description": "Task description"},
                    "project_id": {"type": "string", "description": "Project ID"},
                    "due_date": {"type": "string", "description": "Due date (ISO format)"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]}
                }
            },
            required_fields=["title", "project_id"]
        )
        
        # Update Task
        self.register_tool(
            name="update_task",
            description="Update an existing task",
            handler=self._update_task,
            input_schema={
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "title": {"type": "string", "description": "New title"},
                    "description": {"type": "string", "description": "New description"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "due_date": {"type": "string", "description": "Due date (ISO format)"}
                }
            },
            required_fields=["task_id"]
        )
        
        # Complete Task
        self.register_tool(
            name="complete_task",
            description="Mark a task as completed",
            handler=self._complete_task,
            input_schema={
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "notes": {"type": "string", "description": "Completion notes"}
                }
            },
            required_fields=["task_id"]
        )
        
        # Delete Task
        self.register_tool(
            name="delete_task",
            description="Delete a task",
            handler=self._delete_task,
            input_schema={
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"}
                }
            },
            required_fields=["task_id"]
        )
        
        # Get Tasks
        self.register_tool(
            name="get_tasks",
            description="Get tasks for a project",
            handler=self._get_tasks,
            input_schema={
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                    "limit": {"type": "integer", "description": "Maximum number of tasks"}
                }
            },
            required_fields=["project_id"]
        )
        
        # Assign Task
        self.register_tool(
            name="assign_task",
            description="Assign a task to a user",
            handler=self._assign_task,
            input_schema={
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "user_id": {"type": "string", "description": "User ID"}
                }
            },
            required_fields=["task_id", "user_id"]
        )

    async def _create_task(self, title: str, project_id: str, description: str = None,
                          due_date: str = None, priority: str = "medium") -> Dict[str, Any]:
        """Create a new task"""
        try:
            log_operation("create_task", self.config.name, "started", {"title": title, "project": project_id})
            
            task = await self.agent.create_task(
                title=title,
                description=description,
                project_id=project_id,
                due_date=due_date,
                priority=priority
            )
            
            log_operation("create_task", self.config.name, "completed", {"task_id": task.get("id")})
            return task
            
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            self.log_error(e, {"operation": "create_task"})
            raise

    async def _update_task(self, task_id: str, title: str = None, description: str = None,
                          status: str = None, priority: str = None, due_date: str = None) -> Dict[str, Any]:
        """Update an existing task"""
        try:
            log_operation("update_task", self.config.name, "started", {"task_id": task_id})
            
            task = await self.agent.update_task(
                task_id=task_id,
                title=title,
                description=description,
                status=status,
                priority=priority,
                due_date=due_date
            )
            
            log_operation("update_task", self.config.name, "completed", {"task_id": task_id})
            return task
            
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            self.log_error(e, {"operation": "update_task", "task_id": task_id})
            raise

    async def _complete_task(self, task_id: str, notes: str = None) -> Dict[str, Any]:
        """Mark a task as completed"""
        try:
            log_operation("complete_task", self.config.name, "started", {"task_id": task_id})
            
            task = await self.agent.complete_task(task_id=task_id, notes=notes or "")
            
            log_operation("complete_task", self.config.name, "completed", {"task_id": task_id})
            return task
            
        except Exception as e:
            logger.error(f"Error completing task: {e}")
            self.log_error(e, {"operation": "complete_task", "task_id": task_id})
            raise

    async def _delete_task(self, task_id: str) -> Dict[str, Any]:
        """Delete a task"""
        try:
            log_operation("delete_task", self.config.name, "started", {"task_id": task_id})
            
            result = await self.agent.delete_task(task_id=task_id)
            
            log_operation("delete_task", self.config.name, "completed", {"task_id": task_id})
            return result
            
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            self.log_error(e, {"operation": "delete_task", "task_id": task_id})
            raise

    async def _get_tasks(self, project_id: str, status: str = None, limit: int = 10) -> Dict[str, Any]:
        """Get tasks for a project"""
        try:
            log_operation("get_tasks", self.config.name, "started", {"project_id": project_id})
            
            tasks = await self.agent.get_tasks(
                project_id=project_id,
                status=status,
                limit=limit
            )
            
            log_operation("get_tasks", self.config.name, "completed", {"project_id": project_id, "count": len(tasks)})
            return {"tasks": tasks, "count": len(tasks)}
            
        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
            self.log_error(e, {"operation": "get_tasks", "project_id": project_id})
            raise

    async def _assign_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """Assign a task to a user"""
        try:
            log_operation("assign_task", self.config.name, "started", {"task_id": task_id, "user_id": user_id})
            
            task = await self.agent.assign_task(task_id=task_id, user_id=user_id)
            
            log_operation("assign_task", self.config.name, "completed", {"task_id": task_id, "user_id": user_id})
            return task
            
        except Exception as e:
            logger.error(f"Error assigning task: {e}")
            self.log_error(e, {"operation": "assign_task", "task_id": task_id})
            raise


async def create_and_start_task_server(port: int = 8001) -> TaskMCPServer:
    """
    Factory function to create and start Task MCP server
    
    Args:
        port: Port to run server on
        
    Returns:
        Started TaskMCPServer instance
    """
    config = MCPServerConfig(
        name="Task MCP Server",
        description="Task management via MCP",
        version="1.0.0",
        port=port
    )
    
    server = TaskMCPServer(config)
    await server.initialize()
    await server.start(port)
    
    return server


if __name__ == "__main__":
    # For local testing
    import asyncio
    
    async def main():
        server = await create_and_start_task_server()
        print(f"Task MCP Server running on port {server.config.port}")
        print(f"Available tools: {len(server.list_tools())}")
        for tool in server.list_tools():
            print(f"  - {tool['name']}: {tool['description']}")
    
    asyncio.run(main())
