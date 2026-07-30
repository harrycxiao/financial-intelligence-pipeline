from pydantic import BaseModel


class ChatRequest(BaseModel):
    """
    Incoming chat request.
    """

    message: str


class ChatResponse(BaseModel):
    """
    Outgoing chat response.
    """

    answer: str