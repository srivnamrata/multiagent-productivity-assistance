"""
Firestore Schema Definitions

Defines all Firestore collection schemas, validation rules, and database indexes
for the multi-agent productivity system.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMERATIONS FOR DATA VALIDATION
# ============================================================================

class ResearchSource(Enum):
    """Research article sources"""
    TOWARDS_DATA_SCIENCE = "towards_data_science"
    ARXIV = "arxiv"
    MEDIUM = "medium"
    HACKER_NEWS = "hacker_news"
    REDDIT = "reddit"
    GOOGLE_RESEARCH = "google_research"


class ResearchCategory(Enum):
    """Research article categories"""
    ARTIFICIAL_INTELLIGENCE = "artificial_intelligence"
    MACHINE_LEARNING = "machine_learning"
    DEEP_LEARNING = "deep_learning"
    ROBOTICS = "robotics"
    NLP = "nlp"
    COMPUTER_VISION = "computer_vision"
    REINFORCEMENT_LEARNING = "reinforcement_learning"
    DATA_SCIENCE = "data_science"


class NewsSource(Enum):
    """News article sources"""
    CNN = "cnn"
    BBC = "bbc"
    REUTERS = "reuters"
    ASSOCIATED_PRESS = "associated_press"
    AL_JAZEERA = "al_jazeera"
    THE_GUARDIAN = "the_guardian"
    NPR = "npr"
    NEW_YORK_TIMES = "new_york_times"


class NewsCategory(Enum):
    """News article categories"""
    POLITICS = "politics"
    BUSINESS = "business"
    TECHNOLOGY = "technology"
    HEALTH = "health"
    SPORTS = "sports"
    ENTERTAINMENT = "entertainment"
    WORLD = "world"
    NATIONAL = "national"
    SCIENCE = "science"
    CLIMATE = "climate"
    OPINION = "opinion"
    OTHER = "other"


# ============================================================================
# RESEARCH AGENT SCHEMAS
# ============================================================================

@dataclass
class ResearchArticle:
    """Research article document schema"""
    id: str
    title: str
    source: str  # ResearchSource enum value
    url: str
    published_date: str
    category: str  # ResearchCategory enum value
    summary: str
    full_content: Optional[str] = None
    has_audio: bool = False
    audio_url: Optional[str] = None
    voice: Optional[str] = None
    audio_language: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    reading_time: int = 0
    engagement_score: int = 0
    week: int = 0
    year: int = 0
    is_trending: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Firestore document"""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}


@dataclass
class CustomResearchSummary:
    """Custom research summary document schema"""
    id: str
    title: str
    summary: str
    article_ids: List[str]
    focus_areas: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    created_by: str = ""
    audio_url: Optional[str] = None
    voice: Optional[str] = None
    language: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    is_public: bool = False
    view_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Firestore document"""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}


# ============================================================================
# NEWS AGENT SCHEMAS
# ============================================================================

@dataclass
class NewsArticle:
    """News article document schema"""
    id: str
    title: str
    source: str  # NewsSource enum value
    category: str  # NewsCategory enum value
    region: str  # "national" or "world"
    url: str
    published_date: str
    summary: str
    full_content: Optional[str] = None
    has_audio: bool = False
    audio_url: Optional[str] = None
    voice: Optional[str] = None
    audio_language: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    reading_time: int = 0
    importance_score: float = 0.5
    is_breaking: bool = False
    engagement_score: int = 0
    week: int = 0
    year: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Firestore document"""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}


@dataclass
class CustomNewsSummary:
    """Custom news summary document schema"""
    id: str
    title: str
    summary: str
    article_ids: List[str]
    focus_areas: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    created_by: str = ""
    audio_url: Optional[str] = None
    voice: Optional[str] = None
    language: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    is_public: bool = False
    view_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Firestore document"""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}


# ============================================================================
# FIRESTORE COLLECTION DEFINITIONS
# ============================================================================

FIRESTORE_COLLECTION_DEFINITIONS = {
    # Research Agent Collections
    "research_articles": {
        "description": "Research articles from aggregated sources",
        "document_schema": ResearchArticle,
        "indexes": [
            ["published_date", "category"],
            ["week", "year"],
            ["source", "published_date"],
            ["is_trending", "published_date"],
            ["category", "published_date"],
            ["has_audio"],
        ],
    },
    "custom_research_summaries": {
        "description": "Custom research summaries created from article selections",
        "document_schema": CustomResearchSummary,
        "indexes": [
            ["created_at", "created_by"],
            ["is_public", "created_at"],
            ["tags"],
            ["created_by"],
        ],
    },
    # News Agent Collections
    "news_articles": {
        "description": "News articles from multiple sources",
        "document_schema": NewsArticle,
        "indexes": [
            ["published_date", "category"],
            ["week", "year"],
            ["source", "published_date"],
            ["is_breaking", "published_date"],
            ["category", "region"],
            ["region", "published_date"],
            ["importance_score", "published_date"],
            ["has_audio"],
        ],
    },
    "custom_news_summaries": {
        "description": "Custom news summaries created from article selections",
        "document_schema": CustomNewsSummary,
        "indexes": [
            ["created_at", "created_by"],
            ["is_public", "created_at"],
            ["tags"],
            ["created_by"],
        ],
    },
}


# ============================================================================
# DATA VALIDATION RULES
# ============================================================================

DATA_VALIDATION_RULES = {
    # Research Articles Validation
    "research_articles": {
        "title": {
            "type": "string",
            "max_length": 500,
            "required": True,
        },
        "source": {
            "type": "string",
            "enum": [s.value for s in ResearchSource],
            "required": True,
        },
        "category": {
            "type": "string",
            "enum": [c.value for c in ResearchCategory],
            "required": True,
        },
        "summary": {
            "type": "string",
            "max_length": 2000,
            "required": True,
        },
        "keywords": {
            "type": "array",
            "max_length": 50,
            "item_type": "string",
        },
        "article_ids": {
            "type": "array",
            "max_length": 100,
            "item_type": "string",
        },
    },
    # Custom Research Summaries Validation
    "custom_research_summaries": {
        "title": {
            "type": "string",
            "max_length": 500,
            "required": True,
        },
        "summary": {
            "type": "string",
            "max_length": 3000,
            "required": True,
        },
        "article_ids": {
            "type": "array",
            "max_length": 100,
            "item_type": "string",
            "required": True,
        },
        "focus_areas": {
            "type": "array",
            "max_length": 20,
            "item_type": "string",
        },
    },
    # News Articles Validation
    "news_articles": {
        "title": {
            "type": "string",
            "max_length": 500,
            "required": True,
        },
        "source": {
            "type": "string",
            "enum": [s.value for s in NewsSource],
            "required": True,
        },
        "category": {
            "type": "string",
            "enum": [c.value for c in NewsCategory],
            "required": True,
        },
        "region": {
            "type": "string",
            "enum": ["national", "world"],
            "required": True,
        },
        "summary": {
            "type": "string",
            "max_length": 2000,
            "required": True,
        },
        "keywords": {
            "type": "array",
            "max_length": 50,
            "item_type": "string",
        },
        "importance_score": {
            "type": "number",
            "min": 0.0,
            "max": 1.0,
        },
    },
    # Custom News Summaries Validation
    "custom_news_summaries": {
        "title": {
            "type": "string",
            "max_length": 500,
            "required": True,
        },
        "summary": {
            "type": "string",
            "max_length": 3000,
            "required": True,
        },
        "article_ids": {
            "type": "array",
            "max_length": 100,
            "item_type": "string",
            "required": True,
        },
        "focus_areas": {
            "type": "array",
            "max_length": 20,
            "item_type": "string",
        },
    },
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_collection_schema(collection_name: str) -> Optional[Dict[str, Any]]:
    """Get schema definition for a collection"""
    return FIRESTORE_COLLECTION_DEFINITIONS.get(collection_name)


def validate_document(collection_name: str, document: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate a document against collection rules
    
    Returns:
        (is_valid, errors) - tuple with validation result and error list
    """
    rules = DATA_VALIDATION_RULES.get(collection_name, {})
    errors = []
    
    for field_name, rule in rules.items():
        value = document.get(field_name)
        
        # Check required
        if rule.get("required") and (value is None or value == ""):
            errors.append(f"Field '{field_name}' is required")
            continue
        
        if value is None:
            continue
        
        # Check type
        field_type = rule.get("type")
        if field_type == "string" and not isinstance(value, str):
            errors.append(f"Field '{field_name}' must be string")
        elif field_type == "number" and not isinstance(value, (int, float)):
            errors.append(f"Field '{field_name}' must be number")
        elif field_type == "array" and not isinstance(value, list):
            errors.append(f"Field '{field_name}' must be array")
        
        # Check max_length
        if rule.get("max_length") and isinstance(value, (str, list)):
            if len(value) > rule.get("max_length"):
                errors.append(
                    f"Field '{field_name}' exceeds max length {rule.get('max_length')}"
                )
        
        # Check enum
        if rule.get("enum") and value not in rule.get("enum"):
            errors.append(f"Field '{field_name}' has invalid value: {value}")
        
        # Check min/max for numbers
        if field_type == "number":
            if rule.get("min") is not None and value < rule.get("min"):
                errors.append(
                    f"Field '{field_name}' must be >= {rule.get('min')}"
                )
            if rule.get("max") is not None and value > rule.get("max"):
                errors.append(
                    f"Field '{field_name}' must be <= {rule.get('max')}"
                )
    
    return len(errors) == 0, errors
