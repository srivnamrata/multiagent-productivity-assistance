"""
Pub/Sub Service for Real-time Agent Communication
Enables Critic Agent to monitor workflow progress in real-time via Google Cloud Pub/Sub.
"""

import json
import asyncio
from typing import Dict, Callable, Optional, Any
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class MockPubSubService:
    """
    Mock Pub/Sub for local development.
    In production, replace with google.cloud.pubsub_v1
    """
    
    def __init__(self):
        self.topics: Dict[str, list] = defaultdict(list)
        self.subscribers: Dict[str, list] = defaultdict(list)
    
    async def publish(self, topic: str, message: Dict[str, Any]):
        """
        Publish a message to a topic.
        Asynchronously notifies all subscribers.
        """
        logger.info(f"📢 Publishing to {topic}: {message}")
        
        self.topics[topic].append(message)
        
        # Notify all subscribers
        tasks = []
        for callback, context in self.subscribers[topic]:
            task = asyncio.create_task(callback(message, context))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def subscribe(self, topic: str, callback: Callable, context: Dict = None):
        """
        Subscribe to a topic.
        Callback is called whenever a message is published.
        """
        logger.info(f"📡 Subscribing to {topic}")
        self.subscribers[topic].append((callback, context or {}))
    
    async def get_topic_messages(self, topic: str) -> list:
        """Retrieve all messages published to a topic"""
        return self.topics.get(topic, [])


class GCPPubSubService:
    """
    Real Google Cloud Pub/Sub Service.
    Use this in production with actual GCP credentials.
    """
    
    def __init__(self, project_id: str):
        from google.cloud import pubsub_v1
        
        self.project_id = project_id
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()
        self.subscriptions: Dict[str, Any] = {}
    
    async def publish(self, topic: str, message: Dict[str, Any]):
        """Publish message to GCP Pub/Sub topic"""
        topic_path = self.publisher.topic_path(self.project_id, topic)
        message_json = json.dumps(message)
        
        future = self.publisher.publish(topic_path, message_json.encode('utf-8'))
        message_id = future.result()
        logger.info(f"Published message {message_id} to {topic}")
    
    async def subscribe(self, topic: str, callback: Callable, context: Dict = None):
        """Subscribe to GCP Pub/Sub topic"""
        subscription_path = self.subscriber.subscription_path(
            self.project_id, f"{topic}-subscription"
        )
        
        def message_callback(message):
            data = json.loads(message.data.decode('utf-8'))
            asyncio.run(callback(data, context or {}))
            message.ack()
        
        streaming_pull_future = self.subscriber.subscribe(
            subscription_path, callback=message_callback
        )
        
        self.subscriptions[topic] = streaming_pull_future
        logger.info(f"Subscribed to {topic}")


def create_pubsub_service(use_mock: bool = True, project_id: str = None) -> MockPubSubService:
    """Factory function to create appropriate Pub/Sub service"""
    if use_mock:
        return MockPubSubService()
    else:
        if not project_id:
            raise ValueError("GCP project_id required for real Pub/Sub")
        return GCPPubSubService(project_id)
