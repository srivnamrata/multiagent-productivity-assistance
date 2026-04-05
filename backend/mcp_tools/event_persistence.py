"""
Event Persistence System

Logs all system events to Firestore for audit trail
Provides event replay and analysis capabilities
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import asdict

from firestore_adapter import FirestoreAdapter
from firestore_schemas import Event, AccessLog

logger = logging.getLogger(__name__)


class EventLogger:
    """
    Records and persists all system events
    Used for audit trails, compliance, and debugging
    """
    
    def __init__(self, firestore_adapter: FirestoreAdapter):
        """
        Initialize event logger
        
        Args:
            firestore_adapter: FirestoreAdapter instance for persistence
        """
        self.adapter = firestore_adapter
        self._event_queue: List[Event] = []
        self._queue_lock = asyncio.Lock()
        self._is_running = False
        self._processor_task = None
        
        logger.info("EventLogger initialized")
    
    async def start(self, flush_interval_seconds: int = 5) -> None:
        """
        Start the event logger background processor
        
        Args:
            flush_interval_seconds: How often to flush queued events to Firestore
        """
        self._is_running = True
        self._processor_task = asyncio.create_task(
            self._process_events_loop(flush_interval_seconds)
        )
        logger.info("EventLogger started")
    
    async def stop(self) -> None:
        """Stop the event logger and flush remaining events"""
        self._is_running = False
        if self._processor_task:
            await self._processor_task
        
        # Final flush
        await self.flush()
        logger.info("EventLogger stopped")
    
    async def log_event(self, event_type: str, source: str, action: str = None,
                       user_id: str = None, resource_id: str = None,
                       resource_type: str = None, data: Dict[str, Any] = None,
                       result: Dict[str, Any] = None, error: str = None,
                       metadata: Dict[str, Any] = None) -> str:
        """
        Log a system event
        
        Args:
            event_type: Type of event (e.g., "task_created", "note_updated")
            source: Agent/service that generated the event
            action: Action performed (create, update, delete, read)
            user_id: User who triggered the event
            resource_id: Resource affected by the event
            resource_type: Type of resource (task, note, event, etc.)
            data: Input data for the event
            result: Result of the operation
            error: Error message if operation failed
            metadata: Additional metadata
            
        Returns:
            Event ID
        """
        event_id = str(uuid.uuid4())
        
        event = Event(
            id=event_id,
            event_type=event_type,
            source=source,
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            action=action or "unknown",
            status="processed" if not error else "failed",
            timestamp=datetime.now().isoformat(),
            data=data or {},
            result=result or {},
            error=error,
            metadata=metadata or {},
            retention_days=90
        )
        
        async with self._queue_lock:
            self._event_queue.append(event)
        
        logger.debug(f"Logged event {event_id}: {event_type}")
        return event_id
    
    async def log_access(self, user_id: str, resource_id: str, resource_type: str,
                        access_type: str, ip_address: str = None, user_agent: str = None,
                        duration_ms: int = 0, success: bool = True,
                        error_message: str = None, metadata: Dict[str, Any] = None) -> str:
        """
        Log a user access event
        
        Args:
            user_id: User accessing the resource
            resource_id: Resource being accessed
            resource_type: Type of resource
            access_type: Type of access (read, write, delete, share)
            ip_address: IP address of the user
            user_agent: User agent string
            duration_ms: Duration of access in milliseconds
            success: Whether access was successful
            error_message: Error message if access failed
            metadata: Additional metadata
            
        Returns:
            Access log ID
        """
        log_id = str(uuid.uuid4())
        
        access_log = AccessLog(
            id=log_id,
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            access_type=access_type,
            timestamp=datetime.now().isoformat(),
            ip_address=ip_address,
            user_agent=user_agent,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            metadata=metadata or {}
        )
        
        try:
            await self.adapter.create_access_log(access_log)
            logger.debug(f"Logged access {log_id}: {resource_type}/{resource_id}")
        except Exception as e:
            logger.error(f"Error logging access: {e}")
        
        return log_id
    
    async def flush(self) -> int:
        """
        Flush queued events to Firestore
        
        Returns:
            Number of events flushed
        """
        async with self._queue_lock:
            if not self._event_queue:
                return 0
            
            events_to_flush = self._event_queue.copy()
            self._event_queue.clear()
        
        flushed_count = 0
        for event in events_to_flush:
            try:
                await self.adapter.create_event_log(event)
                flushed_count += 1
            except Exception as e:
                logger.error(f"Error flushing event {event.id}: {e}")
                # Re-add to queue on failure
                async with self._queue_lock:
                    self._event_queue.append(event)
        
        if flushed_count > 0:
            logger.info(f"Flushed {flushed_count} events to Firestore")
        
        return flushed_count
    
    async def _process_events_loop(self, flush_interval_seconds: int) -> None:
        """Background task to periodically flush events"""
        while self._is_running:
            try:
                await asyncio.sleep(flush_interval_seconds)
                await self.flush()
            except Exception as e:
                logger.error(f"Error in event processing loop: {e}")
    
    async def get_events(self, filters: List[tuple] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get events from Firestore
        
        Args:
            filters: Query filters
            limit: Maximum number of events
            
        Returns:
            List of events
        """
        return await self.adapter.query_event_logs(filters, limit)
    
    async def get_events_by_source(self, source: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get events from a specific source"""
        filters = [("source", "==", source)]
        return await self.get_events(filters, limit)
    
    async def get_events_by_type(self, event_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get events of a specific type"""
        filters = [("event_type", "==", event_type)]
        return await self.get_events(filters, limit)
    
    async def get_events_by_user(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get events triggered by a specific user"""
        filters = [("user_id", "==", user_id)]
        return await self.get_events(filters, limit)
    
    async def get_events_by_resource(self, resource_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get events affecting a specific resource"""
        filters = [("resource_id", "==", resource_id)]
        return await self.get_events(filters, limit)
    
    async def replay_events(self, start_time: str, end_time: str = None,
                           event_type: str = None, source: str = None) -> List[Dict[str, Any]]:
        """
        Replay events from a time range
        
        Args:
            start_time: Start time (ISO format)
            end_time: End time (ISO format)
            event_type: Filter by event type
            source: Filter by source
            
        Returns:
            List of events in the time range
        """
        filters = [("timestamp", ">=", start_time)]
        
        if end_time:
            filters.append(("timestamp", "<=", end_time))
        
        if event_type:
            filters.append(("event_type", "==", event_type))
        
        if source:
            filters.append(("source", "==", source))
        
        return await self.get_events(filters)
    
    async def cleanup_old_events(self) -> int:
        """
        Delete events older than retention period
        
        Returns:
            Number of events deleted
        """
        retention_days = 90
        cutoff_date = (datetime.now() - timedelta(days=retention_days)).isoformat()
        
        # Get events older than cutoff
        old_events = await self.adapter.query("events", [("timestamp", "<", cutoff_date)])
        
        deleted_count = 0
        for event in old_events:
            try:
                success = await self.adapter.delete("events", event["id"])
                if success:
                    deleted_count += 1
            except Exception as e:
                logger.error(f"Error deleting old event {event['id']}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old events")
        
        return deleted_count


class EventEmitter:
    """
    Decorators and utilities for emitting events from handlers
    """
    
    def __init__(self, logger: EventLogger):
        """Initialize event emitter"""
        self.logger = logger
    
    def emit_event(self, event_type: str, source: str):
        """
        Decorator to emit events automatically
        
        Args:
            event_type: Type of event
            source: Source of the event
        """
        def decorator(func):
            async def wrapper(*args, **kwargs):
                try:
                    result = await func(*args, **kwargs)
                    
                    # Extract metadata from arguments
                    user_id = kwargs.get("user_id")
                    resource_id = result.get("id") if isinstance(result, dict) else None
                    resource_type = kwargs.get("resource_type", source)
                    
                    await self.logger.log_event(
                        event_type=event_type,
                        source=source,
                        action="execute",
                        user_id=user_id,
                        resource_id=resource_id,
                        resource_type=resource_type,
                        data=kwargs,
                        result=result if isinstance(result, dict) else {"status": "success"}
                    )
                    
                    return result
                    
                except Exception as e:
                    user_id = kwargs.get("user_id")
                    resource_id = kwargs.get("id") or kwargs.get("resource_id")
                    
                    await self.logger.log_event(
                        event_type=event_type,
                        source=source,
                        action="execute",
                        user_id=user_id,
                        resource_id=resource_id,
                        error=str(e)
                    )
                    raise
            
            return wrapper
        return decorator


class EventAggregator:
    """
    Aggregates and analyzes events
    Provides insights into system behavior
    """
    
    def __init__(self, logger: EventLogger):
        """Initialize event aggregator"""
        self.logger = logger
    
    async def get_activity_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get activity summary for the last N hours
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Activity summary
        """
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        events = await self.logger.replay_events(start_time)
        
        # Aggregate data
        summary = {
            "period_hours": hours,
            "total_events": len(events),
            "by_type": {},
            "by_source": {},
            "by_action": {},
            "errors": 0
        }
        
        for event in events:
            # Count by type
            event_type = event.get("event_type", "unknown")
            summary["by_type"][event_type] = summary["by_type"].get(event_type, 0) + 1
            
            # Count by source
            source = event.get("source", "unknown")
            summary["by_source"][source] = summary["by_source"].get(source, 0) + 1
            
            # Count by action
            action = event.get("action", "unknown")
            summary["by_action"][action] = summary["by_action"].get(action, 0) + 1
            
            # Count errors
            if event.get("status") == "failed":
                summary["errors"] += 1
        
        return summary
    
    async def get_user_activity(self, user_id: str, hours: int = 24) -> Dict[str, Any]:
        """
        Get activity for a specific user
        
        Args:
            user_id: User ID
            hours: Number of hours to analyze
            
        Returns:
            User activity summary
        """
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        events = await self.logger.replay_events(start_time)
        user_events = [e for e in events if e.get("user_id") == user_id]
        
        return {
            "user_id": user_id,
            "period_hours": hours,
            "total_actions": len(user_events),
            "by_type": {},
            "by_resource": {},
            "errors": 0
        }
    
    async def get_health_events(self, hours: int = 1) -> Dict[str, Any]:
        """
        Get health-related events from the last N hours
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Health events summary
        """
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        events = await self.logger.get_events([("timestamp", ">=", start_time)])
        
        failed_events = [e for e in events if e.get("status") == "failed"]
        
        return {
            "period_hours": hours,
            "total_events": len(events),
            "failed_count": len(failed_events),
            "success_rate": ((len(events) - len(failed_events)) / len(events) * 100) if events else 0,
            "failures": failed_events[:10]  # Last 10 failures
        }


# ============================================================================
# Global Event Logger Instance
# ============================================================================

_global_event_logger: Optional[EventLogger] = None
_global_event_emitter: Optional[EventEmitter] = None


def initialize_event_logging(firestore_adapter: FirestoreAdapter) -> tuple[EventLogger, EventEmitter]:
    """
    Initialize global event logging system
    
    Args:
        firestore_adapter: FirestoreAdapter instance
        
    Returns:
        Tuple of (EventLogger, EventEmitter)
    """
    global _global_event_logger, _global_event_emitter
    
    _global_event_logger = EventLogger(firestore_adapter)
    _global_event_emitter = EventEmitter(_global_event_logger)
    
    logger.info("Event logging system initialized")
    return _global_event_logger, _global_event_emitter


def get_event_logger() -> Optional[EventLogger]:
    """Get the global event logger instance"""
    return _global_event_logger


def get_event_emitter() -> Optional[EventEmitter]:
    """Get the global event emitter instance"""
    return _global_event_emitter
