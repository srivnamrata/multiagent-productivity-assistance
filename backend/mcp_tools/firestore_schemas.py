"""
Firestore Database Schema Definitions

Defines all Firestore collections and document structures
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


# ============================================================================
# Tasks Collection
# ============================================================================

@dataclass
class Task:
    """Task document structure"""
    id: str
    project_id: str
    title: str
    description: str = ""
    status: str = "pending"  # pending, in_progress, completed
    priority: str = "medium"  # low, medium, high
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""
    completed_at: Optional[str] = None
    completion_notes: str = ""
    tags: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "assigned_to": self.assigned_to,
            "due_date": self.due_date,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "completion_notes": self.completion_notes,
            "tags": self.tags or []
        }


# ============================================================================
# Calendar Events Collection
# ============================================================================

@dataclass
class CalendarEvent:
    """Calendar event document structure"""
    id: str
    title: str
    description: str = ""
    start_time: str = ""
    end_time: str = ""
    location: str = ""
    attendees: List[str] = None
    organizer: str = ""
    created_at: str = ""
    updated_at: str = ""
    recurrence: Optional[str] = None  # daily, weekly, monthly
    reminder_minutes: int = 15
    is_all_day: bool = False
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "location": self.location,
            "attendees": self.attendees or [],
            "organizer": self.organizer,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "recurrence": self.recurrence,
            "reminder_minutes": self.reminder_minutes,
            "is_all_day": self.is_all_day,
            "metadata": self.metadata or {}
        }


# ============================================================================
# Notes Collection
# ============================================================================

@dataclass
class Note:
    """Note document structure"""
    id: str
    title: str
    content: str = ""
    tags: List[str] = None
    is_public: bool = False
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""
    last_accessed: Optional[str] = None
    access_count: int = 0
    related_note_ids: List[str] = None
    attachments: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags or [],
            "is_public": self.is_public,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "related_note_ids": self.related_note_ids or [],
            "attachments": self.attachments or [],
            "metadata": self.metadata or {}
        }


# ============================================================================
# Events Collection (Audit Trail)
# ============================================================================

@dataclass
class Event:
    """Event document structure for audit trail"""
    id: str
    event_type: str
    source: str  # Which agent/service generated this event
    user_id: Optional[str] = None
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    action: str = ""  # create, update, delete, read
    status: str = "processed"  # processed, failed, pending_retry
    timestamp: str = ""
    data: Dict[str, Any] = None
    result: Dict[str, Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    retention_days: int = 90  # How long to keep this event
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "source": self.source,
            "user_id": self.user_id,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "action": self.action,
            "status": self.status,
            "timestamp": self.timestamp,
            "data": self.data or {},
            "result": self.result or {},
            "error": self.error,
            "metadata": self.metadata or {},
            "retention_days": self.retention_days
        }


# ============================================================================
# Projects Collection
# ============================================================================

@dataclass
class Project:
    """Project document structure"""
    id: str
    name: str
    description: str = ""
    owner: str = ""
    members: List[str] = None
    status: str = "active"  # active, archived, deleted
    created_at: str = ""
    updated_at: str = ""
    settings: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "owner": self.owner,
            "members": self.members or [],
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "settings": self.settings or {},
            "metadata": self.metadata or {}
        }


# ============================================================================
# Access Logs Collection
# ============================================================================

@dataclass
class AccessLog:
    """Access log document structure"""
    id: str
    user_id: str
    resource_id: str
    resource_type: str
    access_type: str  # read, write, delete, share
    timestamp: str = ""
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    duration_ms: int = 0
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "access_type": self.access_type,
            "timestamp": self.timestamp,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_message": self.error_message,
            "metadata": self.metadata or {}
        }


# ============================================================================
# System Configuration Collection
# ============================================================================

@dataclass
class SystemConfig:
    """System configuration document structure"""
    key: str  # Unique configuration key
    value: Any
    type: str  # string, number, boolean, object, array
    description: str = ""
    updated_at: str = ""
    updated_by: str = ""
    is_secret: bool = False
    environment: str = "production"  # production, staging, development
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "type": self.type,
            "description": self.description,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
            "is_secret": self.is_secret,
            "environment": self.environment
        }


# ============================================================================
# Research Articles Collection
# ============================================================================

@dataclass
class ResearchArticle:
    """Research article document structure"""
    id: str
    title: str
    source: str  # towards_data_science, arxiv, medium, hacker_news, reddit_ml, google_research
    url: str = ""
    published_date: str = ""
    created_at: str = ""
    category: str = ""  # artificial_intelligence, machine_learning, robotics, etc.
    summary: str = ""
    full_content: Optional[str] = None
    has_audio: bool = False
    audio_url: Optional[str] = None
    voice: str = "female"  # male, female
    audio_language: str = "en-US"
    authors: List[str] = None
    keywords: List[str] = None
    reading_time_minutes: int = 0
    engagement_score: float = 0.0
    week: int = 0  # ISO week number
    year: int = 0  # Year for weekly digest
    is_trending: bool = False
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "url": self.url,
            "published_date": self.published_date,
            "created_at": self.created_at,
            "category": self.category,
            "summary": self.summary,
            "full_content": self.full_content,
            "has_audio": self.has_audio,
            "audio_url": self.audio_url,
            "voice": self.voice,
            "audio_language": self.audio_language,
            "authors": self.authors or [],
            "keywords": self.keywords or [],
            "reading_time_minutes": self.reading_time_minutes,
            "engagement_score": self.engagement_score,
            "week": self.week,
            "year": self.year,
            "is_trending": self.is_trending,
            "metadata": self.metadata or {}
        }


# ============================================================================
# Custom Research Summaries Collection
# ============================================================================

@dataclass
class CustomResearchSummary:
    """Custom research summary document structure"""
    id: str
    title: str
    summary: str = ""
    article_ids: List[str] = None
    focus_areas: List[str] = None
    created_at: str = ""
    created_by: str = ""
    audio_url: Optional[str] = None
    voice: str = "female"
    language: str = "en-US"
    tags: List[str] = None
    is_public: bool = False
    view_count: int = 0
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "article_ids": self.article_ids or [],
            "focus_areas": self.focus_areas or [],
            "created_at": self.created_at,
            "created_by": self.created_by,
            "audio_url": self.audio_url,
            "voice": self.voice,
            "language": self.language,
            "tags": self.tags or [],
            "is_public": self.is_public,
            "view_count": self.view_count,
            "metadata": self.metadata or {}
        }


# ============================================================================
# Collection Index Definitions
# ============================================================================

FIRESTORE_COLLECTION_DEFINITIONS = {
    "tasks": {
        "description": "Task management documents",
        "indexes": [
            ["project_id", "status"],
            ["project_id", "due_date"],
            ["assigned_to", "status"],
            ["created_at"]
        ]
    },
    "calendar_events": {
        "description": "Calendar event documents",
        "indexes": [
            ["start_time", "end_time"],
            ["organizer", "start_time"],
            ["attendees"],
            ["created_at"]
        ]
    },
    "notes": {
        "description": "Note/knowledge base documents",
        "indexes": [
            ["created_by", "created_at"],
            ["tags"],
            ["is_public"],
            ["updated_at"]
        ]
    },
    "events": {
        "description": "Audit trail and event log documents",
        "indexes": [
            ["timestamp", "source"],
            ["event_type", "timestamp"],
            ["user_id", "timestamp"],
            ["resource_id"],
            ["status"]
        ]
    },
    "projects": {
        "description": "Project documents",
        "indexes": [
            ["owner", "status"],
            ["members"],
            ["created_at"]
        ]
    },
    "access_logs": {
        "description": "User access log documents",
        "indexes": [
            ["user_id", "timestamp"],
            ["resource_id"],
            ["access_type", "timestamp"]
        ]
    },
    "system_config": {
        "description": "System configuration documents",
        "indexes": [
            ["environment", "key"]
        ]
    },
    "research_articles": {
        "description": "Research article documents from AI/ML/Robotics sources",
        "indexes": [
            ["published_date", "category"],
            ["week", "year"],
            ["source", "published_date"],
            ["is_trending", "published_date"],
            ["category", "published_date"],
            ["has_audio"]
        ]
    },
    "custom_research_summaries": {
        "description": "Custom research summary documents",
        "indexes": [
            ["created_at", "created_by"],
            ["is_public", "created_at"],
            ["tags"],
            ["created_by"]
        ]
    }
}


# ============================================================================
# TTL (Time To Live) Policies
# ============================================================================

TTL_POLICIES = {
    "events": 90,  # days - Keep audit logs for 90 days
    "access_logs": 30,  # days - Keep access logs for 30 days
}


# ============================================================================
# Data Validation Rules
# ============================================================================

DATA_VALIDATION_RULES = {
    "tasks": {
        "required": ["id", "project_id", "title"],
        "status_enum": ["pending", "in_progress", "completed"],
        "priority_enum": ["low", "medium", "high"]
    },
    "calendar_events": {
        "required": ["id", "title", "start_time", "end_time"],
        "recurrence_enum": [None, "daily", "weekly", "monthly"],
        "min_reminder_minutes": 0,
        "max_reminder_minutes": 10080  # 7 days
    },
    "notes": {
        "required": ["id", "title", "content"],
        "title_max_length": 255,
        "max_tags": 20
    },
    "events": {
        "required": ["id", "event_type", "source", "timestamp"],
        "status_enum": ["processed", "failed", "pending_retry"],
        "action_enum": ["create", "update", "delete", "read"]
    },
    "access_logs": {
        "required": ["id", "user_id", "resource_id", "resource_type", "access_type"],
        "access_type_enum": ["read", "write", "delete", "share"]
    },
    "research_articles": {
        "required": ["id", "title", "source", "url", "category"],
        "source_enum": ["towards_data_science", "arxiv", "medium", "hacker_news", "reddit_ml", "google_research"],
        "category_enum": ["artificial_intelligence", "machine_learning", "robotics", "deep_learning", "nlp", "computer_vision", "reinforcement_learning", "data_science"],
        "title_max_length": 500,
        "summary_max_length": 2000,
        "max_keywords": 50
    },
    "custom_research_summaries": {
        "required": ["id", "title", "summary"],
        "title_max_length": 255,
        "summary_max_length": 5000,
        "max_article_ids": 100,
        "max_focus_areas": 20,
        "max_tags": 20
    }
}
