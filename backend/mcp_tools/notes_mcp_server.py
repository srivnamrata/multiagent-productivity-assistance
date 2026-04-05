"""
Notes Agent MCP Server

Wraps the NotesAgent in an MCP server for distributed processing
Exposes note management operations as MCP tools
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any

from base_mcp_server import BaseMCPServer, MCPServerConfig
from utils import log_operation

# Import the existing NotesAgent
import sys
sys.path.insert(0, '../agents')
from notes_agent import NotesAgent

logger = logging.getLogger(__name__)


class NotesMCPServer(BaseMCPServer):
    """
    MCP server for Notes Agent
    Provides distributed note-taking and knowledge management
    """

    def __init__(self, config: Optional[MCPServerConfig] = None):
        """Initialize Notes MCP server"""
        if config is None:
            config = MCPServerConfig(
                name="Notes MCP Server",
                description="Manages notes and knowledge base",
                version="1.0.0",
                port=8003
            )
        
        super().__init__(config)
        self.agent: Optional[NotesAgent] = None

    async def initialize(self) -> None:
        """Initialize notes agent and register tools"""
        logger.info("Initializing Notes Agent...")
        
        # Initialize the agent
        self.agent = NotesAgent()
        
        # Register tools that expose agent methods
        await self._register_tools()
        
        logger.info("Notes Agent initialized successfully")

    async def _register_tools(self) -> None:
        """Register note management tools"""
        
        # Create Note
        self.register_tool(
            name="create_note",
            description="Create a new note",
            handler=self._create_note,
            input_schema={
                "properties": {
                    "title": {"type": "string", "description": "Note title"},
                    "content": {"type": "string", "description": "Note content"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for organization"},
                    "is_public": {"type": "boolean", "description": "Whether note is public"}
                }
            },
            required_fields=["title", "content"]
        )
        
        # Update Note
        self.register_tool(
            name="update_note",
            description="Update an existing note",
            handler=self._update_note,
            input_schema={
                "properties": {
                    "note_id": {"type": "string", "description": "Note ID"},
                    "title": {"type": "string", "description": "New title"},
                    "content": {"type": "string", "description": "New content"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Updated tags"}
                }
            },
            required_fields=["note_id"]
        )
        
        # Delete Note
        self.register_tool(
            name="delete_note",
            description="Delete a note",
            handler=self._delete_note,
            input_schema={
                "properties": {
                    "note_id": {"type": "string", "description": "Note ID"}
                }
            },
            required_fields=["note_id"]
        )
        
        # Search Notes
        self.register_tool(
            name="search_notes",
            description="Search notes by query",
            handler=self._search_notes,
            input_schema={
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
                    "limit": {"type": "integer", "description": "Maximum number of results"}
                }
            },
            required_fields=["query"]
        )
        
        # Get Note
        self.register_tool(
            name="get_note",
            description="Get a note by ID",
            handler=self._get_note,
            input_schema={
                "properties": {
                    "note_id": {"type": "string", "description": "Note ID"}
                }
            },
            required_fields=["note_id"]
        )
        
        # List Notes
        self.register_tool(
            name="list_notes",
            description="List all notes",
            handler=self._list_notes,
            input_schema={
                "properties": {
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
                    "limit": {"type": "integer", "description": "Maximum number of notes"}
                }
            },
            required_fields=[]
        )
        
        # Link Notes
        self.register_tool(
            name="link_notes",
            description="Create a connection between two notes",
            handler=self._link_notes,
            input_schema={
                "properties": {
                    "source_note_id": {"type": "string", "description": "Source note ID"},
                    "target_note_id": {"type": "string", "description": "Target note ID"},
                    "relationship": {"type": "string", "description": "Type of relationship"}
                }
            },
            required_fields=["source_note_id", "target_note_id"]
        )
        
        # Get Related Notes
        self.register_tool(
            name="get_related_notes",
            description="Get notes related to a given note",
            handler=self._get_related_notes,
            input_schema={
                "properties": {
                    "note_id": {"type": "string", "description": "Note ID"},
                    "limit": {"type": "integer", "description": "Maximum number of results"}
                }
            },
            required_fields=["note_id"]
        )

    async def _create_note(self, title: str, content: str, tags: List[str] = None,
                          is_public: bool = False) -> Dict[str, Any]:
        """Create a new note"""
        try:
            log_operation("create_note", self.config.name, "started", {"title": title})
            
            note = await self.agent.create_note(
                title=title,
                content=content,
                tags=tags or [],
                is_public=is_public
            )
            
            log_operation("create_note", self.config.name, "completed", {"note_id": note.get("id")})
            return note
            
        except Exception as e:
            logger.error(f"Error creating note: {e}")
            self.log_error(e, {"operation": "create_note"})
            raise

    async def _update_note(self, note_id: str, title: str = None, content: str = None,
                          tags: List[str] = None) -> Dict[str, Any]:
        """Update an existing note"""
        try:
            log_operation("update_note", self.config.name, "started", {"note_id": note_id})
            
            note = await self.agent.update_note(
                note_id=note_id,
                title=title,
                content=content,
                tags=tags
            )
            
            log_operation("update_note", self.config.name, "completed", {"note_id": note_id})
            return note
            
        except Exception as e:
            logger.error(f"Error updating note: {e}")
            self.log_error(e, {"operation": "update_note", "note_id": note_id})
            raise

    async def _delete_note(self, note_id: str) -> Dict[str, Any]:
        """Delete a note"""
        try:
            log_operation("delete_note", self.config.name, "started", {"note_id": note_id})
            
            result = await self.agent.delete_note(note_id=note_id)
            
            log_operation("delete_note", self.config.name, "completed", {"note_id": note_id})
            return result
            
        except Exception as e:
            logger.error(f"Error deleting note: {e}")
            self.log_error(e, {"operation": "delete_note", "note_id": note_id})
            raise

    async def _search_notes(self, query: str, tags: List[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Search notes"""
        try:
            log_operation("search_notes", self.config.name, "started", {"query": query})
            
            results = await self.agent.search_notes(
                query=query,
                tags=tags or [],
                limit=limit
            )
            
            log_operation("search_notes", self.config.name, "completed", {"count": len(results)})
            return {"results": results, "count": len(results)}
            
        except Exception as e:
            logger.error(f"Error searching notes: {e}")
            self.log_error(e, {"operation": "search_notes"})
            raise

    async def _get_note(self, note_id: str) -> Dict[str, Any]:
        """Get a note by ID"""
        try:
            log_operation("get_note", self.config.name, "started", {"note_id": note_id})
            
            note = await self.agent.get_note(note_id=note_id)
            
            log_operation("get_note", self.config.name, "completed", {"note_id": note_id})
            return note
            
        except Exception as e:
            logger.error(f"Error getting note: {e}")
            self.log_error(e, {"operation": "get_note", "note_id": note_id})
            raise

    async def _list_notes(self, tags: List[str] = None, limit: int = 20) -> Dict[str, Any]:
        """List all notes"""
        try:
            log_operation("list_notes", self.config.name, "started", {})
            
            notes = await self.agent.list_notes(tags=tags or [], limit=limit)
            
            log_operation("list_notes", self.config.name, "completed", {"count": len(notes)})
            return {"notes": notes, "count": len(notes)}
            
        except Exception as e:
            logger.error(f"Error listing notes: {e}")
            self.log_error(e, {"operation": "list_notes"})
            raise

    async def _link_notes(self, source_note_id: str, target_note_id: str,
                         relationship: str = "related") -> Dict[str, Any]:
        """Create a connection between notes"""
        try:
            log_operation("link_notes", self.config.name, "started",
                         {"source": source_note_id, "target": target_note_id})
            
            result = await self.agent.link_notes(
                source_note_id=source_note_id,
                target_note_id=target_note_id,
                relationship=relationship
            )
            
            log_operation("link_notes", self.config.name, "completed", {})
            return result
            
        except Exception as e:
            logger.error(f"Error linking notes: {e}")
            self.log_error(e, {"operation": "link_notes"})
            raise

    async def _get_related_notes(self, note_id: str, limit: int = 10) -> Dict[str, Any]:
        """Get related notes"""
        try:
            log_operation("get_related_notes", self.config.name, "started", {"note_id": note_id})
            
            notes = await self.agent.get_related_notes(note_id=note_id, limit=limit)
            
            log_operation("get_related_notes", self.config.name, "completed", {"count": len(notes)})
            return {"notes": notes, "count": len(notes)}
            
        except Exception as e:
            logger.error(f"Error getting related notes: {e}")
            self.log_error(e, {"operation": "get_related_notes", "note_id": note_id})
            raise


async def create_and_start_notes_server(port: int = 8003) -> NotesMCPServer:
    """
    Factory function to create and start Notes MCP server
    
    Args:
        port: Port to run server on
        
    Returns:
        Started NotesMCPServer instance
    """
    config = MCPServerConfig(
        name="Notes MCP Server",
        description="Notes management via MCP",
        version="1.0.0",
        port=port
    )
    
    server = NotesMCPServer(config)
    await server.initialize()
    await server.start(port)
    
    return server


if __name__ == "__main__":
    # For local testing
    import asyncio
    
    async def main():
        server = await create_and_start_notes_server()
        print(f"Notes MCP Server running on port {server.config.port}")
        print(f"Available tools: {len(server.list_tools())}")
        for tool in server.list_tools():
            print(f"  - {tool['name']}: {tool['description']}")
    
    asyncio.run(main())
