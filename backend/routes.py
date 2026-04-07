import asyncio
import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from database import save_message, get_messages
from llm import stream_chat_response
from memory import search_memories, store_memories

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

    # Search memories for personalized context
    memories_context = search_memories(body.message, body.conversation_id)

    async def event_stream():
        full_response = ""
        try:
            async for token in stream_chat_response(history, memories_context):
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        # Save the complete assistant message
        if full_response:
            saved = await save_message(pool, body.conversation_id, "assistant", full_response)
            yield f"data: {json.dumps({'done': True, 'message_id': str(saved['id'])})}\n\n"

            # Store memories in background (don't block the response)
            loop = asyncio.get_event_loop()
            loop.run_in_executor(
                None,
                store_memories,
                [
                    {"role": "user", "content": body.message},
                    {"role": "assistant", "content": full_response},
                ],
                body.conversation_id,
            )
        else:
            yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
