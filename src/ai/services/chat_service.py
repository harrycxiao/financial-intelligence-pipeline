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

from src.ai.agents.financial_chat_agent import (
    financial_chat_agent,
)


async def answer_financial_question(
    message: str,
) -> str:
    """
    Generate a response to a financial question.

    Parameters
    ----------
    message:
        The user's natural-language question.

    Returns
    -------
    str
        The agent's final response.
    """

    result = await financial_chat_agent.run(message)

    return result.output