"""
Calendar Agent - Sub-agent for calendar and scheduling management
Handles Google Calendar operations, event scheduling, availability checks, and meeting management
"""

import asyncio
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)


class CalendarAgent:
    """
    Sub-agent specialized in calendar and scheduling operations.
    Handles:
    - Creating calendar events with attendees
    - Checking availability for dates/times
    - Finding optimal meeting times
    - Updating and deleting events
    - Managing recurring events
    - Handling timezone conversions
    """
    
    def __init__(self, knowledge_graph=None, llm_service=None):
        self.knowledge_graph = knowledge_graph
        self.llm_service = llm_service
        self.events = {}  # event_id -> event data
        self.calendars = {}  # user_id -> calendar data
    
    async def execute(self, step: Dict[str, Any], previous_results: Dict) -> Dict[str, Any]:
        """
        Execute a calendar management step.
        Step types: "create_event", "check_availability", "find_meeting_time", 
                   "update_event", "delete_event", "list_events"
        """
        step_type = step.get("type")
        
        if step_type == "create_event":
            return await self._create_event(step)
        elif step_type == "check_availability":
            return await self._check_availability(step)
        elif step_type == "find_meeting_time":
            return await self._find_meeting_time(step)
        elif step_type == "update_event":
            return await self._update_event(step)
        elif step_type == "delete_event":
            return await self._delete_event(step)
        elif step_type == "list_events":
            return await self._list_events(step)
        else:
            return {"status": "unsupported_step_type", "error": f"Unknown step type: {step_type}"}
    
    async def _create_event(self, step: Dict) -> Dict:
        """Create a new calendar event"""
        try:
            event_id = str(uuid.uuid4())
            title = step.get("title", "Untitled Event")
            description = step.get("description", "")
            start_time = step.get("start_time")
            end_time = step.get("end_time")
            attendees = step.get("attendees", [])
            location = step.get("location", "")
            timezone = step.get("timezone", "UTC")
            
            if not start_time or not end_time:
                return {
                    "status": "error",
                    "error": "start_time and end_time are required"
                }
            
            # Validate time format (ISO 8601)
            try:
                datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                return {
                    "status": "error",
                    "error": "Invalid time format. Use ISO 8601 format (e.g., 2024-04-05T14:00:00Z)"
                }
            
            event = {
                "event_id": event_id,
                "title": title,
                "description": description,
                "start_time": start_time,
                "end_time": end_time,
                "attendees": attendees,
                "location": location,
                "timezone": timezone,
                "created_at": datetime.now().isoformat(),
                "status": "scheduled"
            }
            
            self.events[event_id] = event
            
            # Log in knowledge graph if available
            if self.knowledge_graph:
                await self.knowledge_graph.add_entity({
                    "id": event_id,
                    "type": "event",
                    "name": title,
                    "attributes": event
                })
            
            logger.info(f"✅ Created event: {title} (ID: {event_id})")
            
            return {
                "status": "success",
                "event_id": event_id,
                "title": title,
                "start_time": start_time,
                "end_time": end_time,
                "attendees": attendees,
                "location": location,
                "message": f"Event '{title}' scheduled successfully"
            }
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _check_availability(self, step: Dict) -> Dict:
        """Check availability for a user or list of users"""
        try:
            user_ids = step.get("user_ids", [])
            start_time = step.get("start_time")
            end_time = step.get("end_time")
            
            if not user_ids or not start_time or not end_time:
                return {
                    "status": "error",
                    "error": "user_ids, start_time, and end_time are required"
                }
            
            availability = {}
            
            for user_id in user_ids:
                # Check for conflicts in the specified time range
                conflicts = []
                for event_id, event in self.events.items():
                    if user_id in event.get("attendees", []):
                        event_start = event.get("start_time")
                        event_end = event.get("end_time")
                        
                        # Simple overlap detection
                        if not (event_end <= start_time or event_start >= end_time):
                            conflicts.append({
                                "event_id": event_id,
                                "title": event.get("title"),
                                "start_time": event_start,
                                "end_time": event_end
                            })
                
                availability[user_id] = {
                    "available": len(conflicts) == 0,
                    "conflicts": conflicts
                }
            
            logger.info(f"✅ Checked availability for {len(user_ids)} users")
            
            return {
                "status": "success",
                "availability": availability,
                "requested_start_time": start_time,
                "requested_end_time": end_time
            }
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _find_meeting_time(self, step: Dict) -> Dict:
        """Find optimal meeting time for multiple attendees"""
        try:
            attendees = step.get("attendees", [])
            duration_minutes = step.get("duration_minutes", 60)
            start_date = step.get("start_date")
            end_date = step.get("end_date")
            
            if not attendees or not start_date or not end_date:
                return {
                    "status": "error",
                    "error": "attendees, start_date, and end_date are required"
                }
            
            # Generate candidate time slots
            candidates = []
            current = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            while current < end:
                slot_end = current + timedelta(minutes=duration_minutes)
                
                # Check if all attendees are available
                all_available = True
                for attendee in attendees:
                    for event_id, event in self.events.items():
                        if attendee in event.get("attendees", []):
                            event_start = event.get("start_time")
                            event_end = event.get("end_time")
                            
                            if not (event_end <= current.isoformat() or event_start >= slot_end.isoformat()):
                                all_available = False
                                break
                    if not all_available:
                        break
                
                if all_available:
                    candidates.append({
                        "start_time": current.isoformat(),
                        "end_time": slot_end.isoformat(),
                        "available_attendees": len(attendees)
                    })
                
                current += timedelta(hours=1)  # Check hourly slots
            
            logger.info(f"✅ Found {len(candidates)} available meeting slots")
            
            return {
                "status": "success",
                "candidates": candidates[:5],  # Return top 5 options
                "total_candidates": len(candidates),
                "attendees": attendees,
                "duration_minutes": duration_minutes
            }
        except Exception as e:
            logger.error(f"Error finding meeting time: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _update_event(self, step: Dict) -> Dict:
        """Update an existing calendar event"""
        try:
            event_id = step.get("event_id")
            
            if not event_id or event_id not in self.events:
                return {"status": "error", "error": "Event not found"}
            
            event = self.events[event_id]
            
            # Update fields if provided
            if "title" in step:
                event["title"] = step["title"]
            if "description" in step:
                event["description"] = step["description"]
            if "start_time" in step:
                event["start_time"] = step["start_time"]
            if "end_time" in step:
                event["end_time"] = step["end_time"]
            if "attendees" in step:
                event["attendees"] = step["attendees"]
            if "location" in step:
                event["location"] = step["location"]
            
            event["updated_at"] = datetime.now().isoformat()
            
            logger.info(f"✅ Updated event: {event_id}")
            
            return {
                "status": "success",
                "event_id": event_id,
                "event": event,
                "message": "Event updated successfully"
            }
        except Exception as e:
            logger.error(f"Error updating event: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _delete_event(self, step: Dict) -> Dict:
        """Delete a calendar event"""
        try:
            event_id = step.get("event_id")
            
            if not event_id or event_id not in self.events:
                return {"status": "error", "error": "Event not found"}
            
            event_title = self.events[event_id].get("title", "Unknown")
            del self.events[event_id]
            
            logger.info(f"✅ Deleted event: {event_id} ({event_title})")
            
            return {
                "status": "success",
                "event_id": event_id,
                "message": f"Event '{event_title}' deleted successfully"
            }
        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _list_events(self, step: Dict) -> Dict:
        """List calendar events with optional filtering"""
        try:
            user_id = step.get("user_id")
            start_time = step.get("start_time")
            end_time = step.get("end_time")
            limit = step.get("limit", 10)
            
            events = []
            
            for event_id, event in list(self.events.items())[:limit]:
                # Filter by user if specified
                if user_id and user_id not in event.get("attendees", []):
                    continue
                
                # Filter by time range if specified
                if start_time and event.get("end_time") <= start_time:
                    continue
                if end_time and event.get("start_time") >= end_time:
                    continue
                
                events.append({
                    "event_id": event_id,
                    "title": event.get("title"),
                    "start_time": event.get("start_time"),
                    "end_time": event.get("end_time"),
                    "attendees": event.get("attendees", []),
                    "location": event.get("location", "")
                })
            
            logger.info(f"✅ Listed {len(events)} events")
            
            return {
                "status": "success",
                "events": events,
                "count": len(events),
                "total_available": len(self.events)
            }
        except Exception as e:
            logger.error(f"Error listing events: {e}")
            return {"status": "error", "error": str(e)}
