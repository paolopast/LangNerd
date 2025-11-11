from __future__ import annotations

from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.schemas import (
    GuidePayload,
    GuideResponse,
    QuestionPayload,
    QuestionResponse,
    SourceSchema,
)
from app.services.langgraph_pipeline import LangGraphOrchestrator


settings = get_settings()
app = FastAPI(
    title="Videogames LangGraph Guide",
    description=(
        "Backend che usa LangGraph + Gemini per rispondere a domande e produrre"
        " guide testuali sui videogiochi."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = LangGraphOrchestrator(settings)


@app.get("/health")
async def healthcheck():
    return {"status": "ok"}


@app.post("/api/qa", response_model=QuestionResponse)
async def answer_question(payload: QuestionPayload) -> QuestionResponse:
    try:
        result = orchestrator.run_qa(payload.model_dump())
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    sources = [
        SourceSchema(title=source["title"], url=source["url"], snippet=source.get("snippet"))
        for source in result.get("sources", [])[:6]
    ]

    return QuestionResponse(
        answer=result.get("answer", "Non è stato possibile generare una risposta."),
        sources=sources,
    )


@app.post("/api/guide", response_model=GuideResponse)
async def generate_guide(payload: GuidePayload) -> GuideResponse:
    try:
        result = orchestrator.run_guide(payload.model_dump())
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    sources = [
        SourceSchema(title=source["title"], url=source["url"], snippet=source.get("snippet"))
        for source in result.get("sources", [])[:6]
    ]

    return GuideResponse(
        guide=result.get("structured_guide") or {},
        sources=sources,
    )
