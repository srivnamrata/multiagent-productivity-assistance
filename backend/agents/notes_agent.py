"""
Notes Agent - Sub-agent for knowledge management and note-taking
Handles note creation, organization, retrieval, searching, and knowledge base management
"""

import asyncio
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import uuid
import json

logger = logging.getLogger(__name__)


class NotesAgent:
    """
    Sub-agent specialized in knowledge management and note-taking operations.
    Handles:
    - Creating notes with structured data
    - Organizing notes with tags and categories
    - Searching notes by keywords, tags, or metadata
    - Retrieving specific notes
    - Updating and deleting notes
    - Summarizing content
    - Linking related notes
    - Managing knowledge base
    """
    
    def __init__(self, knowledge_graph=None, llm_service=None):
        self.knowledge_graph = knowledge_graph
        self.llm_service = llm_service
        self.notes = {}  # note_id -> note data
        self.categories = {}  # category -> list of note_ids
        self.tags_index = {}  # tag -> list of note_ids
    
    async def execute(self, step: Dict[str, Any], previous_results: Dict) -> Dict[str, Any]:
        """
        Execute a notes management step.
        Step types: "create_note", "search_notes", "get_note", "update_note",
                   "delete_note", "summarize_note", "list_notes", "organize_notes"
        """
        step_type = step.get("type")
        
        if step_type == "create_note":
            return await self._create_note(step)
        elif step_type == "search_notes":
            return await self._search_notes(step)
        elif step_type == "get_note":
            return await self._get_note(step)
        elif step_type == "update_note":
            return await self._update_note(step)
        elif step_type == "delete_note":
            return await self._delete_note(step)
        elif step_type == "summarize_note":
            return await self._summarize_note(step)
        elif step_type == "list_notes":
            return await self._list_notes(step)
        elif step_type == "organize_notes":
            return await self._organize_notes(step)
        else:
            return {"status": "unsupported_step_type", "error": f"Unknown step type: {step_type}"}
    
    async def _create_note(self, step: Dict) -> Dict:
        """Create a new note"""
        try:
            note_id = str(uuid.uuid4())
            title = step.get("title", "Untitled Note")
            content = step.get("content", "")
            category = step.get("category", "general")
            tags = step.get("tags", [])
            metadata = step.get("metadata", {})
            
            # Validate required fields
            if not title or not content:
                return {
                    "status": "error",
                    "error": "title and content are required"
                }
            
            note = {
                "note_id": note_id,
                "title": title,
                "content": content,
                "category": category,
                "tags": tags,
                "metadata": metadata,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "word_count": len(content.split()),
                "pinned": False,
                "related_notes": []
            }
            
            # Store the note
            self.notes[note_id] = note
            
            # Index by category
            if category not in self.categories:
                self.categories[category] = []
            self.categories[category].append(note_id)
            
            # Index by tags
            for tag in tags:
                if tag not in self.tags_index:
                    self.tags_index[tag] = []
                self.tags_index[tag].append(note_id)
            
            # Add to knowledge graph if available
            if self.knowledge_graph:
                await self.knowledge_graph.add_entity({
                    "id": note_id,
                    "type": "note",
                    "name": title,
                    "attributes": {
                        "category": category,
                        "tags": tags,
                        "word_count": note["word_count"]
                    }
                })
            
            logger.info(f"✅ Created note: {title} (ID: {note_id})")
            
            return {
                "status": "success",
                "note_id": note_id,
                "title": title,
                "category": category,
                "tags": tags,
                "word_count": note["word_count"],
                "message": f"Note '{title}' created successfully"
            }
        except Exception as e:
            logger.error(f"Error creating note: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _search_notes(self, step: Dict) -> Dict:
        """Search notes by keywords, tags, or category"""
        try:
            query = step.get("query", "").lower()
            tags = step.get("tags", [])
            category = step.get("category")
            limit = step.get("limit", 10)
            
            results = []
            
            for note_id, note in self.notes.items():
                matched = False
                relevance_score = 0
                
                # Check keyword match in title and content
                if query:
                    if query in note["title"].lower():
                        relevance_score += 10
                        matched = True
                    if query in note["content"].lower():
                        relevance_score += 5
                        matched = True
                
                # Check tag match
                if tags:
                    matching_tags = [t for t in tags if t in note["tags"]]
                    if matching_tags:
                        relevance_score += len(matching_tags) * 3
                        matched = True
                
                # Check category match
                if category and note["category"] == category:
                    relevance_score += 5
                    matched = True
                elif category:
                    matched = False
                
                if matched:
                    results.append({
                        "note_id": note_id,
                        "title": note["title"],
                        "content": note["content"][:200] + "..." if len(note["content"]) > 200 else note["content"],
                        "category": note["category"],
                        "tags": note["tags"],
                        "word_count": note["word_count"],
                        "created_at": note["created_at"],
                        "relevance_score": relevance_score
                    })
            
            # Sort by relevance score
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            results = results[:limit]
            
            logger.info(f"✅ Found {len(results)} notes matching search criteria")
            
            return {
                "status": "success",
                "results": results,
                "count": len(results),
                "query": query,
                "filter_tags": tags,
                "filter_category": category
            }
        except Exception as e:
            logger.error(f"Error searching notes: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _get_note(self, step: Dict) -> Dict:
        """Retrieve a specific note by ID"""
        try:
            note_id = step.get("note_id")
            
            if not note_id or note_id not in self.notes:
                return {"status": "error", "error": "Note not found"}
            
            note = self.notes[note_id]
            
            logger.info(f"✅ Retrieved note: {note_id}")
            
            return {
                "status": "success",
                "note": note
            }
        except Exception as e:
            logger.error(f"Error retrieving note: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _update_note(self, step: Dict) -> Dict:
        """Update an existing note"""
        try:
            note_id = step.get("note_id")
            
            if not note_id or note_id not in self.notes:
                return {"status": "error", "error": "Note not found"}
            
            note = self.notes[note_id]
            
            # Update fields if provided
            if "title" in step:
                note["title"] = step["title"]
            if "content" in step:
                note["content"] = step["content"]
                note["word_count"] = len(step["content"].split())
            if "category" in step:
                old_category = note["category"]
                new_category = step["category"]
                # Update category index
                if old_category in self.categories:
                    self.categories[old_category].remove(note_id)
                if new_category not in self.categories:
                    self.categories[new_category] = []
                self.categories[new_category].append(note_id)
                note["category"] = new_category
            if "tags" in step:
                old_tags = note["tags"]
                new_tags = step["tags"]
                # Update tags index
                for tag in old_tags:
                    if tag in self.tags_index:
                        self.tags_index[tag].remove(note_id)
                for tag in new_tags:
                    if tag not in self.tags_index:
                        self.tags_index[tag] = []
                    self.tags_index[tag].append(note_id)
                note["tags"] = new_tags
            if "metadata" in step:
                note["metadata"].update(step["metadata"])
            if "pinned" in step:
                note["pinned"] = step["pinned"]
            
            note["updated_at"] = datetime.now().isoformat()
            
            logger.info(f"✅ Updated note: {note_id}")
            
            return {
                "status": "success",
                "note_id": note_id,
                "note": note,
                "message": "Note updated successfully"
            }
        except Exception as e:
            logger.error(f"Error updating note: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _delete_note(self, step: Dict) -> Dict:
        """Delete a note"""
        try:
            note_id = step.get("note_id")
            
            if not note_id or note_id not in self.notes:
                return {"status": "error", "error": "Note not found"}
            
            note = self.notes[note_id]
            note_title = note.get("title", "Unknown")
            
            # Remove from category index
            category = note.get("category")
            if category in self.categories:
                self.categories[category].remove(note_id)
            
            # Remove from tags index
            for tag in note.get("tags", []):
                if tag in self.tags_index:
                    self.tags_index[tag].remove(note_id)
            
            # Delete the note
            del self.notes[note_id]
            
            logger.info(f"✅ Deleted note: {note_id} ({note_title})")
            
            return {
                "status": "success",
                "note_id": note_id,
                "message": f"Note '{note_title}' deleted successfully"
            }
        except Exception as e:
            logger.error(f"Error deleting note: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _summarize_note(self, step: Dict) -> Dict:
        """Summarize a note's content"""
        try:
            note_id = step.get("note_id")
            max_sentences = step.get("max_sentences", 3)
            
            if not note_id or note_id not in self.notes:
                return {"status": "error", "error": "Note not found"}
            
            note = self.notes[note_id]
            content = note.get("content", "")
            
            # Simple summarization: extract first N sentences
            sentences = content.split(". ")
            summary = ". ".join(sentences[:max_sentences])
            if not summary.endswith("."):
                summary += "."
            
            # If LLM service is available, use it for better summarization
            if self.llm_service:
                try:
                    summary = await self.llm_service.summarize(content, max_sentences)
                except:
                    pass  # Fall back to simple summarization
            
            logger.info(f"✅ Summarized note: {note_id}")
            
            return {
                "status": "success",
                "note_id": note_id,
                "title": note.get("title"),
                "summary": summary,
                "original_word_count": note.get("word_count"),
                "summary_word_count": len(summary.split())
            }
        except Exception as e:
            logger.error(f"Error summarizing note: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _list_notes(self, step: Dict) -> Dict:
        """List notes with optional filtering"""
        try:
            category = step.get("category")
            sort_by = step.get("sort_by", "created_at")  # created_at, updated_at, word_count
            descending = step.get("descending", True)
            limit = step.get("limit", 20)
            
            notes = []
            
            for note_id, note in self.notes.items():
                # Filter by category if specified
                if category and note.get("category") != category:
                    continue
                
                notes.append({
                    "note_id": note_id,
                    "title": note.get("title"),
                    "category": note.get("category"),
                    "tags": note.get("tags"),
                    "word_count": note.get("word_count"),
                    "created_at": note.get("created_at"),
                    "updated_at": note.get("updated_at"),
                    "pinned": note.get("pinned", False)
                })
            
            # Sort notes
            sort_key = sort_by
            if sort_by == "created_at":
                notes.sort(key=lambda x: x["created_at"], reverse=descending)
            elif sort_by == "updated_at":
                notes.sort(key=lambda x: x["updated_at"], reverse=descending)
            elif sort_by == "word_count":
                notes.sort(key=lambda x: x["word_count"], reverse=descending)
            
            # Pin priority: pinned notes first
            notes.sort(key=lambda x: x["pinned"], reverse=True)
            
            notes = notes[:limit]
            
            logger.info(f"✅ Listed {len(notes)} notes")
            
            return {
                "status": "success",
                "notes": notes,
                "count": len(notes),
                "total_available": len(self.notes),
                "category_filter": category,
                "sort_by": sort_by
            }
        except Exception as e:
            logger.error(f"Error listing notes: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _organize_notes(self, step: Dict) -> Dict:
        """Organize notes by suggesting categories and tags"""
        try:
            # Get statistics about current organization
            stats = {
                "total_notes": len(self.notes),
                "categories": {cat: len(notes) for cat, notes in self.categories.items()},
                "total_tags": len(self.tags_index),
                "most_used_tags": sorted(
                    [(tag, len(note_ids)) for tag, note_ids in self.tags_index.items()],
                    key=lambda x: x[1],
                    reverse=True
                )[:10],
                "most_used_categories": sorted(
                    [(cat, len(note_ids)) for cat, note_ids in self.categories.items()],
                    key=lambda x: x[1],
                    reverse=True
                )
            }
            
            logger.info(f"✅ Generated organization statistics")
            
            return {
                "status": "success",
                "organization_stats": stats,
                "suggestions": {
                    "consider_merging": "Consider merging similar tags/categories with low usage",
                    "total_organization": f"Notes organized into {len(self.categories)} categories with {len(self.tags_index)} tags"
                }
            }
        except Exception as e:
            logger.error(f"Error organizing notes: {e}")
            return {"status": "error", "error": str(e)}
