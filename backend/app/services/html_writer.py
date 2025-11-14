from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def _clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return html.escape(value.strip())


def _render_section(title: str, body: str) -> str:
    if not body:
        return ""
    return f"""
    <section class="block">
        <h2>{title}</h2>
        {body}
    </section>
    """


class GuideHTMLBuilder:
    """Generate standalone HTML guides that mirror the structured data."""

    def __init__(self, output_dir: str) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build_html(self, guide: Dict[str, Any], language: str = "it") -> str:
        title = _clean_text(guide.get("game_title") or "Guida videoludica")
        generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        html_content = f"""
        <!DOCTYPE html>
        <html lang="{language}">
        <head>
            <meta charset="utf-8" />
            <title>{title} - LangNerd</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    background-color: #05070f;
                    color: #f5f6fb;
                    margin: 0;
                    padding: 2rem;
                }}
                h1 {{ color: #63d2ff; }}
                h2 {{ color: #ff914d; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: .3rem; }}
                .meta {{ color: #9fb3ff; font-size: 0.9rem; margin-bottom: 2rem; }}
                .block {{ margin-bottom: 1.5rem; }}
                ul {{ padding-left: 1.3rem; }}
                li {{ margin-bottom: .5rem; }}
                .muted {{ color: #a3b2d4; }}
                .card {{ border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 1rem; margin-bottom: 1rem; }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            <div class="meta">Generato con LangNerd • {generated_at} • Lingua: {language.upper()}</div>
            {self._render_text_block("Descrizione sintetica", guide.get("elevator_pitch"))}
            {self._render_text_block("Trama completa", guide.get("story_overview"))}
            {self._render_text_block("Ambientazione", guide.get("world_setting"))}
            {self._render_text_block("Relazioni e fazioni", guide.get("relationships"))}
            {self._render_list_block("Personaggi principali", guide.get("main_characters"), ["name", "role", "description"])}
            {self._render_list_block("Missioni e strategie", guide.get("missions_and_tips"), ["title", "details", "strategy"])}
            {self._render_list_block("Trofei PlayStation", guide.get("trophies"), ["name", "tier", "description", "tips"])}
            {self._render_text_block("Approfondimenti avanzati", guide.get("advanced_insights"))}
        </body>
        </html>
        """

        filename = f"{title.lower().replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.html"
        output_path = self.output_dir / filename
        output_path.write_text(html_content, encoding="utf-8")
        return str(output_path)

    def _render_text_block(self, title: str, content: Optional[str]) -> str:
        cleaned = content.strip() if isinstance(content, str) else ""
        if not cleaned:
            return ""
        return _render_section(title, cleaned)

    def _render_list_block(
        self,
        title: str,
        items: Optional[Iterable[Dict[str, Any]]],
        fields: List[str],
    ) -> str:
        if not items:
            return ""
        rows = []
        for item in items:
            card_lines = []
            for field in fields:
                value = item.get(field)
                if not value:
                    continue
                label = field.replace("_", " ").title()
                card_lines.append(f"<p><strong>{label}:</strong> {value}</p>")
            if card_lines:
                rows.append(f'<div class="card">{"".join(card_lines)}</div>')
        if not rows:
            return ""
        return _render_section(title, "".join(rows))
