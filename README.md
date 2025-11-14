# Videogames LangGraph Guide

Stack completo (FastAPI + LangGraph + Gemini + React) che permette di:

- rispondere a domande puntuali sui videogiochi usando ricerche web in tempo reale;
- orchestrare la ragionamento con LangGraph e Gemini per mantenere contesto e citare fonti;
- generare report strutturati con descrizione, trama, missioni, relazioni e lista trofei (PlayStation) mostrati nel browser e scaricabili in HTML dettagliato.

## Prerequisiti

- Python 3.11+
- Node.js 20+
- Google AI Studio API key (Gemini) esportata come `GOOGLE_API_KEY`
- SerpAPI key per le ricerche (`SERPAPI_API_KEY`)

## Backend (FastAPI + LangGraph)

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate  # su PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Duplica .env.example in .env per configurare le variabili (vedi note sotto)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Su Windows usa `copy .env.example .env`; su macOS/Linux `cp .env.example .env`.

Endpoint principali:

- `POST /api/qa` -> risposte rapide + fonti (HTML pronto per il frontend).
- `POST /api/guide` -> ritorna JSON strutturato + percorso/URL dell'HTML esportato.
- `GET /health` -> verifica stato.

## Frontend (Vite + React + TypeScript)

```bash
cd frontend
# Duplica .env.example in .env per configurare le variabili (vedi note sotto)
npm install
npm run dev  # http://localhost:5173
```

Su Windows usa `copy .env.example .env`; su macOS/Linux `cp .env.example .env`.

Lo `npm run build` produce gli asset statici in `frontend/dist`.

## Flusso LangGraph

1. **Classify node**: identifica se la richiesta e Q&A o guida strutturata e definisce le query web.
2. **Search node**: chiama l'API professionale di SerpAPI (Google Search) per ottenere fonti fresche e localizzate.
3. **Answer / Guide nodes**: Gemini elabora il contesto per risposte puntuali o per compilare la struttura JSON (trama, personaggi, missioni, trofei, approfondimenti).
4. **Guide node**: restituisce la struttura finale.
5. **Export node**: costruisce un file HTML completo (missioni, trofei, trama estesa) salvato in `EXPORT_OUTPUT_DIR`.

## Testing rapido

- Backend: `pytest` non e configurato, ma puoi fare smoke test con `uvicorn` e `curl` sui due endpoint.
- Frontend: `npm run build` (gia eseguito) verifica il typing TypeScript + bundle Vite.

## Variabili ambiente principali

| Nome | Descrizione |
| --- | --- |
| `GOOGLE_API_KEY` | **Obbligatoria** per usare Gemini |
| `GEMINI_MODEL` | default `gemini-1.5-flash` |
| `SERPAPI_API_KEY` | **Obbligatoria** per le ricerche SerpAPI |
| `SEARCH_LANGUAGE` / `SEARCH_COUNTRY` | Parametri `hl`/`gl` di SerpAPI (es. `it`) |
| `SEARCH_MAX_RESULTS` | Numero massimo di snippet per query |
| `EXPORT_OUTPUT_DIR` | Cartella (relativa o assoluta) in cui salvare gli HTML generati |
| `VITE_API_BASE_URL` (frontend) | URL del backend, es. `http://localhost:8000` |

## Note

- Il backend effettua richieste web live, quindi serve connettivita internet.
- Ogni guida è visibile nel frontend e scaricabile via link `/generated/<nome>.html`.
- Ricorda di proteggere la tua API key Gemini nelle distribuzioni in produzione.
