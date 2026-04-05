"""
LLM Service - Integration with Google Vertex AI
Provides language model capabilities for agents to understand requests and generate plans.
"""

import json
import logging
from typing import Optional, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMService(ABC):
    """Abstract base class for LLM services"""
    
    @abstractmethod
    async def call(self, prompt: str, **kwargs) -> str:
        """Call the LLM with a prompt"""
        pass


class MockLLMService(LLMService):
    """
    Mock LLM for local development and testing.
    Returns realistic mock responses.
    """
    
    async def call(self, prompt: str, **kwargs) -> str:
        """Return mock responses based on prompt content"""
        
        # For execution plan generation
        if "execution plan" in prompt.lower():
            return json.dumps({
                "goal": "Execute workflow",
                "total_steps": 3,
                "steps": [
                    {
                        "step_id": 0,
                        "name": "Prepare context",
                        "type": "note",
                        "agent": "knowledge",
                        "depends_on": [],
                        "timeout_seconds": 10
                    },
                    {
                        "step_id": 1,
                        "name": "Schedule meeting",
                        "type": "calendar",
                        "agent": "scheduler",
                        "depends_on": [0],
                        "timeout_seconds": 20
                    },
                    {
                        "step_id": 2,
                        "name": "Create task",
                        "type": "task",
                        "agent": "task",
                        "depends_on": [],
                        "timeout_seconds": 10
                    }
                ]
            })
        
        # For revised plans
        if "revised plan" in prompt.lower():
            return json.dumps({
                "revised_plan": [
                    {
                        "step_id": 0,
                        "name": "Quick context check",
                        "type": "note",
                        "agent": "knowledge",
                        "depends_on": [],
                        "timeout_seconds": 5
                    },
                    {
                        "step_id": 1,
                        "name": "Find free time slot",
                        "type": "calendar",
                        "agent": "scheduler",
                        "depends_on": [0],
                        "timeout_seconds": 15
                    }
                ],
                "explanation": "Optimized by merging steps and parallelizing"
            })
        
        # For goal drift detection
        if "goal" in prompt.lower() and "on track" in prompt.lower():
            return json.dumps({
                "on_track": True,
                "reasoning": "Progress aligns with original goal",
                "recommended_action": "Continue execution"
            })
        
        # For better approach detection
        if "more efficient" in prompt.lower():
            return json.dumps({
                "has_better_approach": True,
                "efficiency_gain": 0.25,
                "alternative_plan": [],
                "reasoning": "Can parallelize first two steps"
            })
        
        return json.dumps({"response": "OK"})


class VertexAILLMService(LLMService):
    """
    Real Vertex AI implementation.
    Uses Google Cloud Vertex AI for LLM calls.
    """
    
    def __init__(self, project_id: str, location: str = "us-central1", 
                 model: str = "gemini-1.5-pro"):
        import vertexai
        from vertexai.generative_models import GenerativeModel
        
        self.project_id = project_id
        self.location = location
        
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        
        self.model = GenerativeModel(model)
    
    async def call(self, prompt: str, **kwargs) -> str:
        """
        Call Vertex AI Gemini model.
        Supports streaming and structured outputs.
        """
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=kwargs.get("generation_config"),
                safety_settings=kwargs.get("safety_settings")
            )
            
            return response.text
        
        except Exception as e:
            logger.error(f"Vertex AI call failed: {e}")
            raise


def create_llm_service(use_mock: bool = True, 
                       project_id: Optional[str] = None,
                       model: str = "gemini-1.5-pro") -> LLMService:
    """Factory function to create appropriate LLM service"""
    
    if use_mock:
        logger.info("Using Mock LLM Service (development)")
        return MockLLMService()
    else:
        if not project_id:
            raise ValueError("GCP project_id required for Vertex AI")
        logger.info(f"Using Vertex AI LLM Service (project: {project_id})")
        return VertexAILLMService(project_id, model=model)
