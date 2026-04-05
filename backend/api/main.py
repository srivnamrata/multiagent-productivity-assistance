"""
FastAPI Application - Main Entry Point
Defines API endpoints for the Multi-Agent Productivity Assistant.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
from datetime import datetime

# Import agents and services
from agents.orchestrator_agent import OrchestratorAgent, WorkflowRequest
from agents.critic_agent import CriticAgent
from agents.auditor_agent import SecurityAuditorAgent
from agents.debate_engine import MultiAgentDebateEngine, DebateParticipant
from services.llm_service import create_llm_service
from services.knowledge_graph_service import KnowledgeGraphService
from services.pubsub_service import create_pubsub_service
from config import get_config

# Configure logging
logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Multi-Agent Productivity Assistant",
    description="AI-powered workflow orchestration with autonomous planning and execution",
    version="1.0.0"
)

# Load configuration
config = get_config()

# Initialize services
llm_service = create_llm_service(
    use_mock=config.USE_MOCK_LLM,
    project_id=config.GCP_PROJECT_ID,
    model=config.LLM_MODEL
)

pubsub_service = create_pubsub_service(
    use_mock=config.USE_MOCK_PUBSUB,
    project_id=config.GCP_PROJECT_ID
)

knowledge_graph = KnowledgeGraphService(firestore_client=None)

# Initialize agents
critic_agent = CriticAgent(llm_service, knowledge_graph, pubsub_service)
security_auditor = SecurityAuditorAgent(llm_service, knowledge_graph)
orchestrator = OrchestratorAgent(llm_service, critic_agent, knowledge_graph, pubsub_service)

# Register sub-agents (scheduler, task executor, etc.)
# These would be actual agent implementations
class MockSchedulerAgent:
    async def execute(self, step, previous_results):
        logger.info(f"MockSchedulerAgent executing: {step.get('name')}")
        return {"scheduled": True}

class MockTaskAgent:
    async def execute(self, step, previous_results):
        logger.info(f"MockTaskAgent executing: {step.get('name')}")
        return {"task_created": True}

class MockKnowledgeAgent:
    async def execute(self, step, previous_results):
        logger.info(f"MockKnowledgeAgent executing: {step.get('name')}")
        return {"context_gathered": True}

orchestrator.register_sub_agent("scheduler", MockSchedulerAgent())
orchestrator.register_sub_agent("task", MockTaskAgent())
orchestrator.register_sub_agent("knowledge", MockKnowledgeAgent())

# Initialize debate engine with registered agents
agents_for_debate = {
    "security_auditor": security_auditor,
    "knowledge_agent": orchestrator.sub_agents.get("knowledge"),
    "task_agent": orchestrator.sub_agents.get("task"),
    "scheduler_agent": orchestrator.sub_agents.get("scheduler")
}
debate_engine = MultiAgentDebateEngine(agents_for_debate)


# ============================================================================
# API Models
# ============================================================================

class WorkflowRequestModel(BaseModel):
    """API request model for creating a workflow"""
    goal: str
    description: Optional[str] = None
    priority: str = "medium"  # low, medium, high, critical
    deadline: Optional[str] = None
    context: Dict[str, Any] = {}


class WorkflowStatusModel(BaseModel):
    """API response model for workflow status"""
    workflow_id: str
    status: str
    goal: str
    progress: Optional[Dict] = None
    critic_audit: Optional[Dict] = None


# ============================================================================
# API Endpoints
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("🚀 Multi-Agent Productivity Assistant Starting")
    logger.info(f"Environment: {config.__class__.__name__}")
    logger.info(f"Critic Agent Enabled: {config.CRITIC_AGENT_ENABLED}")
    logger.info(f"Security Auditor: ✅ Cross-Agent Vibe-Checking ENABLED")
    logger.info(f"Debate Engine: ✅ Multi-Agent Consensus ENABLED")
    logger.info(f"LLM Service: {'Mock' if config.USE_MOCK_LLM else 'Vertex AI'}")


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {
        "service": "Multi-Agent Productivity Assistant",
        "version": "1.0.0",
        "status": "operational",
        "features": [
            "🧠 Orchestrator Agent - Primary coordinator",
            "🔍 Critic Agent - Proactive goal anticipation & autonomous replanning",
            "🔐 Security & Strategy Auditor - Cross-agent vibe-checking",
            "🗣️ Multi-Agent Debate Engine - Team consensus & voting",
            "📊 Knowledge Graph - Semantic understanding",
            "🔄 Real-time Pub/Sub - Inter-agent communication",
            "🏆 Survival Fitness Function - Rank best team outcomes"
        ],
        "innovation_highlights": [
            "Autonomous agents that think strategically",
            "Trustworthy AI through peer-review",
            "Multi-dimensional safety checks before execution",
            "Team consensus via intelligent debate",
            "Transparency in every decision"
        ]
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "orchestrator": "ready",
            "critic_agent": "running" if config.CRITIC_AGENT_ENABLED else "disabled",
            "knowledge_graph": "ready",
            "pubsub": "connected"
        }
    }


@app.post("/workflows", tags=["Workflows"])
async def create_workflow(request: WorkflowRequestModel):
    """
    Create and execute a new workflow.
    
    The Orchestrator Agent will:
    1. Parse the goal and generate an execution plan
    2. Build a knowledge graph for context
    3. Start the Critic Agent for monitoring
    4. Execute the plan with sub-agents
    5. Handle autonomous replanning if issues are detected
    
    Returns: workflow_id for tracking
    """
    import uuid
    
    workflow_id = str(uuid.uuid4())[:8]
    
    logger.info(f"📋 Creating workflow: {workflow_id}")
    logger.info(f"Goal: {request.goal}")
    
    # Create workflow request
    workflow_request = WorkflowRequest(
        request_id=workflow_id,
        goal=request.goal,
        description=request.description or "",
        priority=request.priority,
        deadline=request.deadline,
        context=request.context,
        created_at=datetime.now().isoformat()
    )
    
    # Process asynchronously (would be in background in production)
    # await orchestrator.process_user_request(workflow_request)
    
    # For demo, just start it
    import asyncio
    asyncio.create_task(orchestrator.process_user_request(workflow_request))
    
    return {
        "workflow_id": workflow_id,
        "status": "created",
        "message": "Workflow created and processing started",
        "goal": request.goal
    }


@app.get("/workflows/{workflow_id}", tags=["Workflows"])
async def get_workflow_status(workflow_id: str):
    """Get the current status of a workflow"""
    
    status = orchestrator.get_workflow_status(workflow_id)
    
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    
    return status


@app.get("/workflows/{workflow_id}/audit", tags=["Workflows"])
async def get_critic_audit(workflow_id: str):
    """
    Get the Critic Agent's audit report for a workflow.
    Shows all issues detected and autonomous replans executed.
    
    This demonstrates the "Proactive Goal Anticipation" feature.
    """
    
    audit_report = critic_agent.get_workflow_audit_report(workflow_id)
    
    if not audit_report:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return {
        "workflow_id": workflow_id,
        "critic_audit": audit_report,
        "replans_executed": len(critic_agent.get_decision_history()),
        "decisions": [
            {
                "reasoning": d.reasoning,
                "efficiency_gain": f"{d.efficiency_gain*100:.1f}%",
                "confidence": f"{d.confidence_score*100:.0f}%",
                "replanned_at": d.replanned_at
            }
            for d in critic_agent.get_decision_history()
        ]
    }


@app.get("/knowledge-graph/export", tags=["Knowledge Graph"])
async def export_knowledge_graph():
    """
    Export the knowledge graph for visualization.
    Shows all entities and their relationships.
    """
    return knowledge_graph.export_graph()


@app.post("/demonstrate-critic-agent", tags=["Demo"])
async def demonstrate_critic():
    """
    Demonstration endpoint showing the Critic Agent in action.
    Creates a sample workflow with issues for the Critic to detect and fix.
    """
    
    demo_workflow_id = "demo-001"
    
    # Create a sample plan with suboptimal steps
    demo_plan = [
        {
            "step_id": 0,
            "name": "Get all calendar events",  # Inefficient: loads all instead of filtering
            "type": "calendar",
            "agent": "scheduler",
            "depends_on": [],
            "timeout_seconds": 60  # Takes too long
        },
        {
            "step_id": 1,
            "name": "Check Bob's availability",
            "type": "search",
            "agent": "knowledge",
            "depends_on": [0],
            "timeout_seconds": 30
        },
        {
            "step_id": 2,
            "name": "Check Alice's availability",  # Can be parallel!
            "type": "search",
            "agent": "knowledge",
            "depends_on": [0],
            "timeout_seconds": 30
        },
        {
            "step_id": 3,
            "name": "Create meeting",
            "type": "calendar",
            "agent": "scheduler",
            "depends_on": [1, 2],
            "timeout_seconds": 30
        }
    ]
    
    logger.info("🎬 Demonstrating Critic Agent capabilities...")
    
    # Start monitoring (Critic will find issues)
    await critic_agent.start_monitoring(demo_workflow_id, demo_plan)
    
    # Simulate progress updates that trigger Critic analysis
    await pubsub_service.publish(
        topic=f"workflow-{demo_workflow_id}-progress",
        message={
            "workflow_id": demo_workflow_id,
            "step_id": 0,
            "step_name": "Get all calendar events",
            "status": "completed",
            "duration_seconds": 45
        }
    )
    
    return {
        "message": "Critic Agent demonstration started",
        "workflow_id": demo_workflow_id,
        "original_plan": demo_plan,
        "critique": "Critic will detect: (1) Inefficient filtering, (2) Bottleneck, (3) Parallelization opportunity",
        "expected_action": "Autonomous replan with ~25% efficiency improvement"
    }


# ============================================================================
# Cross-Agent Vibe-Checking Endpoints (NEW!)
# ============================================================================

@app.post("/actions/vibe-check", tags=["Vibe-Checking"])
async def vibe_check_action(
    executor_agent: str,
    action: Dict[str, Any],
    reasoning: str,
    context: str = ""
):
    """
    🧠 CROSS-AGENT VIBE-CHECK
    
    Before executing a high-stakes action, the Security & Strategy Auditor
    reviews the executor's thought process and assesses:
    
    1. Intent Alignment - Aligned with user's long-term goals?
    2. PII/Safety Check - Is private information being leaked?
    3. Conflict Resolution - Conflicts with previous actions?
    4. Risk Assessment - What's the downside?
    5. Alternative Validation - Are there safer alternatives?
    
    Returns: Audit report with approval/rejection decision
    """
    
    logger.info(f"🔍 Vibe-checking action from {executor_agent}")
    
    audit_report = await security_auditor.audit_action(
        executor_agent=executor_agent,
        action=action,
        reasoning=reasoning,
        previous_context=context
    )
    
    return {
        "vibe_check_id": audit_report.action_id,
        "executor": executor_agent,
        "approval_status": audit_report.approval_status,
        "overall_risk": audit_report.overall_risk.value,
        "Human review required": audit_report.human_review_required,
        "audit_findings": {
            "intent_alignment": {
                "status": audit_report.intent_alignment.severity.value,
                "reason": audit_report.intent_alignment.description
            },
            "pii_safety": {
                "status": audit_report.pii_safety.severity.value,
                "evidence": audit_report.pii_safety.evidence
            },
            "conflict_resolution": {
                "status": audit_report.conflict_resolution.severity.value,
                "conflicts_found": len(audit_report.conflict_resolution.evidence)
            },
            "risk_assessment": {
                "risk_level": audit_report.risk_assessment.severity.value,
                "worst_case": audit_report.risk_assessment.description
            },
            "alternative_validation": {
                "better_alternatives_exist": len(audit_report.alternative_validation.evidence) > 0
            }
        },
        "recommendation": audit_report.final_recommendation,
        "next_steps": "APPROVED - Proceed" if audit_report.approval_status == "approved" 
                      else "ESCALATED - Awaiting human review" if audit_report.approval_status == "escalated"
                      else "CONDITIONAL - Proceed with caution" if audit_report.approval_status == "conditional"
                      else "REJECTED - Do not execute"
    }


@app.post("/debate/initiate", tags=["Multi-Agent Debate"])
async def initiate_agent_debate(
    action: Dict[str, Any],
    executor_agent: str = "executor",
    reasoning: str = "",
    issue_context: str = "High-stakes decision requiring team consensus"
):
    """
    🗣️ MULTI-AGENT DEBATE
    
    When a vibe-check raises concerns, trigger a full inter-agent debate.
    All agents discuss the action and vote on whether to proceed.
    
    The "Survival Fitness Function" ranks solutions by:
    - Support votes: +1.0
    - Conditional support: +0.7
    - Concerns: -0.5
    - Opposition: -1.5
    
    This creates trustworthy autonomous decisions through team consensus.
    """
    
    logger.info(f"🗣️  Initiating debate about: {action.get('name', 'Unknown')}")
    
    debate_session = await debate_engine.debate_high_stakes_action(
        action=action,
        executor_agent=executor_agent,
        executor_reasoning=reasoning,
        issue_context=issue_context
    )
    
    debate_summary = debate_engine.get_debate_summary(debate_session.debate_id)
    
    return {
        "debate_id": debate_session.debate_id,
        "message": "🗣️ Multi-agent debate completed",
        "summary": debate_summary,
        "final_decision": f"{'✅ CONSENSUS REACHED' if debate_session.consensus_reached else '⚠️ No consensus'} "
                         f"(Team Confidence: {debate_session.confidence_score:.0%})"
    }


@app.get("/debate/{debate_id}", tags=["Multi-Agent Debate"])
async def get_debate_details(debate_id: str):
    """
    Get full details of a debate including all arguments and votes.
    Perfect for visualizing team discussion in the UI.
    """
    
    debate_summary = debate_engine.get_debate_summary(debate_id)
    
    if not debate_summary:
        raise HTTPException(status_code=404, detail="Debate not found")
    
    return debate_summary


@app.get("/vibe-check/{check_id}", tags=["Vibe-Checking"])
async def get_vibe_check_report(check_id: str):
    """
    Get the full vibe-check audit report for an action.
    Shows all 5 audit dimensions.
    """
    
    report = security_auditor.get_audit_report(check_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Vibe-check report not found")
    
    return {
        "check_id": report.action_id,
        "executor": report.executor_agent,
        "status": report.approval_status,
        "overall_risk": report.overall_risk.value,
        "audit_concerns": {
            "intent_alignment": {
                "severity": report.intent_alignment.severity.value,
                "description": report.intent_alignment.description,
                "recommendation": report.intent_alignment.recommendation
            },
            "pii_safety": {
                "severity": report.pii_safety.severity.value,
                "pii_found": report.pii_safety.evidence,
                "recommendation": report.pii_safety.recommendation
            },
            "conflict_resolution": {
                "severity": report.conflict_resolution.severity.value,
                "conflicts": report.conflict_resolution.evidence,
                "recommendation": report.conflict_resolution.recommendation
            },
            "risk_assessment": {
                "severity": report.risk_assessment.severity.value,
                "worst_case_scenario": report.risk_assessment.description,
                "mitigation_steps": report.risk_assessment.evidence
            },
            "alternative_validation": {
                "severity": report.alternative_validation.severity.value,
                "alternatives_found": report.alternative_validation.evidence,
                "recommendation": report.alternative_validation.recommendation
            }
        },
        "recommendation": report.final_recommendation,
        "human_review_required": report.human_review_required,
        "audit_duration_ms": report.audit_duration_ms
    }


@app.get("/audit-history", tags=["Vibe-Checking"])
async def get_audit_history(limit: int = 10):
    """
    Get recent vibe-check audit history.
    Shows all actions that have been audited and their approval status.
    """
    
    return {
        "recent_audits": security_auditor.get_audit_history(limit),
        "total_audits_conducted": len(security_auditor.audit_history)
    }


@app.post("/demonstrate-vibe-check", tags=["Demo"])
async def demonstrate_vibe_check():
    """
    🎬 DEMONSTRATION: Cross-Agent Vibe-Checking in Action
    
    Shows how the system catches potentially risky actions and
    requires team consensus before execution.
    """
    
    # Scenario 1: A risky action that gets flagged
    risky_action = {
        "id": "action-risky-001",
        "name": "Transfer $50,000 to external account",
        "type": "financial",
        "amount": 50000,
        "target": "external-account-unknown@bank.com"
    }
    
    logger.info("🎬 Demo: Vibe-checking risky action")
    
    audit_report = await security_auditor.audit_action(
        executor_agent="payment_agent",
        action=risky_action,
        reasoning="User requested large transfer",
        previous_context="User normally makes <$5K transfers"
    )
    
    # Scenario 2: A safe action that gets approved
    safe_action = {
        "id": "action-safe-001",
        "name": "Create new task: Review project budget",
        "type": "task",
        "priority": "high"
    }
    
    audit_report_safe = await security_auditor.audit_action(
        executor_agent="task_agent",
        action=safe_action,
        reasoning="User needs to prepare for quarterly review",
        previous_context="User creates budgeting tasks regularly"
    )
    
    return {
        "demonstration": "Cross-Agent Vibe-Checking",
        "scenarios_tested": [
            {
                "name": "High-Risk Financial Transfer",
                "action": risky_action,
                "approval_status": audit_report.approval_status,
                "risk_level": audit_report.overall_risk.value,
                "explanation": "⚠️ Large transfer to unknown account triggers safety concerns",
                "requires_debate": audit_report.human_review_required
            },
            {
                "name": "Safe Task Creation",
                "action": safe_action,
                "approval_status": audit_report_safe.approval_status,
                "risk_level": audit_report_safe.overall_risk.value,
                "explanation": "✅ Routine task with no safety concerns",
                "requires_debate": audit_report_safe.human_review_required
            }
        ],
        "key_insight": "The auditor gauges both intent and safety, ensuring autonomous "
                      "actions align with user goals and security policies"
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if config.API_DEBUG else "An error occurred"
        }
    )


# ============================================================================
# Start the server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host=config.API_HOST,
        port=config.API_PORT,
        debug=config.API_DEBUG,
        log_level=config.LOG_LEVEL.lower()
    )
