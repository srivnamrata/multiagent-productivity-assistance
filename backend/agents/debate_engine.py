"""
Multi-Agent Debate & Voting System
Enables agents to discuss high-stakes decisions and reach consensus.
Creates a "Survival Fitness Function" that ranks different solutions.

This is where agents become a true "collaborative team" rather than
independent workers executing in isolation.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class VoteType(Enum):
    """Types of votes agents can cast"""
    SUPPORT = "support"                # Full support
    CONDITIONAL_SUPPORT = "conditional"  # Support with conditions
    NEUTRAL = "neutral"                # No strong opinion
    CONCERN = "concern"                # Has concerns
    OPPOSE = "oppose"                  # Strong disagreement


class DebateParticipant(Enum):
    """Agents that participate in debates"""
    EXECUTOR = "executor"              # Agent proposing action
    SECURITY_AUDITOR = "security_auditor"  # Safety reviewer
    KNOWLEDGE_AGENT = "knowledge_agent"  # Context provider
    TASK_AGENT = "task_agent"          # Task expert
    SCHEDULER_AGENT = "scheduler_agent"  # Timeline expert


@dataclass
class DebateArgument:
    """An agent's argument in the debate"""
    agent: DebateParticipant
    timestamp: str
    position: str
    reasoning: str
    evidence: List[str]
    vote: VoteType
    confidence: float  # 0.0-1.0


@dataclass
class DebateSession:
    """A complete debate about a high-stakes action"""
    debate_id: str
    action_being_debated: Dict[str, Any]
    issue_at_stake: str
    
    arguments: List[DebateArgument]
    
    # Outcome
    consensus_reached: bool
    winning_position: Optional[str]
    dissenting_agents: List[DebateParticipant]
    confidence_score: float  # Overall team consensus (0.0-1.0)
    
    # Metadata
    started_at: str
    concluded_at: Optional[str] = None
    duration_ms: Optional[float] = None


class MultiAgentDebateEngine:
    """
    Orchestrates debates between agents about high-stakes decisions.
    
    When an action is too risky for one agent to decide alone,
    the team debates alternatives and votes on the best one.
    
    The "Survival Fitness Function": 
    Score = (Support Votes × 1.0) + 
            (Conditional Votes × 0.7) - 
            (Concern Votes × 0.5) - 
            (Oppose Votes × 1.5)
    """
    
    def __init__(self, agents_dict: Dict[str, Any]):
        """
        Initialize debate engine with available agents.
        
        agents_dict should contain:
        - "executor": The agent that wants to execute something
        - "security_auditor": The safety reviewer
        - "knowledge_agent": Context/knowledge provider
        - "task_agent": Task expert
        - "scheduler_agent": Timeline expert
        """
        self.agents = agents_dict
        self.debates: Dict[str, DebateSession] = {}
    
    async def debate_high_stakes_action(self, 
                                       action: Dict[str, Any],
                                       executor_agent: Any,
                                       executor_reasoning: str,
                                       issue_context: str = "") -> DebateSession:
        """
        Trigger a full debate about a high-stakes action.
        
        Multi-round debate:
        Round 1: Executor presents proposal
        Round 2: Each agent responds with their position
        Round 3: Rebuttals and clarifications
        Round 4: Final vote
        """
        
        import uuid
        import time
        
        debate_id = f"debate-{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        
        logger.info(f"🗣️  Starting debate: {debate_id}")
        logger.info(f"   Issue: {issue_context}")
        
        # Initialize debate session
        debate = DebateSession(
            debate_id=debate_id,
            action_being_debated=action,
            issue_at_stake=issue_context,
            arguments=[],
            consensus_reached=False,
            winning_position=None,
            dissenting_agents=[],
            confidence_score=0.0,
            started_at=datetime.now().isoformat()
        )
        
        # ROUND 1: Executor presents their case
        logger.info("📢 ROUND 1: Executor Proposal")
        executor_arg = await self._get_executor_argument(
            executor_agent, executor_reasoning, action
        )
        debate.arguments.append(executor_arg)
        
        # ROUND 2: Each agent reviews and votes
        logger.info("🤔 ROUND 2: Agent Review & Voting")
        participant_arguments = await self._gather_agent_positions(
            args_tuple=(
                executor_agent, action, executor_reasoning, issue_context
            )
        )
        debate.arguments.extend(participant_arguments)
        
        # ROUND 3: Interactive debate (rebuttals)
        logger.info("💬 ROUND 3: Debate & Clarifications")
        rebuttal_arguments = await self._conduct_rebuttals(
            debate, executor_agent
        )
        debate.arguments.extend(rebuttal_arguments)
        
        # ROUND 4: Final voting
        logger.info("🗳️  ROUND 4: Final Vote")
        votes = [arg.vote for arg in debate.arguments]
        
        # Analyze debate results
        debate.consensus_reached, debate.winning_position, \
        debate.dissenting_agents, debate.confidence_score = \
            self._analyze_debate(debate.arguments)
        
        # Calculate debate duration
        debate.concluded_at = datetime.now().isoformat()
        debate.duration_ms = (time.time() - start_time) * 1000
        
        # Store debate
        self.debates[debate_id] = debate
        
        logger.info(f"✅ Debate concluded: {debate.consensus_reached}")
        logger.info(f"   Consensus: {debate.confidence_score:.0%}")
        logger.info(f"   Duration: {debate.duration_ms:.0f}ms")
        
        return debate
    
    async def _get_executor_argument(self, executor_agent: Any,
                                     reasoning: str,
                                     action: Dict) -> DebateArgument:
        """
        Get the executor agent's initial proposal.
        """
        
        return DebateArgument(
            agent=DebateParticipant.EXECUTOR,
            timestamp=datetime.now().isoformat(),
            position=f"I propose executing: {action.get('name', 'Unknown action')}",
            reasoning=reasoning,
            evidence=action.get("evidence", []),
            vote=VoteType.SUPPORT,  # Executor always supports their own proposal
            confidence=0.85
        )
    
    async def _gather_agent_positions(self, 
                                      args_tuple: tuple) -> List[DebateArgument]:
        """
        Get voting positions from all agents.
        """
        executor_agent, action, reasoning, context = args_tuple
        arguments = []
        
        # Security & Strategy Auditor
        if "security_auditor" in self.agents:
            auditor_arg = await self._get_auditor_position(
                action, reasoning, context
            )
            arguments.append(auditor_arg)
        
        # Knowledge Agent
        if "knowledge_agent" in self.agents:
            knowledge_arg = await self._get_knowledge_position(
                action, reasoning, context
            )
            arguments.append(knowledge_arg)
        
        # Task Agent  
        if "task_agent" in self.agents:
            task_arg = await self._get_task_position(
                action, reasoning, context
            )
            arguments.append(task_arg)
        
        # Scheduler Agent
        if "scheduler_agent" in self.agents:
            scheduler_arg = await self._get_scheduler_position(
                action, reasoning, context
            )
            arguments.append(scheduler_arg)
        
        return arguments
    
    async def _get_auditor_position(self, action: Dict, 
                                   reasoning: str,
                                   context: str) -> DebateArgument:
        """Security Auditor's assessment"""
        
        # This would call the security auditor agent
        # For now, return a mock decision
        
        safety_concerns = len([v for k, v in action.items() 
                              if isinstance(v, str) and 
                              any(x in v.lower() 
                                  for x in ["delete", "transfer", "send"])])
        
        if safety_concerns > 0:
            vote = VoteType.CONCERN
            position = "⚠️  I have safety concerns about this action"
            confidence = 0.8
        else:
            vote = VoteType.CONDITIONAL_SUPPORT
            position = "✅ Safety profile seems acceptable with monitoring"
            confidence = 0.85
        
        return DebateArgument(
            agent=DebateParticipant.SECURITY_AUDITOR,
            timestamp=datetime.now().isoformat(),
            position=position,
            reasoning="Assessed for PII leaks, reversibility, and worst-case risk",
            evidence=["PII check: PASS", "Reversibility: HIGH", "Risk level: MEDIUM"],
            vote=vote,
            confidence=confidence
        )
    
    async def _get_knowledge_position(self, action: Dict,
                                      reasoning: str,
                                      context: str) -> DebateArgument:
        """Knowledge Agent's context assessment"""
        
        # Check for goal alignment
        is_aligned = "goal" not in context or "aligned" in context.lower()
        
        if is_aligned:
            vote = VoteType.SUPPORT
            position = "✅ This action aligns with our knowledge base and goals"
            confidence = 0.8
        else:
            vote = VoteType.CONCERN
            position = "⚠️  This may conflict with what we know about the user's preferences"
            confidence = 0.75
        
        return DebateArgument(
            agent=DebateParticipant.KNOWLEDGE_AGENT,
            timestamp=datetime.now().isoformat(),
            position=position,
            reasoning="Assessed context, historical data, and goal alignment",
            evidence=["Consistency check: PASS", "User preference alignment: HIGH"],
            vote=vote,
            confidence=confidence
        )
    
    async def _get_task_position(self, action: Dict,
                                reasoning: str,
                                context: str) -> DebateArgument:
        """Task Agent's domain expertise"""
        
        # Simple heuristic: shorter actions are better
        action_size = sum(len(str(v)) for v in action.values())
        
        if action_size < 1000:
            vote = VoteType.SUPPORT
            position = "✅ Task execution is feasible and well-scoped"
            confidence = 0.85
        else:
            vote = VoteType.CONCERN
            position = "⚠️  This task seems complex - might benefit from decomposition"
            confidence = 0.7
        
        return DebateArgument(
            agent=DebateParticipant.TASK_AGENT,
            timestamp=datetime.now().isoformat(),
            position=position,
            reasoning="Assessed task complexity, dependencies, and feasibility",
            evidence=["Scope: REASONABLE", "Dependencies: CLEAR"],
            vote=vote,
            confidence=confidence
        )
    
    async def _get_scheduler_position(self, action: Dict,
                                      reasoning: str,
                                      context: str) -> DebateArgument:
        """Scheduler Agent's timeline assessment"""
        
        vote = VoteType.CONDITIONAL_SUPPORT
        position = "⏰ Timing looks acceptable, but monitor for deadline conflicts"
        confidence = 0.8
        
        return DebateArgument(
            agent=DebateParticipant.SCHEDULER_AGENT,
            timestamp=datetime.now().isoformat(),
            position=position,
            reasoning="Assessed resource availability and timeline constraints",
            evidence=["Calendar: FREE", "Priority conflicts: NONE"],
            vote=vote,
            confidence=confidence
        )
    
    async def _conduct_rebuttals(self, debate: DebateSession,
                                executor_agent: Any) -> List[DebateArgument]:
        """
        Allow agents to rebut each other's arguments (simplified for hackathon).
        """
        
        # For this implementation, we'll keep rebuttals minimal
        # In production, this would be a full multi-turn conversation
        
        rebuttals = []
        
        # If there are concerns, executor can clarify
        concerns = [arg for arg in debate.arguments 
                   if arg.vote in [VoteType.CONCERN, VoteType.OPPOSE]]
        
        if concerns:
            executor_rebuttal = DebateArgument(
                agent=DebateParticipant.EXECUTOR,
                timestamp=datetime.now().isoformat(),
                position="I understand your concerns and want to address them",
                reasoning="Responding to feedback from peers",
                evidence=[c.agent.value for c in concerns],
                vote=VoteType.SUPPORT,
                confidence=0.85
            )
            rebuttals.append(executor_rebuttal)
        
        return rebuttals
    
    def _analyze_debate(self, arguments: List[DebateArgument]) -> tuple:
        """
        Analyze debate results and determine consensus.
        
        Returns: (consensus_reached, winning_position, dissenting_agents, confidence)
        """
        
        # Count votes
        vote_counts = {
            VoteType.SUPPORT: 0,
            VoteType.CONDITIONAL_SUPPORT: 0,
            VoteType.NEUTRAL: 0,
            VoteType.CONCERN: 0,
            VoteType.OPPOSE: 0
        }
        
        dissenting = []
        
        for arg in arguments:
            vote_counts[arg.vote] += 1
            if arg.vote in [VoteType.CONCERN, VoteType.OPPOSE]:
                dissenting.append(arg.agent)
        
        total_votes = sum(vote_counts.values())
        
        # Calculate "Survival Fitness Score"
        # Higher score = better action quality and safety
        fitness_score = (
            (vote_counts[VoteType.SUPPORT] * 1.0) +
            (vote_counts[VoteType.CONDITIONAL_SUPPORT] * 0.7) -
            (vote_counts[VoteType.CONCERN] * 0.5) -
            (vote_counts[VoteType.OPPOSE] * 1.5)
        )
        
        # Normalize confidence to 0.0-1.0
        max_fitness = total_votes  # Best case: all support (with max weight)
        confidence = max(0.0, min(1.0, fitness_score / max_fitness if max_fitness > 0 else 0.5))
        
        # Determine consensus
        support_percentage = vote_counts[VoteType.SUPPORT] / total_votes if total_votes > 0 else 0
        
        # Consensus requires 70%+ support or conditional support
        supportive_votes = (vote_counts[VoteType.SUPPORT] + 
                           vote_counts[VoteType.CONDITIONAL_SUPPORT])
        consensus = supportive_votes / total_votes >= 0.7 if total_votes > 0 else True
        
        # Winning position
        winning_position = "APPROVE WITH CAUTION" if consensus else "REQUIRES DISCUSSION"
        
        return consensus, winning_position, dissenting, confidence
    
    def get_debate_summary(self, debate_id: str) -> Optional[Dict[str, Any]]:
        """Get a human-readable summary of a debate"""
        debate = self.debates.get(debate_id)
        if not debate:
            return None
        
        # Categorize arguments
        support_args = [arg for arg in debate.arguments 
                       if arg.vote == VoteType.SUPPORT]
        conditional_args = [arg for arg in debate.arguments 
                           if arg.vote == VoteType.CONDITIONAL_SUPPORT]
        concern_args = [arg for arg in debate.arguments 
                       if arg.vote == VoteType.CONCERN]
        oppose_args = [arg for arg in debate.arguments 
                      if arg.vote == VoteType.OPPOSE]
        
        return {
            "debate_id": debate_id,
            "action": debate.action_being_debated.get("name", "Unknown"),
            "issue": debate.issue_at_stake,
            "duration_ms": debate.duration_ms,
            "consensus": debate.consensus_reached,
            "overall_confidence": f"{debate.confidence_score:.0%}",
            "votes": {
                "support": len(support_args),
                "conditional_support": len(conditional_args),
                "concern": len(concern_args),
                "oppose": len(oppose_args)
            },
            "dissenting_agents": [agent.value for agent in debate.dissenting_agents],
            "arguments": [
                {
                    "agent": arg.agent.value,
                    "vote": arg.vote.value,
                    "position": arg.position,
                    "confidence": arg.confidence
                }
                for arg in debate.arguments
            ],
            "recommendation": f"{'✅ APPROVED' if debate.consensus_reached else '⚠️  NEEDS REVIEW'}"
        }
