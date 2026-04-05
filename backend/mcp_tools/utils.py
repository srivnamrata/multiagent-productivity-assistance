"""
MCP Utilities
Helper functions for MCP servers
"""

import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)


def json_serialize(obj: Any) -> Any:
    """
    JSON serializer for objects not serializable by default json code
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    if isinstance(obj, bytes):
        return obj.decode('utf-8')
    return str(obj)


def safe_json_dumps(data: Dict[str, Any]) -> str:
    """Safely dump object to JSON string"""
    try:
        return json.dumps(data, default=json_serialize)
    except Exception as e:
        logger.error(f"JSON serialization error: {e}")
        return json.dumps({"error": str(e)})


def safe_json_loads(data: str) -> Dict[str, Any]:
    """Safely load JSON string to object"""
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return {"error": f"Invalid JSON: {str(e)}"}


def format_error(error: Exception) -> Dict[str, Any]:
    """Format an exception for error response"""
    return {
        "error": str(error),
        "type": type(error).__name__,
        "traceback": traceback.format_exc()
    }


def validate_input(input_data: Dict[str, Any], required_fields: list) -> bool:
    """Validate that all required fields are present in input"""
    for field in required_fields:
        if field not in input_data:
            return False
    return True


def extract_field(data: Dict[str, Any], field: str, default=None, required=False):
    """
    Safely extract a field from dictionary
    """
    value = data.get(field, default)
    if required and value is None:
        raise ValueError(f"Required field missing: {field}")
    return value


async def run_async_safely(coro):
    """
    Run async coroutine with error handling
    """
    try:
        return await coro
    except Exception as e:
        logger.error(f"Async operation failed: {e}")
        raise


def sanitize_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize user input to prevent injection attacks
    """
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            # Remove potentially dangerous characters
            sanitized[key] = value.replace('\x00', '').strip()
        elif isinstance(value, dict):
            sanitized[key] = sanitize_input(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_input(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


def log_operation(operation: str, agent: str, status: str, details: Dict = None):
    """
    Log MCP operations for audit trail
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "operation": operation,
        "agent": agent,
        "status": status,
        "details": details or {}
    }
    logger.info(f"MCP Operation: {json.dumps(log_entry)}")
    return log_entry
