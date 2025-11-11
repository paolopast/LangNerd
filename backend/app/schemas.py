from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class SourceSchema(BaseModel):
    title: str = Field(..., description="Result title or site name")
    url: str = Field(..., description="Source URL")
    snippet: Optional[str] = Field(default=None, description="Short preview text, when available")


class QuestionPayload(BaseModel):
    question: str = Field(..., description="Domanda puntuale sul videogioco")
    game: Optional[str] = Field(default=None, description="Nome del videogioco se specificato")
    focus: Optional[str] = Field(default=None, description="Informazione extra da privilegiare")
    language: Optional[str] = Field(default=None, description="Lingua della risposta (default italiano)")


class QuestionResponse(BaseModel):
    answer: str
    sources: List[SourceSchema]
    mode: Literal["qa"] = "qa"


class GuidePayload(BaseModel):
    game: str = Field(..., description="Nome ufficiale del videogioco")
    focus: Optional[str] = Field(default=None, description="Aspetti da analizzare con maggior profondità")
    extra: Optional[str] = Field(default=None, description="Note aggiuntive fornite dall'utente")
    language: Optional[str] = Field(default=None, description="Lingua del documento (default italiano)")


class GuideResponse(BaseModel):
    guide: Dict[str, Any] = Field(..., description="Struttura dati generata dal LLM che il frontend visualizza")
    sources: List[SourceSchema]
    mode: Literal["guide"] = "guide"
