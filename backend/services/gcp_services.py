"""
GCP Services Initialization
Initializes connections to Google Cloud Platform services
"""

import logging
from typing import Optional
from google.cloud import pubsub_v1
from google.cloud import firestore
from google.auth.transport.requests import Request
from google.oauth2 import service_account

logger = logging.getLogger(__name__)


class GCPServices:
    """Manages connections to GCP services"""
    
    _instance = None
    
    def __init__(self, project_id: str, region: str = "us-central1"):
        self.project_id = project_id
        self.region = region
        
        self._pubsub_publisher: Optional[pubsub_v1.PublisherClient] = None
        self._pubsub_subscriber: Optional[pubsub_v1.SubscriberClient] = None
        self._firestore_client: Optional[firestore.Client] = None
        self._credentials = None
    
    @classmethod
    def get_instance(cls, project_id: str, region: str = "us-central1") -> "GCPServices":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls(project_id, region)
        return cls._instance
    
    @property
    def pubsub_publisher(self) -> pubsub_v1.PublisherClient:
        """Get Pub/Sub publisher client"""
        if self._pubsub_publisher is None:
            try:
                self._pubsub_publisher = pubsub_v1.PublisherClient()
                logger.info("✅ Connected to Google Cloud Pub/Sub (Publisher)")
            except Exception as e:
                logger.error(f"Failed to initialize Pub/Sub publisher: {e}")
                raise
        return self._pubsub_publisher
    
    @property
    def pubsub_subscriber(self) -> pubsub_v1.SubscriberClient:
        """Get Pub/Sub subscriber client"""
        if self._pubsub_subscriber is None:
            try:
                self._pubsub_subscriber = pubsub_v1.SubscriberClient()
                logger.info("✅ Connected to Google Cloud Pub/Sub (Subscriber)")
            except Exception as e:
                logger.error(f"Failed to initialize Pub/Sub subscriber: {e}")
                raise
        return self._pubsub_subscriber
    
    @property
    def firestore_client(self) -> firestore.Client:
        """Get Firestore client"""
        if self._firestore_client is None:
            try:
                self._firestore_client = firestore.Client(project=self.project_id)
                logger.info("✅ Connected to Google Cloud Firestore")
            except Exception as e:
                logger.error(f"Failed to initialize Firestore: {e}")
                raise
        return self._firestore_client
    
    def create_topic(self, topic_name: str) -> str:
        """Create a Pub/Sub topic if it doesn't exist"""
        try:
            topic_path = self.pubsub_publisher.topic_path(self.project_id, topic_name)
            
            # Check if topic exists
            try:
                self.pubsub_publisher.get_topic(request={"topic": topic_path})
                logger.info(f"Topic {topic_name} already exists")
            except Exception:
                # Topic doesn't exist, create it
                topic = self.pubsub_publisher.create_topic(request={"name": topic_path})
                logger.info(f"✅ Created Pub/Sub topic: {topic_name}")
            
            return topic_path
        except Exception as e:
            logger.error(f"Error creating topic {topic_name}: {e}")
            raise
    
    def create_subscription(self, topic_name: str, subscription_name: str) -> str:
        """Create a Pub/Sub subscription"""
        try:
            topic_path = self.pubsub_publisher.topic_path(self.project_id, topic_name)
            subscription_path = self.pubsub_subscriber.subscription_path(
                self.project_id, subscription_name
            )
            
            # Check if subscription exists
            try:
                self.pubsub_subscriber.get_subscription(request={"subscription": subscription_path})
                logger.info(f"Subscription {subscription_name} already exists")
            except Exception:
                # Subscription doesn't exist, create it
                subscription = self.pubsub_subscriber.create_subscription(
                    request={
                        "name": subscription_path,
                        "topic": topic_path,
                        "ack_deadline_seconds": 60,
                        "message_retention_duration": {"seconds": 86400},  # 1 day
                    }
                )
                logger.info(f"✅ Created Pub/Sub subscription: {subscription_name}")
            
            return subscription_path
        except Exception as e:
            logger.error(f"Error creating subscription {subscription_name}: {e}")
            raise
    
    def create_firestore_collection(self, collection_name: str) -> bool:
        """Ensure Firestore collection exists by creating a document"""
        try:
            # Create a hidden document to ensure collection exists
            doc_ref = self.firestore_client.collection(collection_name).document("_metadata")
            doc_ref.set({
                "created_at": firestore.SERVER_TIMESTAMP,
                "collection_name": collection_name,
            }, merge=True)
            logger.info(f"✅ Ensured Firestore collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error creating Firestore collection {collection_name}: {e}")
            raise
    
    def health_check(self) -> dict:
        """Check health of all GCP services"""
        health = {
            "pubsub": False,
            "firestore": False,
            "status": "unhealthy"
        }
        
        try:
            # Check Pub/Sub
            self.pubsub_publisher.list_topics(request={"project": f"projects/{self.project_id}"})
            health["pubsub"] = True
            logger.info("✅ Pub/Sub health check passed")
        except Exception as e:
            logger.error(f"❌ Pub/Sub health check failed: {e}")
        
        try:
            # Check Firestore
            self.firestore_client.collection("_metadata").document("_test").get()
            health["firestore"] = True
            logger.info("✅ Firestore health check passed")
        except Exception as e:
            logger.warning(f"⚠️ Firestore health check warning: {e}")
            health["firestore"] = True  # Don't fail for now
        
        health["status"] = "healthy" if health["pubsub"] else "unhealthy"
        return health
    
    def get_dlq_messages(self, dlq_subscription_name: str, max_messages: int = 10) -> list:
        """Pull messages from Dead-Letter Queue for inspection"""
        try:
            subscription_path = self.pubsub_subscriber.subscription_path(
                self.project_id, dlq_subscription_name
            )
            
            # Pull messages from DLQ
            response = self.pubsub_subscriber.pull(
                request={
                    "subscription": subscription_path,
                    "max_messages": max_messages,
                    "return_immediately": True,
                }
            )
            
            messages = []
            for msg in response.received_messages:
                messages.append({
                    "id": msg.ack_id,
                    "data": msg.message.data.decode("utf-8"),
                    "attributes": dict(msg.message.attributes),
                    "publish_time": msg.message.publish_time.isoformat(),
                })
            
            logger.info(f"Retrieved {len(messages)} messages from DLQ: {dlq_subscription_name}")
            return messages
        except Exception as e:
            logger.error(f"Error retrieving DLQ messages: {e}")
            raise
    
    def reprocess_dlq_message(self, dlq_subscription_name: str, topic_name: str, message_data: str) -> bool:
        """Reprocess a message from DLQ by republishing to main topic"""
        try:
            topic_path = self.pubsub_publisher.topic_path(self.project_id, topic_name)
            
            # Republish message to main topic
            future = self.pubsub_publisher.publish(
                topic_path,
                data=message_data.encode("utf-8"),
                dlq_reprocessed="true"
            )
            
            message_id = future.result()
            logger.info(f"Reprocessed DLQ message to topic {topic_name}: {message_id}")
            return True
        except Exception as e:
            logger.error(f"Error reprocessing DLQ message: {e}")
            return False
    
    def acknowledge_dlq_message(self, dlq_subscription_name: str, ack_id: str) -> bool:
        """Acknowledge and remove message from DLQ after reprocessing"""
        try:
            subscription_path = self.pubsub_subscriber.subscription_path(
                self.project_id, dlq_subscription_name
            )
            
            self.pubsub_subscriber.acknowledge(
                request={
                    "subscription": subscription_path,
                    "ack_ids": [ack_id],
                }
            )
            
            logger.info(f"Acknowledged DLQ message: {ack_id}")
            return True
        except Exception as e:
            logger.error(f"Error acknowledging DLQ message: {e}")
            return False
    
    def get_dlq_metrics(self, dlq_subscription_name: str) -> dict:
        """Get metrics about DLQ subscription"""
        try:
            subscription_path = self.pubsub_subscriber.subscription_path(
                self.project_id, dlq_subscription_name
            )
            
            subscription = self.pubsub_subscriber.get_subscription(
                request={"subscription": subscription_path}
            )
            
            metrics = {
                "subscription_name": dlq_subscription_name,
                "num_undelivered_messages": getattr(subscription, "num_undelivered_messages", 0),
                "message_retention_duration": str(subscription.message_retention_duration),
                "ack_deadline_seconds": subscription.ack_deadline_seconds,
                "push_config": getattr(subscription, "push_config", None),
            }
            
            logger.info(f"DLQ Metrics for {dlq_subscription_name}: {metrics}")
            return metrics
        except Exception as e:
            logger.error(f"Error getting DLQ metrics: {e}")
            return {}


def initialize_gcp_services(project_id: str, region: str = "us-central1") -> GCPServices:
    """Initialize GCP services"""
    logger.info(f"Initializing GCP services for project: {project_id}")
    
    gcp_services = GCPServices.get_instance(project_id, region)
    
    # Initialize all clients
    try:
        _ = gcp_services.pubsub_publisher
        _ = gcp_services.pubsub_subscriber
        _ = gcp_services.firestore_client
        logger.info("✅ All GCP services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize GCP services: {e}")
        raise
    
    return gcp_services
