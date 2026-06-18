from __future__ import annotations
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from app.services import nlu, llm

router = APIRouter(prefix="/api/chat", tags=["chat"])

# In-memory conversation store (prototype only -- use a DB/session store in production)
SESSIONS: "dict[str, dict]" = {}


class ChatRequest(BaseModel):
    session_id: str = "default"
    message: str
    language: str = "en"  # "en" or "kn"


class ChatResponse(BaseModel):
    session_id: str
    message: str
    intent: str
    evidence: str
    data: Optional[dict] = None
    suggestions: list[str] = []


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest):
    session = SESSIONS.setdefault(req.session_id, {"context": {}, "history": []})
    result = nlu.handle_query(req.message, context=session["context"])
    session["context"] = result.pop("context", {})

    # Optional LLM polishing of the answer (no-op if no LLM configured)
    enhanced = llm.enhance_response(req.message, result)
    final_answer = enhanced or result["answer"]

    session["history"].append({
        "role": "user",
        "message": req.message,
    })
    session["history"].append({
        "role": "assistant",
        "message": final_answer,
        "intent": result["intent"],
        "evidence": result["evidence"],
    })

    return ChatResponse(
        session_id=req.session_id,
        message=final_answer,
        intent=result["intent"],
        evidence=result["evidence"],
        data=result.get("data"),
        suggestions=result.get("suggestions", []),
    )


@router.get("/{session_id}/history")
def get_history(session_id: str):
    session = SESSIONS.get(session_id, {"history": []})
    return {"session_id": session_id, "history": session["history"]}


@router.delete("/{session_id}")
def clear_session(session_id: str):
    SESSIONS.pop(session_id, None)
    return {"status": "cleared", "session_id": session_id}
