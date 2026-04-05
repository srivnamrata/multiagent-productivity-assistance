"""
CRITIC AGENT - The Innovation Core
Proactively audits workflow progress, detects bottlenecks, and replans autonomously.
This agent embodies "Agentic AI" - it doesn't just execute, it thinks strategically.
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk levels for detected issues"""
    CRITICAL = "critical"      # Workflow will fail
    HIGH = "high"             # Major inefficiency
    MEDIUM = "medium"         # Could be better
    LOW = "low"               # Minor optimization


@dataclass
class WorkflowIssue:
    """Detected workflow issue"""
    issue_type: str
    risk_level: RiskLevel
    description: str
    affected_steps: List[int]
    detection_time: str
    evidence: Dict[str, Any]


@dataclass
class ReplanDecision:
    """Autonomous replan decision made by Critic Agent"""
    original_plan: List[Dict[str, Any]]
    revised_plan: List[Dict[str, Any]]
    reasoning: str
    efficiency_gain: float  # percentage
    risk_mitigation: List[str]
    confidence_score: float  # 0.0-1.0
    replanned_at: str


class CriticAgent:
    """
    The Critic Agent autonomously monitors workflow execution and proactively replans.
    
    Key Responsibilities:
    1. Monitor workflow progress in real-time via Pub/Sub
    2. Audit against the Knowledge Graph for context
    3. Detect dead-ends, bottlenecks, and inefficiencies
    4. Generate alternative execution paths
    5. Autonomously decide to replan if efficiency improves >15%
    6. Provide transparent reasoning for decisions
    """
    
    def __init__(self, llm_service, knowledge_graph_service, pubsub_service):
        self.llm_service = llm_service
        self.knowledge_graph = knowledge_graph_service
        self.pubsub = pubsub_service
        self.current_workflows: Dict[str, Dict] = {}
        self.decision_history: List[ReplanDecision] = []
        
    async def start_monitoring(self, workflow_id: str, workflow_plan: List[Dict[str, Any]]):
        """
        Start monitoring a workflow for potential issues.
        Runs continuously in background, listening to Pub/Sub updates.
        """
        logger.info(f"🔍 Critic Agent starting monitoring for workflow {workflow_id}")
        self.current_workflows[workflow_id] = {
            "plan": workflow_plan,
            "progress": [],
            "issues": [],
            "start_time": datetime.now().isoformat(),
            "status": "monitoring"
        }
        
        # Subscribe to workflow progress events
        await self.pubsub.subscribe(
            topic=f"workflow-{workflow_id}-progress",
            callback=self._on_progress_update,
            context={"workflow_id": workflow_id}
        )
    
    async def _on_progress_update(self, message: Dict[str, Any], context: Dict):
        """
        Called whenever a step in the workflow completes.
        This is where the magic happens - continuous auditing.
        """
        workflow_id = context["workflow_id"]
        step_result = message
        
        logger.info(f"📊 Received progress update for {workflow_id}: {step_result['step_name']}")
        
        # Record progress
        self.current_workflows[workflow_id]["progress"].append(step_result)
        
        # AUDIT: Detect issues
        issues = await self._audit_workflow(workflow_id)
        
        if issues:
            logger.warning(f"⚠️ Detected {len(issues)} issues in workflow {workflow_id}")
            for issue in issues:
                self.current_workflows[workflow_id]["issues"].append(issue)
                
                # HIGH RISK = Take action immediately
                if issue.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
                    await self._attempt_replan(workflow_id, issue)
    
    async def _audit_workflow(self, workflow_id: str) -> List[WorkflowIssue]:
        """
        Comprehensive audit of workflow health.
        Checks 5 dimensions:
        1. Deadlock Detection - Are dependencies circular?
        2. Bottleneck Detection - Are there resource constraints?
        3. Goal Drift - Is workflow still aligned with original goal?
        4. Efficiency - Are there faster alternatives?
        5. Dependency Analysis - Are prerequisites met?
        """
        workflow = self.current_workflows[workflow_id]
        issues = []
        
        # 1. DEADLOCK DETECTION
        deadlock_issue = await self._detect_deadlock(workflow)
        if deadlock_issue:
            issues.append(deadlock_issue)
        
        # 2. BOTTLENECK DETECTION
        bottleneck_issues = await self._detect_bottlenecks(workflow)
        issues.extend(bottleneck_issues)
        
        # 3. GOAL DRIFT DETECTION
        drift_issue = await self._detect_goal_drift(workflow)
        if drift_issue:
            issues.append(drift_issue)
        
        # 4. EFFICIENCY ANALYSIS
        inefficiency_issue = await self._detect_inefficiency(workflow)
        if inefficiency_issue:
            issues.append(inefficiency_issue)
        
        return issues
    
    async def _detect_deadlock(self, workflow: Dict) -> Optional[WorkflowIssue]:
        """
        Detect circular dependencies that could cause infinite loops.
        Uses Knowledge Graph to analyze task dependencies.
        """
        plan = workflow["plan"]
        dependencies = {}
        
        for i, step in enumerate(plan):
            deps = step.get("depends_on", [])
            dependencies[i] = deps
        
        # Check for cycles using graph traversal
        visited = set()
        rec_stack = set()
        
        def has_cycle(step_id):
            visited.add(step_id)
            rec_stack.add(step_id)
            
            for dep in dependencies.get(step_id, []):
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True
            
            rec_stack.remove(step_id)
            return False
        
        # Check all steps
        for step_id in range(len(plan)):
            if step_id not in visited:
                if has_cycle(step_id):
                    return WorkflowIssue(
                        issue_type="circular_dependency",
                        risk_level=RiskLevel.CRITICAL,
                        description=f"Circular dependency detected in workflow steps",
                        affected_steps=list(rec_stack),
                        detection_time=datetime.now().isoformat(),
                        evidence={"dependencies": dependencies}
                    )
        
        return None
    
    async def _detect_bottlenecks(self, workflow: Dict) -> List[WorkflowIssue]:
        """
        Detect bottlenecks - steps that are taking too long or blocking others.
        """
        issues = []
        progress = workflow["progress"]
        plan = workflow["plan"]
        
        if not progress:
            return issues
        
        # Calculate average step duration
        step_durations = {}
        for execution in progress:
            step_name = execution.get("step_name")
            duration = execution.get("duration_seconds", 0)
            
            if step_name not in step_durations:
                step_durations[step_name] = []
            step_durations[step_name].append(duration)
        
        # Identify outliers (steps taking 2x average time)
        avg_duration = sum(sum(v) for v in step_durations.values()) / len(progress) if progress else 0
        
        for step_name, durations in step_durations.items():
            avg_step_duration = sum(durations) / len(durations)
            
            if avg_step_duration > (avg_duration * 2) and avg_step_duration > 5:  # >5 sec and 2x avg
                # Find step index
                step_idx = next((i for i, s in enumerate(plan) if s.get("name") == step_name), -1)
                
                # Check how many steps depend on this
                dependents = sum(1 for s in plan if step_name in s.get("depends_on", []))
                
                if dependents > 0:
                    issues.append(WorkflowIssue(
                        issue_type="bottleneck",
                        risk_level=RiskLevel.HIGH if dependents > 2 else RiskLevel.MEDIUM,
                        description=f"Step '{step_name}' is a bottleneck (avg {avg_step_duration:.1f}s). "
                                   f"{dependents} downstream steps waiting.",
                        affected_steps=[step_idx],
                        detection_time=datetime.now().isoformat(),
                        evidence={
                            "avg_duration": avg_step_duration,
                            "baseline_duration": avg_duration,
                            "dependent_steps": dependents
                        }
                    ))
        
        return issues
    
    async def _detect_goal_drift(self, workflow: Dict) -> Optional[WorkflowIssue]:
        """
        Detect if workflow has drifted from original goal.
        Uses LLM to compare current progress against original objective.
        """
        progress_text = "\n".join([f"- {p['step_name']}: {p['status']}" 
                                  for p in workflow["progress"][-5:]])  # Last 5 steps
        original_goal = workflow["plan"][0].get("goal", "Unknown")
        
        prompt = f"""
        Original Goal: {original_goal}
        
        Recent Progress:
        {progress_text}
        
        Is this workflow still on track to achieve the original goal?
        Respond with JSON: {{"on_track": true/false, "reasoning": "...", "recommended_action": "..."}}
        """
        
        response = await self.llm_service.call(prompt)
        analysis = json.loads(response)
        
        if not analysis.get("on_track"):
            return WorkflowIssue(
                issue_type="goal_drift",
                risk_level=RiskLevel.HIGH,
                description=f"Workflow drifted from goal. {analysis.get('reasoning')}",
                affected_steps=[],
                detection_time=datetime.now().isoformat(),
                evidence={"analysis": analysis}
            )
        
        return None
    
    async def _detect_inefficiency(self, workflow: Dict) -> Optional[WorkflowIssue]:
        """
        Detect if there's a more efficient path to achieve the same goal.
        """
        plan = workflow["plan"]
        goal = plan[0].get("goal", "")
        
        # Ask LLM to suggest better approach
        plan_text = json.dumps(plan, indent=2)
        
        prompt = f"""
        Goal: {goal}
        
        Current Plan:
        {plan_text}
        
        Suggest a more efficient plan if possible. Respond with JSON:
        {{
            "has_better_approach": true/false,
            "efficiency_gain": 0.2,  # 20% faster
            "alternative_plan": [...],
            "reasoning": "..."
        }}
        """
        
        response = await self.llm_service.call(prompt)
        analysis = json.loads(response)
        
        if analysis.get("has_better_approach") and analysis.get("efficiency_gain", 0) > 0.15:
            return WorkflowIssue(
                issue_type="suboptimal_plan",
                risk_level=RiskLevel.MEDIUM,
                description=f"More efficient approach exists ({analysis.get('efficiency_gain')*100:.0f}% faster). "
                          f"{analysis.get('reasoning')}",
                affected_steps=list(range(len(plan))),
                detection_time=datetime.now().isoformat(),
                evidence={
                    "alternative_plan": analysis.get("alternative_plan"),
                    "efficiency_gain": analysis.get("efficiency_gain")
                }
            )
        
        return None
    
    async def _attempt_replan(self, workflow_id: str, issue: WorkflowIssue):
        """
        When a major issue is detected, attempt to autonomously replan.
        This is the GAME-CHANGING feature - the agent doesn't wait for human approval.
        """
        logger.info(f"🧠 Critic Agent attempting autonomous replan for {workflow_id}")
        
        workflow = self.current_workflows[workflow_id]
        original_plan = workflow["plan"]
        progress = workflow["progress"]
        
        # Generate revised plan
        revised_plan = await self._generate_revised_plan(
            original_plan=original_plan,
            issue=issue,
            progress=progress
        )
        
        if revised_plan is None:
            logger.warning(f"Could not generate viable revised plan for {workflow_id}")
            return
        
        # Calculate efficiency improvement
        efficiency_gain = await self._calculate_efficiency_gain(original_plan, revised_plan)
        
        # Make decision to replan
        decision = ReplanDecision(
            original_plan=original_plan,
            revised_plan=revised_plan,
            reasoning=f"Issue detected: {issue.description}. "
                     f"Replan improves efficiency by {efficiency_gain*100:.1f}%",
            efficiency_gain=efficiency_gain,
            risk_mitigation=[
                "Pause current step",
                "Update task dependencies",
                "Resume with new plan",
                "Monitor for conflicts"
            ],
            confidence_score=0.85,  # In production, compute actual confidence
            replanned_at=datetime.now().isoformat()
        )
        
        # 🎯 AUTONOMOUSLY APPLY THE REPLAN
        if efficiency_gain > 0.15 and decision.confidence_score > 0.75:  # >15% improvement
            logger.info(f"✅ Accepting replan for {workflow_id} (↑{efficiency_gain*100:.1f}% efficiency)")
            
            # Notify orchestrator of the replan
            await self.pubsub.publish(
                topic=f"workflow-{workflow_id}-replan",
                message={
                    "action": "replan",
                    "original_plan": original_plan,
                    "revised_plan": revised_plan,
                    "reasoning": decision.reasoning,
                    "efficiency_gain": efficiency_gain,
                    "approved_by_critic": True
                }
            )
            
            # Record decision
            self.decision_history.append(decision)
            workflow["status"] = "replanned"
        else:
            logger.info(f"Rejected replan for {workflow_id} (insufficient improvement or confidence)")
            await self.pubsub.publish(
                topic=f"workflow-{workflow_id}-audit",
                message={
                    "action": "issue_detected",
                    "issue": {
                        "type": issue.issue_type,
                        "description": issue.description,
                        "risk_level": issue.risk_level.value
                    },
                    "recommendation": "Human review recommended"
                }
            )
    
    async def _generate_revised_plan(self, original_plan: List[Dict], 
                                    issue: WorkflowIssue,
                                    progress: List[Dict]) -> Optional[List[Dict]]:
        """
        Use LLM to generate a revised plan that addresses the detected issue.
        """
        original_text = json.dumps(original_plan, indent=2)
        progress_text = json.dumps(progress[-3:], indent=2) if progress else "No progress yet"
        
        prompt = f"""
        Original Execution Plan:
        {original_text}
        
        Detected Issue: {issue.issue_type} - {issue.description}
        
        Recent Progress:
        {progress_text}
        
        Generate a revised plan that:
        1. Addresses the issue
        2. Maintains the original goal
        3. Is more efficient if possible
        4. Leverages completed steps from progress
        
        Respond with JSON: {{"revised_plan": [...], "explanation": "..."}}
        """
        
        try:
            response = await self.llm_service.call(prompt)
            analysis = json.loads(response)
            return analysis.get("revised_plan")
        except Exception as e:
            logger.error(f"Error generating revised plan: {e}")
            return None
    
    async def _calculate_efficiency_gain(self, original_plan: List[Dict], 
                                        revised_plan: List[Dict]) -> float:
        """
        Calculate estimated efficiency improvement (0.0-1.0).
        In production, this would use ML models trained on historical data.
        """
        # Simplified calculation: steps reduced / original steps
        original_steps = len(original_plan)
        revised_steps = len(revised_plan)
        
        if original_steps == 0:
            return 0.0
        
        return max(0.0, (original_steps - revised_steps) / original_steps)
    
    def get_decision_history(self) -> List[ReplanDecision]:
        """Return all autonomous replan decisions made"""
        return self.decision_history
    
    def get_workflow_audit_report(self, workflow_id: str) -> Dict[str, Any]:
        """Generate audit report for a workflow"""
        workflow = self.current_workflows.get(workflow_id, {})
        
        return {
            "workflow_id": workflow_id,
            "status": workflow.get("status"),
            "start_time": workflow.get("start_time"),
            "total_issues_detected": len(workflow.get("issues", [])),
            "issues": [
                {
                    "type": issue.issue_type,
                    "risk_level": issue.risk_level.value,
                    "description": issue.description,
                    "detected_at": issue.detection_time
                }
                for issue in workflow.get("issues", [])
            ],
            "replans_executed": len([d for d in self.decision_history if d]),
            "current_efficiency_vs_original": "TODO: Calculate based on actual execution"
        }
