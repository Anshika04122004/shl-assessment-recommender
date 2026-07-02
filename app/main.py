from fastapi import FastAPI

from app.recommender import chat
from app.schemas import ChatRequest, ChatResponse


app = FastAPI(title="SHL Conversational Assessment Recommender")


@app.get("/")
def root() -> dict[str, object]:
    return {
        "service": "SHL Conversational Assessment Recommender",
        "status": "running",
        "required_endpoints": {
            "health": "/health",
            "chat": "/chat",
        },
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest) -> ChatResponse:
    reply, recommendations, end_of_conversation = chat(request.messages)
    return ChatResponse(
        reply=reply,
        recommendations=recommendations,
        end_of_conversation=end_of_conversation,
    )
