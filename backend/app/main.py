from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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
    title="LangNerd Videogames Guide",
    description="Backend LangGraph + Gemini per Q&A e guide con export HTML automatico.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

export_dir = Path(settings.export_output_dir)
export_dir.mkdir(parents=True, exist_ok=True)
app.mount("/generated", StaticFiles(directory=export_dir), name="generated")

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

    sources = _build_sources(result)
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

    export_path = result.get("export_path")
    if not export_path:
        raise HTTPException(status_code=500, detail="Generazione HTML fallita.")

    rel_name = Path(export_path).name
    sources = _build_sources(result)

    return GuideResponse(
        document_path=export_path,
        document_url=f"/generated/{rel_name}",
        guide=result.get("structured_guide") or {},
        sources=sources,
    )


def _build_sources(result: dict) -> List[SourceSchema]:
    return [
        SourceSchema(title=source["title"], url=source["url"], snippet=source.get("snippet"))
        for source in result.get("sources", [])[:6]
    ]
