from __future__ import annotations

import html
import json
import re
from typing import Any, Dict, List, Literal, Optional, TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph

from app.config import Settings, get_settings
from app.services.html_writer import GuideHTMLBuilder
from app.services.search import search_web


class GuideState(TypedDict, total=False):
    query: str
    game: Optional[str]
    focus: Optional[str]
    extra: Optional[str]
    language: str
    mode: Literal["qa", "guide"]
    search_queries: List[str]
    search_results: List[Dict[str, str]]
    structured_guide: Dict[str, Any]
    answer: str
    export_path: str
    sources: List[Dict[str, str]]


class LangGraphOrchestrator:
    """Encapsulates the LangGraph workflow for QA and guide generation."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.llm = ChatGoogleGenerativeAI(
            model=self.settings.gemini_model,
            temperature=0.2,
            convert_system_message_to_human=True,
            google_api_key=self.settings.google_api_key,
        )
        self.html_builder = GuideHTMLBuilder(self.settings.export_output_dir)
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(GuideState)
        workflow.add_node("classify", self._classify_request)
        workflow.add_node("search", self._run_search)
        workflow.add_node("answer", self._generate_answer)
        workflow.add_node("guide", self._generate_guide_structure)
        workflow.add_node("export", self._generate_export)

        workflow.add_edge(START, "classify")
        workflow.add_edge("classify", "search")
        workflow.add_conditional_edges("search", self._route_after_search)
        workflow.add_edge("guide", "export")
        workflow.add_edge("answer", END)
        workflow.add_edge("export", END)

        return workflow.compile()

    # ---------- graph nodes ----------
    def _classify_request(self, state: GuideState) -> GuideState:
        if state.get("mode"):
            return state

        prompt = (
            "Agisci come orchestratore senior di LangNerd, piattaforma per guide sui videogiochi. "
            "Analizza la richiesta seguente e scegli se attivare la modalità 'qa' (risposta puntuale) "
            "oppure 'guide' (documento strutturato con trama, missioni, trofei). "
            "Restituisci SOLO JSON valido con le chiavi precise: "
            '{"mode": "qa"|"guide", "language": "<codice ISO-639-1>", '
            '"game": "<titolo o null>", "search_queries": ["query 1", "..."]}. '
            "Regole: 1) Se l'utente chiede tutorial completi, panoramiche o PDF -> mode='guide'; "
            "2) imposta language nella lingua in cui l'utente scrive (fallback 'it'); "
            "3) genera almeno 3 query complementari (titolo + trama, missioni, trofei/focus) senza duplicati; "
            "4) non aggiungere testo fuori dal JSON."
            f"\nDomanda utente: {state.get('query')}"
            f"\nGioco indicato: {state.get('game') or 'non specificato'}"
            f"\nFocus richiesto: {state.get('focus') or 'nessuno'}"
        )

        result = self._invoke_json_llm(prompt)
        merged = state.copy()
        if isinstance(result, dict):
            merged["mode"] = result.get("mode", "qa")  # type: ignore
            merged["language"] = result.get("language") or self.settings.default_language
            merged["game"] = result.get("game") or state.get("game")
            merged["search_queries"] = result.get("search_queries") or [state.get("query", "")]
        else:
            merged["mode"] = "qa"
            merged["language"] = state.get("language") or self.settings.default_language
            merged["search_queries"] = [state.get("query", "")]
        return merged

    def _run_search(self, state: GuideState) -> GuideState:
        queries = state.get("search_queries") or [state.get("query", "")]
        aggregated: List[Dict[str, str]] = []
        seen = set()
        language = state.get("language") or self.settings.search_language
        for query in queries:
            if not query:
                continue
            results = search_web(
                query,
                api_key=self.settings.serpapi_api_key,
                max_results=self.settings.search_max_results,
                country=self.settings.search_country,
                language=language,
            )
            for res in results:
                if res["url"] in seen:
                    continue
                seen.add(res["url"])
                aggregated.append(res)

        return {**state, "search_results": aggregated, "sources": aggregated[:6]}

    def _generate_answer(self, state: GuideState) -> GuideState:
        results = state.get("search_results") or []
        language = state.get("language") or self.settings.default_language
        context_blocks = []
        for idx, item in enumerate(results, start=1):
            context_blocks.append(
                f"[{idx}] {item['title']} - {item['url']}\nEstratto: {item.get('snippet','')}"
            )
        context_text = "\n\n".join(context_blocks) if context_blocks else "Nessuna fonte verificata."

        sources = state.get("sources") or state.get("search_results") or []
        prompt = (
            "Tu sei LangNerd Response Engine, specialista di videogiochi. "
            f"Rispondi in {language} seguendo queste regole rigorose:\n"
            "1) Usa SOLO i dati verificabili nel contesto fornito; se mancano info dichiaralo.\n"
            "2) Inizia con un breve executive summary (2 frasi max) focalizzato sul quesito.\n"
            "3) Fornisci istruzioni operative con passaggi numerati e consigli pratici strettamente inerenti.\n"
            "4) Evidenzia eventuali requisiti (livello, oggetti, build consigliate) in una lista puntata.\n"
            "5) Chiudi ogni paragrafo citando almeno una fonte nel formato [n] coerente con gli ID sottostanti.\n"
            "6) Restituisci l'intera risposta come HTML semantico valido (usa <section>, <ol>, <ul>, <li>, <strong>, ecc.).\n"
            "7) Non inventare URL o informazioni; ignora contenuti fuori tema.\n"
            f"\nContesto verificato:\n{context_text}\n"
            f"\nDomanda finale (mantieni la risposta strettamente inerente): {state.get('query') or ''}"
        )

        response = self.llm.invoke(prompt)
        answer_html = self._ensure_html(self._coerce_content(response))
        linked = self._linkify_citations(answer_html, sources)
        return {**state, "answer": linked}

    def _generate_guide_structure(self, state: GuideState) -> GuideState:
        results = state.get("search_results") or []
        language = state.get("language") or self.settings.default_language
        serialized = json.dumps(results, ensure_ascii=False)

        prompt = (
            "Agisci come redattore capo di LangNerd e costruisci una guida completa basata sui risultati "
            "di ricerca JSON forniti. Rispetta rigorosamente queste linee guida:\n"
            "- Usa SOLO informazioni corroborate dalle fonti; se mancano dati, scrivi 'Dato non disponibile'.\n"
            "- Mantieni il tono professionale ma accessibile, sempre in lingua "
            f"{language}.\n"
            "- Story_overview deve essere un riassunto narrativo estremamente dettagliato (minimo 200 parole) "
            "che copra contesto, eventi principali, colpi di scena e conseguenze.\n"
            "- Missions_and_tips deve contenere almeno 6 voci con titoli descrittivi: ogni voce include dettagli "
            "della missione e una strategia operativa passo-passo con suggerimenti di build/oggetti.\n"
            "- Trophies deve contenere almeno 10 trofei PlayStation con tier corretto, descrizione dell'obiettivo "
            "e consigli concreti su come ottenerli rapidamente (citare farming spot, requisiti, condizioni missabili).\n"
            "- Main_characters deve includere protagonisti e antagonisti principali con ruolo nella storia e "
            "sinergie o conflitti rilevanti.\n"
            "- Relationships e advanced_insights devono evidenziare fazioni, alleanze, controstrategie, build meta.\n"
            "- Restituisci esclusivamente JSON valido con la seguente struttura esatta:\n"
            "{\n"
            '  "game_title": str,\n'
            '  "elevator_pitch": str,\n'
            '  "story_overview": str,\n'
            '  "world_setting": str,\n'
            '  "main_characters": [{"name": str, "description": str, "role": str}],\n'
            '  "relationships": str,\n'
            '  "missions_and_tips": [{"title": str, "details": str, "strategy": str}],\n'
            '  "trophies": [{"name": str, "tier": str, "description": str, "tips": str}],\n'
            '  "advanced_insights": str\n'
            "}\n"
            f"Fonti JSON:\n{serialized}\n"
            f"Gioco di riferimento: {state.get('game') or 'non specificato'}"
        )

        structured = self._invoke_json_llm(prompt)
        sources = state.get("sources") or results
        if isinstance(structured, dict):
            structured = self._normalize_guide_html(
                structured,
                fallback_title=state.get("game"),
                sources=sources,
            )
        else:
            structured = self._normalize_guide_html(
                {
                    "game_title": state.get("game") or "Guida videoludica",
                    "elevator_pitch": "Impossibile estrarre informazioni dettagliate.",
                    "story_overview": "Dato non disponibile.",
                    "world_setting": "Dato non disponibile.",
                    "main_characters": [],
                    "relationships": "Dato non disponibile.",
                    "missions_and_tips": [],
                    "trophies": [],
                    "advanced_insights": "Dato non disponibile.",
                },
                fallback_title=state.get("game"),
                sources=sources,
            )
        return {**state, "structured_guide": structured}


    # ---------- routing ----------
    def _route_after_search(self, state: GuideState) -> str:
        return "guide" if state.get("mode") == "guide" else "answer"

    def _generate_export(self, state: GuideState) -> GuideState:
        guide = state.get("structured_guide") or {}
        language = state.get("language") or self.settings.default_language
        export_path = self.html_builder.build_html(guide, language=language)
        return {**state, "export_path": export_path}

    # ---------- helpers ----------
    def _invoke_json_llm(self, prompt: str) -> Any:
        response = self.llm.invoke(
            [
                {"role": "system", "content": "Rispondi solo con JSON valido."},
                {"role": "user", "content": prompt},
            ]
        )
        raw_content = self._coerce_content(response)
        candidate = self._extract_json_payload(raw_content)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return None

    def _coerce_content(self, response: Any) -> str:
        content = response.content if hasattr(response, "content") else str(response)
        if isinstance(content, list):
            text_fragments: List[str] = []
            for part in content:
                if isinstance(part, dict) and part.get("text"):
                    text_fragments.append(part["text"])
                else:
                    text_fragments.append(str(part))
            content = "".join(text_fragments)
        return str(content)

    def _ensure_html(self, text: str) -> str:
        stripped = (text or "").strip()
        if not stripped:
            return "<p></p>"
        if re.search(r"<[a-zA-Z][\s\S]*?>", stripped):
            return stripped
        paragraphs = [
            f"<p>{html.escape(line.strip())}</p>"
            for line in stripped.split("\n")
            if line.strip()
        ]
        return "".join(paragraphs) or f"<p>{html.escape(stripped)}</p>"

    def _normalize_guide_html(
        self,
        guide: Dict[str, Any],
        *,
        fallback_title: Optional[str],
        sources: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        normalized = guide.copy()
        text_fields = [
            "elevator_pitch",
            "story_overview",
            "world_setting",
            "relationships",
            "advanced_insights",
        ]
        for field in text_fields:
            value = normalized.get(field) or "Dato non disponibile."
            normalized[field] = self._linkify_citations(
                self._ensure_html(str(value)),
                sources,
            )

        def sanitize_list(items, factory):
            safe_items: List[Dict[str, Any]] = []
            if not isinstance(items, list):
                return safe_items
            for raw in items:
                if isinstance(raw, dict):
                    safe_items.append(factory(raw))
            return safe_items

        normalized["main_characters"] = sanitize_list(
            normalized.get("main_characters"),
            lambda char: {
                "name": char.get("name") or "Personaggio sconosciuto",
                "description": self._linkify_citations(
                    self._ensure_html(char.get("description") or "Dato non disponibile."),
                    sources,
                ),
                "role": self._linkify_citations(
                    self._ensure_html(char.get("role") or "Dato non disponibile."),
                    sources,
                ),
            },
        )

        normalized["missions_and_tips"] = sanitize_list(
            normalized.get("missions_and_tips"),
            lambda mission: {
                "title": mission.get("title") or "Missione senza titolo",
                "details": self._linkify_citations(
                    self._ensure_html(mission.get("details") or "Dato non disponibile."),
                    sources,
                ),
                "strategy": self._linkify_citations(
                    self._ensure_html(mission.get("strategy") or "Dato non disponibile."),
                    sources,
                ),
            },
        )

        normalized["trophies"] = sanitize_list(
            normalized.get("trophies"),
            lambda trophy: {
                "name": trophy.get("name") or "Trofeo sconosciuto",
                "tier": trophy.get("tier") or trophy.get("rarity") or "?",
                "description": self._linkify_citations(
                    self._ensure_html(trophy.get("description") or "Dato non disponibile."),
                    sources,
                ),
                "tips": self._linkify_citations(
                    self._ensure_html(trophy.get("tips") or trophy.get("strategy") or "Dato non disponibile."),
                    sources,
                ),
            },
        )

        normalized["game_title"] = normalized.get("game_title") or fallback_title or "Guida videoludica"
        return normalized

    def _linkify_citations(self, html_text: str, sources: List[Dict[str, str]]) -> str:
        if not html_text:
            return html_text

        expanded = self._expand_reference_groups(html_text)
        pattern = re.compile(r"\[(\d+)\]")

        def repl(match: re.Match[str]) -> str:
            try:
                idx = int(match.group(1))
            except ValueError:
                return match.group(0)
            if 1 <= idx <= len(sources):
                url = html.escape(sources[idx - 1].get("url", ""))
                if url:
                    return (
                        f'<sup><a href="{url}" target="_blank" rel="noreferrer">[{idx}]</a></sup>'
                    )
            return match.group(0)

        return pattern.sub(repl, expanded)

    def _expand_reference_groups(self, text: str) -> str:
        pattern = re.compile(r"\[(\s*\d+(?:\s*[, ]\s*\d+)+\s*)\]")

        def repl(match: re.Match[str]) -> str:
            content = match.group(1)
            numbers = [num for num in re.split(r"[, ]+", content.strip()) if num]
            if not numbers:
                return match.group(0)
            return "".join(f"[{num}]" for num in numbers)

        return pattern.sub(repl, text)

    def _extract_json_payload(self, text: str) -> str:
        """Strip markdown fences and isolate the JSON object for robust parsing."""

        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return match.group(0)
        return cleaned

    # ---------- public API ----------
    def run_qa(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        initial_state: GuideState = {
            "query": payload.get("question") or payload.get("query") or "",
            "game": payload.get("game"),
            "focus": payload.get("focus"),
            "language": payload.get("language") or self.settings.default_language,
            "mode": "qa",
            "search_queries": self._build_queries(payload),
        }
        return self.graph.invoke(initial_state)

    def run_guide(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        base_query = f"videogioco {payload.get('game','')}"
        extra_focus = payload.get("focus") or ""
        composed_query = f"{base_query} {extra_focus}".strip()
        initial_state: GuideState = {
            "query": composed_query,
            "game": payload.get("game"),
            "focus": payload.get("focus"),
            "extra": payload.get("extra"),
            "language": payload.get("language") or self.settings.default_language,
            "mode": "guide",
            "search_queries": self._build_queries(payload, include_trophies=True),
        }
        return self.graph.invoke(initial_state)

    def _build_queries(self, payload: Dict[str, Any], include_trophies: bool = False) -> List[str]:
        game = payload.get("game") or ""
        focus = payload.get("focus") or ""
        question = payload.get("question") or payload.get("query") or ""
        queries = [question]
        if game:
            queries.append(f"{game} trama completa")
            queries.append(f"{game} missioni guida")
        if include_trophies and game:
            queries.append(f"{game} lista trofei PlayStation")
        if focus:
            queries.append(f"{game} {focus}")
        return [q for q in queries if q]
