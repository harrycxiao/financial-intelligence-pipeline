"""
chat_service.py

Thin service layer for the financial chatbot.

Responsibilities
----------------
- Accept a user's chat message.
- Execute the financial chat agent.
- Return the agent's natural-language response.

This module intentionally contains no financial logic,
database queries, or prompt engineering.

Those responsibilities belong to the deterministic tools
and the financial chat agent.
"""

from pydantic_ai.messages import ModelMessage

conversation_history: list[ModelMessage] = []

from src.ai.agents.financial_chat_agent import (
    financial_chat_agent,
)

async def answer_financial_question(
    message: str,
) -> str:
    global conversation_history

    result = await financial_chat_agent.run(
        user_prompt=message,
        message_history=conversation_history,
    )

    conversation_history = result.all_messages()

    return result.output