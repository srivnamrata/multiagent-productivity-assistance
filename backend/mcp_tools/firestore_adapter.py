"""
Firestore Adapter

Handles all Firestore operations for the MCP system
Provides CRUD operations and query capabilities across all collections
"""

import logging
from typing import Dict, List, Any, Optional, Type, Typevar
from datetime import datetime
from abc import ABC, abstractmethod

from firestore_schemas import (
    Task, CalendarEvent, Note, Event, Project, AccessLog, SystemConfig,
    FIRESTORE_COLLECTION_DEFINITIONS, TTL_POLICIES, DATA_VALIDATION_RULES
)

logger = logging.getLogger(__name__)

T = TypeVar('T')  # For generic type hints


class FirestoreAdapter:
    """
    Adapter for Firestore operations
    Provides unified interface for all database operations
    """
    
    def __init__(self, project_id: str = None, use_mock: bool = False):
        """
        Initialize Firestore adapter
        
        Args:
            project_id: GCP project ID
            use_mock: Use mock Firestore for development
        """
        self.project_id = project_id
        self.use_mock = use_mock
        self._client = None
        self._collections_cache = {}
        
        if not use_mock:
            try:
                import firebase_admin
                from firebase_admin import firestore
                
                if not firebase_admin._apps:
                    firebase_admin.initialize_app()
                
                self._client = firestore.client()
                logger.info(f"Initialized Firestore client for project {project_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize Firestore client: {e}. Using mock mode.")
                self.use_mock = True
        
        if self.use_mock:
            self._init_mock_firestore()
    
    def _init_mock_firestore(self) -> None:
        """Initialize mock Firestore for development/testing"""
        self._mock_db = {}
        for collection_name in FIRESTORE_COLLECTION_DEFINITIONS.keys():
            self._mock_db[collection_name] = {}
        logger.info("Initialized mock Firestore for development")
    
    # ========================================================================
    # Generic CRUD Operations
    # ========================================================================
    
    async def create(self, collection: str, document_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a document in a collection
        
        Args:
            collection: Collection name
            document_id: Document ID
            data: Document data
            
        Returns:
            Created document data
        """
        try:
            # Validate data
            self._validate_data(collection, data, check_required=True)
            
            # Add metadata
            doc_data = {
                **data,
                "id": document_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            if self.use_mock:
                self._mock_db[collection][document_id] = doc_data
            else:
                self._client.collection(collection).document(document_id).set(doc_data)
            
            logger.info(f"Created document {document_id} in {collection}")
            return doc_data
            
        except Exception as e:
            logger.error(f"Error creating document in {collection}: {e}")
            raise
    
    async def read(self, collection: str, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Read a document from a collection
        
        Args:
            collection: Collection name
            document_id: Document ID
            
        Returns:
            Document data or None if not found
        """
        try:
            if self.use_mock:
                return self._mock_db[collection].get(document_id)
            else:
                doc = self._client.collection(collection).document(document_id).get()
                return doc.to_dict() if doc.exists else None
                
        except Exception as e:
            logger.error(f"Error reading document {document_id} from {collection}: {e}")
            return None
    
    async def update(self, collection: str, document_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a document in a collection
        
        Args:
            collection: Collection name
            document_id: Document ID
            data: Update data (partial)
            
        Returns:
            Updated document data
        """
        try:
            # Validate data (don't check required as it's partial update)
            self._validate_data(collection, data, check_required=False)
            
            # Add metadata
            update_data = {
                **data,
                "updated_at": datetime.now().isoformat()
            }
            
            if self.use_mock:
                if document_id not in self._mock_db[collection]:
                    raise KeyError(f"Document {document_id} not found")
                self._mock_db[collection][document_id].update(update_data)
                return self._mock_db[collection][document_id]
            else:
                self._client.collection(collection).document(document_id).update(update_data)
                doc = await self.read(collection, document_id)
                return doc
                
        except Exception as e:
            logger.error(f"Error updating document {document_id} in {collection}: {e}")
            raise
    
    async def delete(self, collection: str, document_id: str) -> bool:
        """
        Delete a document from a collection
        
        Args:
            collection: Collection name
            document_id: Document ID
            
        Returns:
            True if deleted successfully
        """
        try:
            if self.use_mock:
                if document_id in self._mock_db[collection]:
                    del self._mock_db[collection][document_id]
                    return True
                return False
            else:
                self._client.collection(collection).document(document_id).delete()
                return True
                
        except Exception as e:
            logger.error(f"Error deleting document {document_id} from {collection}: {e}")
            return False
    
    # ========================================================================
    # Query Operations
    # ========================================================================
    
    async def query(self, collection: str, filters: List[tuple] = None,
                   order_by: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """
        Query documents in a collection
        
        Args:
            collection: Collection name
            filters: List of (field, operator, value) tuples
            order_by: Field to order by
            limit: Maximum number of results
            
        Returns:
            List of matching documents
        """
        try:
            if self.use_mock:
                results = list(self._mock_db[collection].values())
                
                # Apply filters
                if filters:
                    for field, operator, value in filters:
                        results = self._apply_filter(results, field, operator, value)
                
                # Order results
                if order_by:
                    results.sort(key=lambda x: x.get(order_by, ""))
                
                # Limit results
                if limit:
                    results = results[:limit]
                
                return results
            else:
                query = self._client.collection(collection)
                
                # Apply filters
                if filters:
                    for field, operator, value in filters:
                        query = query.where(field, operator, value)
                
                # Order results
                if order_by:
                    query = query.order_by(order_by)
                
                # Limit results
                if limit:
                    query = query.limit(limit)
                
                docs = query.stream()
                return [doc.to_dict() for doc in docs]
                
        except Exception as e:
            logger.error(f"Error querying collection {collection}: {e}")
            return []
    
    async def search(self, collection: str, search_term: str, fields: List[str]) -> List[Dict[str, Any]]:
        """
        Search documents by text in specified fields
        
        Args:
            collection: Collection name
            search_term: Text to search for
            fields: Fields to search in
            
        Returns:
            List of matching documents
        """
        try:
            if self.use_mock:
                results = []
                search_lower = search_term.lower()
                
                for doc_id, doc in self._mock_db[collection].items():
                    for field in fields:
                        if field in doc:
                            field_value = str(doc[field]).lower()
                            if search_lower in field_value:
                                results.append(doc)
                                break
                
                return results
            else:
                # For real Firestore, would use Firestore Search or full-text search
                # For now, query each field separately
                results = []
                query = self._client.collection(collection)
                docs = query.stream()
                
                for doc in docs:
                    doc_dict = doc.to_dict()
                    for field in fields:
                        if field in doc_dict:
                            if search_term.lower() in str(doc_dict[field]).lower():
                                results.append(doc_dict)
                                break
                
                return results
                
        except Exception as e:
            logger.error(f"Error searching collection {collection}: {e}")
            return []
    
    # ========================================================================
    # Collection Operations
    # ========================================================================
    
    async def get_collection_stats(self, collection: str) -> Dict[str, Any]:
        """
        Get statistics for a collection
        
        Args:
            collection: Collection name
            
        Returns:
            Collection statistics
        """
        try:
            if self.use_mock:
                docs = self._mock_db[collection]
                return {
                    "collection": collection,
                    "document_count": len(docs),
                    "size_bytes": sum(len(str(doc).encode()) for doc in docs.values())
                }
            else:
                # Get document count
                docs = self._client.collection(collection).stream()
                doc_list = list(docs)
                
                return {
                    "collection": collection,
                    "document_count": len(doc_list),
                    "size_bytes": sum(len(str(doc.to_dict()).encode()) for doc in doc_list)
                }
                
        except Exception as e:
            logger.error(f"Error getting stats for collection {collection}: {e}")
            return {}
    
    # ========================================================================
    # Task Operations
    # ========================================================================
    
    async def create_task(self, task: Task) -> Dict[str, Any]:
        """Create a task"""
        return await self.create("tasks", task.id, task.to_dict())
    
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task"""
        return await self.read("tasks", task_id)
    
    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a task"""
        return await self.update("tasks", task_id, updates)
    
    async def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        return await self.delete("tasks", task_id)
    
    async def query_tasks(self, query_filters: List[tuple] = None, limit: int = None) -> List[Dict[str, Any]]:
        """Query tasks with filters"""
        return await self.query("tasks", query_filters, order_by="created_at", limit=limit)
    
    # ========================================================================
    # Calendar Event Operations
    # ========================================================================
    
    async def create_event(self, event: CalendarEvent) -> Dict[str, Any]:
        """Create a calendar event"""
        return await self.create("calendar_events", event.id, event.to_dict())
    
    async def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get a calendar event"""
        return await self.read("calendar_events", event_id)
    
    async def update_event(self, event_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a calendar event"""
        return await self.update("calendar_events", event_id, updates)
    
    async def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event"""
        return await self.delete("calendar_events", event_id)
    
    async def query_events(self, query_filters: List[tuple] = None, limit: int = None) -> List[Dict[str, Any]]:
        """Query calendar events"""
        return await self.query("calendar_events", query_filters, order_by="start_time", limit=limit)
    
    # ========================================================================
    # Note Operations
    # ========================================================================
    
    async def create_note(self, note: Note) -> Dict[str, Any]:
        """Create a note"""
        return await self.create("notes", note.id, note.to_dict())
    
    async def get_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        """Get a note"""
        return await self.read("notes", note_id)
    
    async def update_note(self, note_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a note"""
        return await self.update("notes", note_id, updates)
    
    async def delete_note(self, note_id: str) -> bool:
        """Delete a note"""
        return await self.delete("notes", note_id)
    
    async def search_notes(self, search_term: str, limit: int = None) -> List[Dict[str, Any]]:
        """Search notes by text"""
        results = await self.search("notes", search_term, ["title", "content", "tags"])
        if limit:
            results = results[:limit]
        return results
    
    # ========================================================================
    # Event (Audit Trail) Operations
    # ========================================================================
    
    async def create_event_log(self, event: Event) -> Dict[str, Any]:
        """Create an event log (audit trail)"""
        return await self.create("events", event.id, event.to_dict())
    
    async def get_event_log(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get an event log"""
        return await self.read("events", event_id)
    
    async def query_event_logs(self, query_filters: List[tuple] = None, limit: int = None) -> List[Dict[str, Any]]:
        """Query event logs"""
        return await self.query("events", query_filters, order_by="timestamp", limit=limit)
    
    # ========================================================================
    # Access Log Operations
    # ========================================================================
    
    async def create_access_log(self, access_log: AccessLog) -> Dict[str, Any]:
        """Create an access log"""
        return await self.create("access_logs", access_log.id, access_log.to_dict())
    
    async def query_access_logs(self, user_id: str = None, resource_id: str = None,
                               limit: int = None) -> List[Dict[str, Any]]:
        """Query access logs"""
        filters = []
        if user_id:
            filters.append(("user_id", "==", user_id))
        if resource_id:
            filters.append(("resource_id", "==", resource_id))
        
        return await self.query("access_logs", filters or None, order_by="timestamp", limit=limit)
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def _validate_data(self, collection: str, data: Dict[str, Any], check_required: bool = True) -> bool:
        """Validate data against collection schema"""
        if collection not in DATA_VALIDATION_RULES:
            return True
        
        rules = DATA_VALIDATION_RULES[collection]
        
        # Check required fields
        if check_required and "required" in rules:
            required = rules["required"]
            missing = [field for field in required if field not in data and field != "id"]
            if missing:
                raise ValueError(f"Missing required fields: {missing}")
        
        return True
    
    def _apply_filter(self, documents: List[Dict[str, Any]], field: str,
                     operator: str, value: Any) -> List[Dict[str, Any]]:
        """Apply filter to documents (for mock Firestore)"""
        filtered = []
        
        for doc in documents:
            doc_value = doc.get(field)
            
            if operator == "==":
                if doc_value == value:
                    filtered.append(doc)
            elif operator == "<":
                if doc_value < value:
                    filtered.append(doc)
            elif operator == "<=":
                if doc_value <= value:
                    filtered.append(doc)
            elif operator == ">":
                if doc_value > value:
                    filtered.append(doc)
            elif operator == ">=":
                if doc_value >= value:
                    filtered.append(doc)
            elif operator == "!=":
                if doc_value != value:
                    filtered.append(doc)
            elif operator == "in":
                if doc_value in value:
                    filtered.append(doc)
            elif operator == "array-contains":
                if isinstance(doc_value, list) and value in doc_value:
                    filtered.append(doc)
        
        return filtered
    
    async def initialize_collections(self) -> None:
        """Initialize all collections and indexes"""
        logger.info("Initializing Firestore collections and indexes")
        
        for collection_name, definition in FIRESTORE_COLLECTION_DEFINITIONS.items():
            if self.use_mock:
                logger.info(f"Collection '{collection_name}': {definition['description']}")
            else:
                # In production, indexes would be created automatically
                # This is here for documentation purposes
                logger.info(f"Collection '{collection_name}' ready with indexes: {definition['indexes']}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get connection health status"""
        return {
            "status": "healthy",
            "firestore_mode": "mock" if self.use_mock else "production",
            "project_id": self.project_id,
            "collections_count": len(FIRESTORE_COLLECTION_DEFINITIONS)
        }
