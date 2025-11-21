"""
Chat API Router with Persistent Memory + Quality Tracking
Tracks response time, tokens, steps, and success rate for each conversation
"""

import os
from fastapi import APIRouter, HTTPException
from typing import Dict
import uuid
import logging
import time

# ADK Imports
from google.adk.agents import Agent
from google.adk.tools import AgentTool, google_search, FunctionTool
from google.adk.runners import InMemoryRunner
from google.adk.models.google_llm import Gemini
from google.adk.code_executors import BuiltInCodeExecutor
from google.genai import types

from models.schemas import ChatRequest, ChatResponse
from database.chat_memory import (
    save_message,
    get_session_history,
    get_user_sessions,
    delete_session,
    get_chat_metrics,
    save_user_preference,
    get_user_preferences
)

# Import Quality Tracker
from database.quality_tracker import QualityTracker, estimate_tokens

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# Model Configuration
MODEL_NAME = os.getenv("AGENT_MODEL", "gemini-2.0-flash-exp")

retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

# Gemini toma la API KEY automáticamente del entorno
gemini_model = Gemini(model=MODEL_NAME, retry_options=retry_config)

# Initialize Quality Tracker
quality_tracker = QualityTracker("ecommerce_agent.db")
logging.info("Quality Tracker Initialized")


# --- Tools ---
def escalate_to_human_support(question: str) -> Dict:
    """Escalates to human support"""
    logging.info(f"--- HUMAN ESCALATION: {question} ---")
    return {
        "status": "success",
        "ticket_id": f"TICKET-{uuid.uuid4().hex[:6]}",
        "message": "A human support agent will contact you shortly."
    }

escalate_tool = FunctionTool(func=escalate_to_human_support)


# --- Agents ---
general_agent = Agent(
    name="GeneralAgent",
    model=gemini_model,
    instruction="You are a friendly customer support agent. Handle greetings and general questions.",
    tools=[escalate_tool],
)

product_agent = Agent(
    name="ProductAgent",
    model=gemini_model,
    instruction="You are a product expert. Use google_search to find real products.",
    tools=[google_search],
)

calculation_agent = Agent(
    name="CalculationAgent",
    model=gemini_model,
    instruction="You are a calculator. Perform math calculations accurately.",
    code_executor=BuiltInCodeExecutor(),
)

coordinator_agent = Agent(
    name="CoordinatorAgent",
    model=gemini_model,
    instruction="""You are a coordinator. Route messages to:
    - GeneralAgent: Greetings, general questions
    - ProductAgent: Product searches
    - CalculationAgent: Math calculations
    """,
    tools=[
        AgentTool(agent=general_agent),
        AgentTool(agent=product_agent),
        AgentTool(agent=calculation_agent),
        escalate_tool,
    ],
)

# --- Endpoints ---

@router.post("/", response_model=ChatResponse)
async def send_message(request: ChatRequest) -> ChatResponse:
    """Handle chat message with persistent memory + quality tracking"""
    
    # Start tracking
    start_time = time.time()
    success = True
    error_occurred = False
    agent_used = "CoordinatorAgent"
    steps_count = 0
    
    try:
        user_query = request.message
        session_id = request.session_id or f"session_{uuid.uuid4().hex[:8]}"
        user_id = request.user_id or session_id
        
        # Load previous messages
        history = get_session_history(session_id, limit=20)
        
        # Build context
        conversation_context = []
        for msg in history[-10:]:
            conversation_context.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Enhanced instruction
        memory_context = ""
        if conversation_context:
            memory_context = "CONVERSATION HISTORY:\n"
            for msg in conversation_context:
                role = "User" if msg["role"] == "user" else "Assistant"
                memory_context += f"{role}: {msg['content']}\n"
            memory_context += "\nIMPORTANT: Use this conversation history.\n\n"
        
        enhanced_instruction = f"""{memory_context}You are a Coordinator agent.
Route user messages to the correct specialist:
1. GeneralAgent: Greetings, general questions
2. ProductAgent: Product searches
3. CalculationAgent: Math calculations

Current user message: {user_query}
"""
        
        # Dynamic Coordinator
        coordinator_with_memory = Agent(
            name="CoordinatorAgent",
            model=gemini_model,
            instruction=enhanced_instruction,
            tools=[
                AgentTool(agent=general_agent),
                AgentTool(agent=product_agent),
                AgentTool(agent=calculation_agent),
                escalate_tool,
            ],
        )
        
        # Runner
        temp_runner = InMemoryRunner(agent=coordinator_with_memory)
        
        # Run
        adk_response_turns = await temp_runner.run(user_query)
        
        # Extract response safely
        try:
            agent_response = adk_response_turns[-1].content.parts[0].text
        except:
            agent_response = str(adk_response_turns)

        # Count steps safely
        try:
            steps_count = len(adk_response_turns)
        except:
            steps_count = 1
        
        # Estimate tokens
        total_text = user_query + agent_response
        tokens_used = estimate_tokens(total_text)
        
        # Save to DB
        save_message(session_id, "user", user_query, user_id)
        save_message(session_id, "assistant", agent_response, user_id)
        
        # Track quality
        response_time = time.time() - start_time
        quality_tracker.track_conversation(
            conversation_id=session_id,
            response_time=response_time,
            tokens_used=tokens_used,
            steps_count=steps_count,
            agent_used=agent_used,
            success=success,
            error_occurred=error_occurred
        )
        
        logging.info(f"Quality tracked: {response_time:.2f}s")
        
        return ChatResponse(
            response=agent_response,
            session_id=session_id,
            user_id=user_id
        )
        
    except Exception as e:
        error_occurred = True
        success = False
        response_time = time.time() - start_time
        
        quality_tracker.track_conversation(
            conversation_id=session_id if 'session_id' in locals() else "error",
            response_time=response_time,
            tokens_used=0,
            steps_count=0,
            agent_used=agent_used,
            success=success,
            error_occurred=error_occurred
        )
        
        logging.error(f"Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> Dict:
    history = get_session_history(session_id)
    return {
        "session_id": session_id,
        "history": history,
        "message_count": len(history)
    }

@router.get("/users/{user_id}/sessions")
async def get_user_session_list(user_id: str) -> Dict:
    sessions = get_user_sessions(user_id)
    return {"user_id": user_id, "sessions": sessions, "total": len(sessions)}

@router.delete("/sessions/{session_id}")
async def delete_session_endpoint(session_id: str) -> Dict:
    delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}

@router.get("/metrics")
async def get_metrics() -> Dict:
    return get_chat_metrics()

@router.get("/quality-metrics")
async def get_quality_metrics(days: int = 7) -> Dict:
    try:
        summary = quality_tracker.get_metrics_summary(days=days)
        by_agent = quality_tracker.get_metrics_by_agent(days=days)
        trends = quality_tracker.get_trends(days=days)
        
        return {
            "summary": summary,
            "by_agent": by_agent.to_dict('records') if not by_agent.empty else [],
            "trends": trends.to_dict('records') if not trends.empty else []
        }
    except Exception as e:
        logging.error(f"Error getting quality metrics: {str(e)}")
        return {"error": str(e)}

@router.post("/users/{user_id}/preferences")
async def save_preferences(user_id: str, preferences: Dict) -> Dict:
    save_user_preference(user_id, preferences)
    return {"status": "saved", "user_id": user_id}

@router.get("/users/{user_id}/preferences")
async def get_preferences(user_id: str) -> Dict:
    prefs = get_user_preferences(user_id)
    return {"user_id": user_id, "preferences": prefs or {}}















































