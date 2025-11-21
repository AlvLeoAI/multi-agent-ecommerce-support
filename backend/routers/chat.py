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


chat_runner = InMemoryRunner(agent=coordinator_agent)
logging.info("ADK Multi-Agent Runner with SQLite Memory Initialized")


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
        
        # Load previous messages from database
        history = get_session_history(session_id, limit=20)
        
        # Build the conversation history for ADK
        conversation_context = []
        for msg in history[-10:]:  # Last 10 messages
            conversation_context.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Create enhanced instruction for the coordinator
        memory_context = ""
        if conversation_context:
            memory_context = "CONVERSATION HISTORY:\n"
            for msg in conversation_context:
                role = "User" if msg["role"] == "user" else "Assistant"
                memory_context += f"{role}: {msg['content']}\n"
            memory_context += "\nIMPORTANT: Use this conversation history to maintain context and remember user information.\n\n"
        
        # Update coordinator instruction dynamically
        enhanced_instruction = f"""{memory_context}You are a Coordinator agent.
Route user messages to the correct specialist:

1. GeneralAgent: Greetings, general questions, human escalation
2. ProductAgent: Product searches and recommendations  
3. CalculationAgent: Math calculations

CRITICAL: If the user asks about information from the conversation history above, 
you MUST reference that information in your response.

Current user message: {user_query}
"""
        
        # Create a new coordinator with memory context
        
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
        
        # Create temporary runner with memory context
        temp_runner = InMemoryRunner(agent=coordinator_with_memory)
        
        # Run the coordinator
        adk_response_turns = await temp_runner.run(
            user_query
        )
        
        # Extract text from response
        
        try:
            agent_response = adk_response_turns[-1].content.parts[0].text
        except:
             
             agent_response = str(adk_response_turns)

        # Count steps (turns in the conversation)
        try:
            steps_count = len(adk_response_turns
















































