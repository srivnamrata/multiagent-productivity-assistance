"""
Primary Orchestrator Agent
Coordinates all sub-agents and oversees workflow execution.
Manages the high-level strategy while delegating to specialists.
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class WorkflowRequest:
    """User request to execute a workflow"""
    request_id: str
    goal: str
    description: str
    priority: str  # "low", "medium", "high", "critical"
    deadline: Optional[str]
    context: Dict[str, Any]
    created_at: str


class OrchestratorAgent:
    """
    Primary Agent that:
    1. Understands user goals
    2. Breaks them into executable tasks
    3. Coordinates sub-agents (scheduler, task executor, knowledge agent)
    4. Manages the Critic agent feedback loop
    5. Ensures execution and provides progress updates
    """
    
    def __init__(self, llm_service, critic_agent, knowledge_graph, pubsub_service):
        self.llm_service = llm_service
        self.critic_agent = critic_agent
        self.knowledge_graph = knowledge_graph
        self.pubsub = pubsub_service
        self.workflows: Dict[str, Dict] = {}  # workflow_id -> workflow state
        self.sub_agents = {}  # Will be populated with scheduler, task, knowledge agents
    
    def register_sub_agent(self, agent_type: str, agent_instance):
        """Register a sub-agent to be coordinated"""
        self.sub_agents[agent_type] = agent_instance
        logger.info(f"Registered sub-agent: {agent_type}")
    
    async def process_user_request(self, request: WorkflowRequest):
        """
        Main entry point: Process a user request and execute the workflow.
        Step 1: Understand goal
        Step 2: Generate execution plan
        Step 3: Build knowledge graph
        Step 4: Distribute to sub-agents
        Step 5: Monitor via Critic agent
        """
        logger.info(f"🎯 Orchestrator processing request: {request.goal}")
        
        workflow_id = request.request_id
        self.workflows[workflow_id] = {
            "request": request,
            "status": "planning",
            "plan": None,
            "started_at": datetime.now().isoformat()
        }
        
        try:
            # Step 1: Analyze the request and generate execution plan
            execution_plan = await self._generate_execution_plan(request)
            self.workflows[workflow_id]["plan"] = execution_plan
            
            logger.info(f"✅ Generated execution plan for {workflow_id}")
            await self.pubsub.publish(f"workflow-{workflow_id}-status", {
                "status": "plan_ready",
                "steps": len(execution_plan)
            })
            
            # Step 2: Build knowledge graph from the plan
            await self._build_knowledge_graph(workflow_id, execution_plan)
            
            # Step 3: Start Critic agent monitoring
            await self.critic_agent.start_monitoring(workflow_id, execution_plan)
            
            # Step 4: Execute the plan
            self.workflows[workflow_id]["status"] = "executing"
            await self._execute_plan(workflow_id, execution_plan)
            
        except Exception as e:
            logger.error(f"Error processing request {workflow_id}: {e}")
            self.workflows[workflow_id]["status"] = "failed"
            self.workflows[workflow_id]["error"] = str(e)
            await self.pubsub.publish(f"workflow-{workflow_id}-status", {
                "status": "failed",
                "error": str(e)
            })
    
    async def _generate_execution_plan(self, request: WorkflowRequest) -> List[Dict[str, Any]]:
        """
        Use LLM to generate a detailed execution plan from user's goal.
        This is where we break down high-level goals into actionable steps.
        """
        prompt = f"""
        Goal: {request.goal}
        Description: {request.description}
        Priority: {request.priority}
        Deadline: {request.deadline}
        Context: {json.dumps(request.context)}
        
        Generate a detailed execution plan in JSON format with the following structure:
        {{
            "goal": "...",
            "total_steps": X,
            "steps": [
                {{
                    "step_id": 0,
                    "name": "step_name",
                    "type": "calendar|task|note|search|integration",
                    "agent": "scheduler|task|knowledge",
                    "depends_on": [step_ids],
                    "inputs": {{}},
                    "expected_outputs": [],
                    "error_handling": "retry|skip|escalate",
                    "timeout_seconds": 30
                }},
                ...
            ],
            "parallel_groups": [[0, 1], [2], [3, 4]],  # Steps that can run in parallel
            "estimated_duration_seconds": 300
        }}
        """
        
        response = await self.llm_service.call(prompt)
        plan_json = json.loads(response)
        
        return plan_json.get("steps", [])
    
    async def _build_knowledge_graph(self, workflow_id: str, plan: List[Dict]):
        """
        Create nodes and edges in knowledge graph for this workflow.
        This gives the Critic agent context to understand the workflow.
        """
        # Create goal node
        goal_node_id = f"workflow-{workflow_id}-goal"
        await self.knowledge_graph.add_node(
            node_id=goal_node_id,
            node_type="goal",
            label=self.workflows[workflow_id]["request"].goal,
            attributes={
                "workflow_id": workflow_id,
                "priority": self.workflows[workflow_id]["request"].priority
            }
        )
        
        # Create task nodes and dependencies
        for step in plan:
            step_id = f"workflow-{workflow_id}-step-{step['step_id']}"
            
            await self.knowledge_graph.add_node(
                node_id=step_id,
                node_type="task",
                label=step.get("name", f"Step {step['step_id']}"),
                attributes={
                    "type": step.get("type"),
                    "agent": step.get("agent"),
                    "timeout": step.get("timeout_seconds")
                }
            )
            
            # Connect to goal
            await self.knowledge_graph.add_edge(
                source_id=step_id,
                target_id=goal_node_id,
                relationship_type="achieves"
            )
            
            # Connect dependencies
            for dep_id in step.get("depends_on", []):
                dep_step_id = f"workflow-{workflow_id}-step-{dep_id}"
                await self.knowledge_graph.add_edge(
                    source_id=step_id,
                    target_id=dep_step_id,
                    relationship_type="depends_on"
                )
        
        logger.info(f"Built knowledge graph for {workflow_id} with {len(plan)} nodes")
    
    async def _execute_plan(self, workflow_id: str, plan: List[Dict]):
        """
        Execute the plan by delegating steps to appropriate sub-agents.
        Respects dependency constraints and runs parallel steps together.
        """
        workflow = self.workflows[workflow_id]
        completed_steps = set()
        
        # Create execution order respecting dependencies
        pending_steps = {i: step for i, step in enumerate(plan)}
        results = {}
        
        while pending_steps:
            # Find steps with all dependencies completed
            ready_steps = []
            
            for step_id, step in pending_steps.items():
                deps = step.get("depends_on", [])
                if all(d in completed_steps for d in deps):
                    ready_steps.append((step_id, step))
            
            if not ready_steps:
                # Deadlock detected - Critic agent should have caught this
                logger.error(f"Deadlock in workflow {workflow_id}")
                raise Exception("Circular dependency detected")
            
            # Execute ready steps (can be in parallel)
            execution_tasks = []
            for step_id, step in ready_steps:
                task = asyncio.create_task(
                    self._execute_step(workflow_id, step_id, step, results)
                )
                execution_tasks.append(task)
            
            # Wait for all ready steps to complete
            step_results = await asyncio.gather(*execution_tasks, return_exceptions=True)
            
            # Process results
            for (step_id, step), result in zip(ready_steps, step_results):
                if isinstance(result, Exception):
                    logger.error(f"Step {step_id} failed: {result}")
                    if step.get("error_handling") != "skip":
                        raise result
                else:
                    results[step_id] = result
                    completed_steps.add(step_id)
                    del pending_steps[step_id]
        
        workflow["status"] = "completed"
        workflow["results"] = results
        logger.info(f"✅ Workflow {workflow_id} completed successfully")
        
        await self.pubsub.publish(f"workflow-{workflow_id}-status", {
            "status": "completed",
            "results": results
        })
    
    async def _execute_step(self, workflow_id: str, step_id: int, 
                           step: Dict, previous_results: Dict) -> Any:
        """
        Execute a single step using the appropriate sub-agent.
        """
        logger.info(f"Executing step {step_id}: {step.get('name')}")
        
        agent_type = step.get("agent")
        if agent_type not in self.sub_agents:
            raise ValueError(f"No sub-agent of type '{agent_type}'")
        
        agent = self.sub_agents[agent_type]
        
        # Publish progress update
        await self.pubsub.publish(f"workflow-{workflow_id}-progress", {
            "workflow_id": workflow_id,
            "step_id": step_id,
            "step_name": step.get("name"),
            "status": "executing",
            "timestamp": datetime.now().isoformat()
        })
        
        try:
            # Execute step with timeout
            result = await asyncio.wait_for(
                agent.execute(step, previous_results),
                timeout=step.get("timeout_seconds", 30)
            )
            
            # Publish completion
            await self.pubsub.publish(f"workflow-{workflow_id}-progress", {
                "workflow_id": workflow_id,
                "step_id": step_id,
                "step_name": step.get("name"),
                "status": "completed",
                "duration_seconds": 5,  # In production, calculate actual duration
                "result_summary": str(result)[:100]
            })
            
            return result
        
        except asyncio.TimeoutError:
            logger.error(f"Step {step_id} timed out")
            raise Exception(f"Step {step_id} timeout exceeded")
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get the current status of a workflow"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {"error": "Workflow not found"}
        
        return {
            "workflow_id": workflow_id,
            "status": workflow.get("status"),
            "goal": workflow.get("request").goal,
            "started_at": workflow.get("started_at"),
            "plan_steps": len(workflow.get("plan") or []),
            "critic_report": self.critic_agent.get_workflow_audit_report(workflow_id)
        }
    
    async def handle_critic_replan(self, workflow_id: str, replan_message: Dict):
        """
        Handle replan decision from Critic agent.
        This is the autonomous replanning feature in action.
        """
        logger.info(f"🔄 Handling replan for workflow {workflow_id}")
        
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return
        
        if replan_message.get("approved_by_critic"):
            logger.info(f"✅ Accepting Critic's replan suggestion")
            # Update workflow with new plan
            workflow["plan"] = replan_message.get("revised_plan")
            workflow["status"] = "replanned"
            
            await self.pubsub.publish(f"workflow-{workflow_id}-replan-accepted", {
                "reasoning": replan_message.get("reasoning"),
                "efficiency_gain": replan_message.get("efficiency_gain")
            })
        else:
            logger.warning(f"Replan rejected by Critic")
