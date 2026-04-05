"""
Configuration Management for Multi-Agent Productivity Assistant
Handles environment-based configuration for local, staging, and production environments.
"""

import os
from typing import Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Application configuration"""
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # GCP Configuration
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")
    GCP_REGION: str = os.getenv("GCP_REGION", "us-central1")
    
    # Service Configuration
    USE_MOCK_LLM: bool = os.getenv("USE_MOCK_LLM", "false").lower() == "true"
    USE_MOCK_PUBSUB: bool = os.getenv("USE_MOCK_PUBSUB", "false").lower() == "true"
    USE_FIRESTORE: bool = os.getenv("USE_FIRESTORE", "false").lower() == "true"
    
    # Vertex AI Configuration
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-1.5-pro")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))
    VERTEX_AI_LOCATION: str = os.getenv("VERTEX_AI_LOCATION", "us-central1")
    
    # Pub/Sub Configuration
    PUBSUB_TOPIC_PREFIX: str = os.getenv("PUBSUB_TOPIC_PREFIX", "productivity-assistant")
    PUBSUB_SUBSCRIPTION_PREFIX: str = os.getenv("PUBSUB_SUBSCRIPTION_PREFIX", "productivity-assistant")
    PUBSUB_ACK_DEADLINE_SECONDS: int = int(os.getenv("PUBSUB_ACK_DEADLINE_SECONDS", "60"))
    PUBSUB_MESSAGE_RETENTION_DURATION: str = os.getenv("PUBSUB_MESSAGE_RETENTION_DURATION", "86400s")  # 1 day
    
    # Dead-Letter Queue (DLQ) Configuration
    DLQ_ENABLED: bool = os.getenv("DLQ_ENABLED", "true").lower() == "true"
    DLQ_TOPIC_PREFIX: str = os.getenv("DLQ_TOPIC_PREFIX", "productivity-assistant-dlq")
    DLQ_MESSAGE_RETENTION_DURATION: str = os.getenv("DLQ_MESSAGE_RETENTION_DURATION", "604800s")  # 7 days
    DLQ_MAX_DELIVERY_ATTEMPTS: int = int(os.getenv("DLQ_MAX_DELIVERY_ATTEMPTS", "5"))
    DLQ_MIN_BACKOFF_SECONDS: int = int(os.getenv("DLQ_MIN_BACKOFF_SECONDS", "10"))
    DLQ_MAX_BACKOFF_SECONDS: int = int(os.getenv("DLQ_MAX_BACKOFF_SECONDS", "600"))
    DLQ_REPROCESS_BATCH_SIZE: int = int(os.getenv("DLQ_REPROCESS_BATCH_SIZE", "10"))
    
    # Firestore Configuration
    FIRESTORE_DATABASE: str = os.getenv("FIRESTORE_DATABASE", "(default)")
    FIRESTORE_COLLECTION_WORKFLOWS: str = "workflows"
    FIRESTORE_COLLECTION_AGENTS: str = "agents"
    FIRESTORE_COLLECTION_DECISIONS: str = "decisions"
    
    # Cloud Logging Configuration
    ENABLE_CLOUD_LOGGING: bool = os.getenv("ENABLE_CLOUD_LOGGING", "true").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Cloud Monitoring Configuration
    ENABLE_CLOUD_MONITORING: bool = os.getenv("ENABLE_CLOUD_MONITORING", "true").lower() == "true"
    METRICS_PREFIX: str = os.getenv("METRICS_PREFIX", "productivity-assistant")
    
    # Cloud Trace Configuration
    ENABLE_CLOUD_TRACE: bool = os.getenv("ENABLE_CLOUD_TRACE", "true").lower() == "true"
    TRACE_SAMPLE_RATE: float = float(os.getenv("TRACE_SAMPLE_RATE", "0.1"))
    
    # Service Configuration
    API_PORT: int = int(os.getenv("PORT", "8000"))
    API_WORKERS: int = int(os.getenv("API_WORKERS", "4"))
    
    # Critic Agent Configuration
    CRITIC_MIN_EFFICIENCY_GAIN: float = float(os.getenv("CRITIC_MIN_EFFICIENCY_GAIN", "0.15"))
    CRITIC_MIN_CONFIDENCE: float = float(os.getenv("CRITIC_MIN_CONFIDENCE", "0.75"))
    CRITIC_MAX_REPLANS_PER_WORKFLOW: int = int(os.getenv("CRITIC_MAX_REPLANS_PER_WORKFLOW", "3"))
    
    # Security Auditor Configuration
    AUDITOR_MIN_CONFIDENCE_THRESHOLD: float = float(os.getenv("AUDITOR_MIN_CONFIDENCE_THRESHOLD", "0.70"))
    AUDITOR_MAX_AUDIT_TIME_SECONDS: float = float(os.getenv("AUDITOR_MAX_AUDIT_TIME_SECONDS", "2.0"))
    
    # Debate Engine Configuration
    DEBATE_MAX_ROUNDS: int = int(os.getenv("DEBATE_MAX_ROUNDS", "4"))
    DEBATE_CONSENSUS_THRESHOLD: float = float(os.getenv("DEBATE_CONSENSUS_THRESHOLD", "0.70"))
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))
    
    # Timeout Configuration
    REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30.0"))
    LLM_TIMEOUT_SECONDS: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "60.0"))
    PUBSUB_TIMEOUT_SECONDS: float = float(os.getenv("PUBSUB_TIMEOUT_SECONDS", "10.0"))
    
    # Performance Configuration
    MAX_CONCURRENT_WORKFLOWS: int = int(os.getenv("MAX_CONCURRENT_WORKFLOWS", "100"))
    MAX_CONCURRENT_LLM_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_LLM_REQUESTS", "10"))
    
    # Feature Flags
    ENABLE_SELF_GOVERNANCE: bool = os.getenv("ENABLE_SELF_GOVERNANCE", "false").lower() == "true"
    ENABLE_AUTO_SCALING: bool = os.getenv("ENABLE_AUTO_SCALING", "true").lower() == "true"
    ENABLE_CACHING: bool = os.getenv("ENABLE_CACHING", "true").lower() == "true"
    
    def validate(self) -> bool:
        """Validate configuration for production"""
        errors = []
        
        if self.ENVIRONMENT == "production":
            if not self.GCP_PROJECT_ID:
                errors.append("GCP_PROJECT_ID is required in production")
            if self.USE_MOCK_LLM:
                errors.append("USE_MOCK_LLM must be False in production")
            if self.USE_MOCK_PUBSUB:
                errors.append("USE_MOCK_PUBSUB must be False in production")
            if not self.ENABLE_CLOUD_LOGGING:
                errors.append("ENABLE_CLOUD_LOGGING must be True in production")
        
        if errors:
            for error in errors:
                logger.error(f"Configuration error: {error}")
            return False
        
        logger.info(f"Configuration validated for {self.ENVIRONMENT} environment")
        return True
    
    def to_dict(self) -> dict:
        """Convert config to dictionary"""
        return {
            "environment": self.ENVIRONMENT,
            "gcp_project_id": self.GCP_PROJECT_ID,
            "gcp_region": self.GCP_REGION,
            "llm_model": self.LLM_MODEL,
            "use_mock_llm": self.USE_MOCK_LLM,
            "use_mock_pubsub": self.USE_MOCK_PUBSUB,
            "use_firestore": self.USE_FIRESTORE,
            "enable_cloud_logging": self.ENABLE_CLOUD_LOGGING,
            "enable_cloud_monitoring": self.ENABLE_CLOUD_MONITORING,
            "enable_cloud_trace": self.ENABLE_CLOUD_TRACE,
        }


def get_config() -> Config:
    """Get configuration instance"""
    config = Config()
    
    # Log non-sensitive configuration
    if os.getenv("ENVIRONMENT") == "development":
        logger.info(f"Configuration loaded: {config.to_dict()}")
    
    return config
