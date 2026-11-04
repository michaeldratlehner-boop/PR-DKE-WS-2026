from fastapi import APIRouter
from starlette.responses import StreamingResponse

from app.llm import generiere_antwort_async_stream
from app.schemas import ChatAnfrage

router = APIRouter(tags=["Chat"])

@router.post("/chat")
async def chat_endpoint(anfrage: ChatAnfrage):
    # Der Generator wird direkt an die FAST API übergeben
    generator = generiere_antwort_async_stream(prompt=anfrage.nachricht)
    return StreamingResponse(generator, media_type="text/event-stream")