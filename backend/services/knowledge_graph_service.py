"""
Knowledge Graph Service
Maintains semantic relationships between tasks, schedules, notes, and goals.
Critical for the Critic Agent to understand context and detect inefficiencies.
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)



@dataclass
class Node:
    id: str
    node_type: str
    label: str
    attributes: Dict[str, Any]
    created_at: str = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

@dataclass
class Edge:
    source_id: str
    target_id: str
    relationship_type: str
    confidence: float
    metadata: Dict[str, Any] = None
    created_at: str = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if self.metadata is None:
            self.metadata = {}

class KnowledgeGraphService:
    """
    Semantic knowledge graph for understanding task relationships and patterns.
    Used by Critic Agent to:
    - Understand task dependencies
    - Detect conflicts and inefficiencies
    - Find alternative execution paths
    - Understand user goals and priorities
    """
    

    def __init__(self, firestore_client):
        self.firestore = firestore_client

        # In‑memory graph (always available)
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []

        # Safe load
        try:
            if self.firestore:
                asyncio.create_task(self.load_from_database())
        except RuntimeError:
            # Running outside event loop (startup)
            pass

    # -----------------------------------------------------
    # ✅ Safe Firestore Write Helper
    # -----------------------------------------------------
    async def _safe_firestore_write(self, collection: str, doc_id: str, data: dict):
        if not self.firestore:
            logger.warning("⚠️ Firestore disabled — skipping persistence.")
            return

        try:
            await self.firestore.collection(collection).document(doc_id).set(data)
            logger.info(f"✅ Firestore persisted: {collection}/{doc_id}")
        except Exception as e:
            logger.error(f"❌ Firestore write failed: {e}")


    async def add_node(self, node_id: str, node_type: str, label: str, attributes: Dict[str, Any]) -> Node:
        node = Node(id=node_id, node_type=node_type, label=label, attributes=attributes)
        self.nodes[node_id] = node

        await self._safe_firestore_write(
            "knowledge_graph",
            node_id,
            asdict(node)
        )

        return node

    
    async def add_edge(self, source_id: str, target_id: str, relationship_type: str, metadata: Dict = None) -> Edge:
        edge = Edge(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            confidence=0.9,
            metadata=metadata or {}
        )

        self.edges.append(edge)

        await self._safe_firestore_write(
            "knowledge_graph_edges",
            f"{source_id}-{target_id}-{relationship_type}",
            asdict(edge)
        )

        return edge

    
    def get_node(self, node_id: str) -> Optional[Node]:
        """Retrieve a node from the graph"""
        return self.nodes.get(node_id)
    
    def get_related_nodes(self, node_id: str, relationship_type: str = None, 
                         max_depth: int = 2) -> List[Node]:
        """
        Get all nodes related to a given node via BFS traversal.
        Used to understand task context and dependencies.
        """
        visited = set()
        queue = [(node_id, 0)]
        related = []
        
        while queue:
            current_id, depth = queue.pop(0)
            
            if current_id in visited or depth > max_depth:
                continue
            
            visited.add(current_id)
            
            # Find all edges from this node
            for edge in self.edges:
                if edge.source_id == current_id:
                    if relationship_type is None or edge.relationship_type == relationship_type:
                        target_node = self.get_node(edge.target_id)
                        if target_node:
                            related.append(target_node)
                            queue.append((edge.target_id, depth + 1))
                
                # Also check reverse edges
                if edge.target_id == current_id:
                    source_node = self.get_node(edge.source_id)
                    if source_node:
                        related.append(source_node)
                        queue.append((edge.source_id, depth + 1))
        
        return [self.get_node(nid) for nid in visited if nid != node_id and nid in self.nodes]
    
    def find_path(self, source_id: str, target_id: str) -> Optional[List[str]]:
        """
        Find shortest path between two nodes using BFS.
        Used to detect circular dependencies.
        """
        visited = set()
        queue = [(source_id, [source_id])]
        
        while queue:
            current_id, path = queue.pop(0)
            
            if current_id == target_id:
                return path
            
            if current_id in visited:
                continue
            visited.add(current_id)
            
            for edge in self.edges:
                if edge.source_id == current_id:
                    next_id = edge.target_id
                    if next_id not in visited:
                        queue.append((next_id, path + [next_id]))
        
        return None
    
    def detect_circular_dependencies(self) -> List[List[str]]:
        """Detect all circular dependencies in the graph"""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node_id: str, path: List[str]):
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for edge in self.edges:
                if edge.source_id == node_id:
                    next_node = edge.target_id
                    
                    if next_node not in visited:
                        dfs(next_node, path + [next_node])
                    elif next_node in rec_stack:
                        # Found a cycle
                        cycle_start = path.index(next_node) if next_node in path else -1
                        if cycle_start != -1:
                            cycle = path[cycle_start:] + [next_node]
                            if cycle not in cycles:
                                cycles.append(cycle)
            
            rec_stack.remove(node_id)
        
        for node_id in self.nodes.keys():
            if node_id not in visited:
                dfs(node_id, [node_id])
        
        return cycles
    
    def get_critical_path(self, goal_node_id: str) -> Optional[List[str]]:
        """
        Find the critical path to achieve a goal (longest path in DAG).
        Used for scheduling optimization.
        """
        # This is simplified; in production use proper DAG algorithm
        goal_node = self.get_node(goal_node_id)
        if not goal_node:
            return None
        
        # Find all nodes that must be completed to achieve this goal
        required = self.get_related_nodes(goal_node_id, "depends_on", max_depth=10)
        
        return [n.id for n in required]
    
    def suggesting_parallel_tasks(self, task_id: str) -> List[str]:
        """
        Find tasks that can be executed in parallel with the given task.
        Used for optimization.
        """
        task = self.get_node(task_id)
        if not task:
            return []
        
        # Find nodes that don't depend on this task and this task doesn't depend on
        independent = []
        for node_id, node in self.nodes.items():
            if node_id == task_id:
                continue
            
            # Check if there's a dependency relationship
            path_forward = self.find_path(task_id, node_id)
            path_backward = self.find_path(node_id, task_id)
            
            if not path_forward and not path_backward:
                independent.append(node_id)
        
        return independent
    
    def get_task_context(self, task_id: str) -> Dict[str, Any]:
        """
        Get comprehensive context for a task including:
        - Related tasks
        - Assigned person
        - Parent goal
        - Timeline constraints
        """
        task = self.get_node(task_id)
        if not task:
            return {}
        
        # Find all relationships
        dependencies = []
        dependent_tasks = []
        assigned_to = None
        parent_goal = None
        related_notes = []
        
        for edge in self.edges:
            if edge.source_id == task_id:
                if edge.relationship_type == "depends_on":
                    dependencies.append(edge.target_id)
                elif edge.relationship_type == "achieves":
                    parent_goal = edge.target_id
                elif edge.relationship_type == "assigned_to":
                    assigned_to = edge.target_id
            
            if edge.target_id == task_id:
                if edge.source_id and edge.relationship_type == "depends_on":
                    dependent_tasks.append(edge.source_id)
                elif edge.relationship_type == "related_to":
                    related_notes.append(edge.source_id)
        
        return {
            "task": asdict(task),
            "dependencies": [asdict(self.get_node(d)) for d in dependencies if self.get_node(d)],
            "dependent_tasks": [asdict(self.get_node(d)) for d in dependent_tasks if self.get_node(d)],
            "assigned_to": assigned_to,
            "parent_goal": asdict(self.get_node(parent_goal)) if parent_goal else None,
            "related_notes": [asdict(self.get_node(n)) for n in related_notes if self.get_node(n)],
            "suggestions": {
                "parallel_tasks": self.suggesting_parallel_tasks(task_id),
                "critical_path": self.get_critical_path(parent_goal) if parent_goal else []
            }
        }
    
    async def load_from_database(self):
        """Load knowledge graph from Firestore"""
        # In production, this would fetch from Firestore
        pass
    
    def export_graph(self) -> Dict[str, Any]:
        """Export graph for visualization and debugging"""
        return {
            "nodes": [asdict(n) for n in self.nodes.values()],
            "edges": [asdict(e) for e in self.edges],
            "cycles": self.detect_circular_dependencies()
        }
