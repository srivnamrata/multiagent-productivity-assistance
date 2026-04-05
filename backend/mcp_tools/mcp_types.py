"""
MCP Type Definitions
Type definitions and protocols for Model Context Protocol servers
"""

from typing import Dict, Any, Callable, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json


class ContentType(str, Enum):
    """Supported content types for MCP"""
    TEXT = "text"
    IMAGE = "image"
    JSON = "json"


@dataclass
class TextContent:
    """Text content for tool results"""
    type: str = "text"
    text: str = ""


@dataclass
class ImageContent:
    """Image content for tool results"""
    type: str = "image"
    data: str = ""  # base64 encoded
    mimeType: str = "image/png"


@dataclass
class ToolInput:
    """Input schema for a tool"""
    type: str = "object"
    properties: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)


@dataclass
class Tool:
    """Tool definition for MCP"""
    name: str
    description: str
    inputSchema: ToolInput
    handler: Optional[Callable] = None


@dataclass
class Resource:
    """Resource definition for MCP"""
    uri: str
    name: str
    description: str
    handler: Optional[Callable] = None


@dataclass
class ToolUseBlock:
    """Tool use request block"""
    type: str = "tool_use"
    id: str = ""
    name: str = ""
    input: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResultBlock:
    """Tool result block"""
    type: str = "tool_result"
    tool_use_id: str = ""
    content: Optional[Any] = None
    isError: bool = False


class MCPException(Exception):
    """Base exception for MCP errors"""
    pass


class ToolNotFoundError(MCPException):
    """Raised when tool is not found"""
    pass


class InvalidInputError(MCPException):
    """Raised when tool input is invalid"""
    pass


class MCPServerError(MCPException):
    """Raised when MCP server encounters an error"""
    pass
