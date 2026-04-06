import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from database import save_message, get_messages
from llm import stream_chat_response

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    conversation_id: str


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/chat")
async def chat(body: ChatRequest, request: Request):
    pool = request.app.state.db_pool

    try:
        # Save user message
        await save_message(pool, body.conversation_id, "user", body.message)

        # Fetch conversation history for context
        history = await get_messages(pool, body.conversation_id)
    except Exception as e:
        logger.exception("Failed to process chat request")
        return {"error": str(e)}

    async def event_stream():
        full_response = ""
        try:
            async for token in stream_chat_response(history):
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        # Save the complete assistant message
        if full_response:
            saved = await save_message(pool, body.conversation_id, "assistant", full_response)
            yield f"data: {json.dumps({'done': True, 'message_id': str(saved['id'])})}\n\n"
        else:
            yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
