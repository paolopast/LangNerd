import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'
import { apiClient } from './api'
import type { GuideResponse, QAResponse, Source } from './types'

type Tab = 'qa' | 'guide'

const defaultLanguage = 'it'

const languageOptions = [
  { value: 'it', label: 'Italiano' },
  { value: 'en', label: 'English' },
  { value: 'es', label: 'Espanol' },
]

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('qa')
  const [qaForm, setQaForm] = useState({
    question: '',
    game: '',
    focus: '',
    language: defaultLanguage,
  })
  const [guideForm, setGuideForm] = useState({
    game: '',
    focus: '',
    extra: '',
    language: defaultLanguage,
  })
  const [qaResult, setQaResult] = useState<QAResponse | null>(null)
  const [guideResult, setGuideResult] = useState<GuideResponse | null>(null)
  const [loading, setLoading] = useState({ qa: false, guide: false })
  const [error, setError] = useState<string | null>(null)

  const currentLanguage = useMemo(() => {
    return activeTab === 'qa' ? qaForm.language : guideForm.language
  }, [activeTab, qaForm.language, guideForm.language])

  const handleAsk = async (event: FormEvent) => {
    event.preventDefault()
    if (!qaForm.question.trim()) {
      setError('Inserisci una domanda')
      return
    }
    setLoading((prev) => ({ ...prev, qa: true }))
    setError(null)
    try {
      const response = await apiClient.askQuestion({
        question: qaForm.question,
        game: qaForm.game || undefined,
        focus: qaForm.focus || undefined,
        language: qaForm.language,
      })
      setQaResult(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore sconosciuto')
    } finally {
      setLoading((prev) => ({ ...prev, qa: false }))
    }
  }

  const handleGuide = async (event: FormEvent) => {
    event.preventDefault()
    if (!guideForm.game.trim()) {
      setError('Specifica il titolo del gioco')
      return
    }
    setLoading((prev) => ({ ...prev, guide: true }))
    setError(null)
    try {
      const response = await apiClient.generateGuide({
        game: guideForm.game,
        focus: guideForm.focus || undefined,
        extra: guideForm.extra || undefined,
        language: guideForm.language,
      })
      setGuideResult(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore sconosciuto')
    } finally {
      setLoading((prev) => ({ ...prev, guide: false }))
    }
  }

  const resetErrorOnInput = () => {
    if (error) setError(null)
  }

  const renderSources = (sources: Source[]) => (
    <div className="sources">
      <p>Fonti principali:</p>
      <ul>
        {sources.map((source) => (
          <li key={source.url}>
            <a href={source.url} target="_blank" rel="noreferrer">
              {source.title}
            </a>
            {source.snippet ? <span> - {source.snippet}</span> : null}
          </li>
        ))}
      </ul>
    </div>
  )

  const toHtml = (value?: string | null) => ({
    __html: value || '',
  })

  const renderEmptyState = (title: string, subtitle: string) => (
    <div className="empty-state">
      <h3>{title}</h3>
      <p>{subtitle}</p>
    </div>
  )

  return (
    <div className="app-shell">
      <div className="control-panel">
        <header className="hero">
          <img src="/langnerd.png" alt="Logo LangNerd" className="brand-logo" />
          <div className="hero-copy">
            <p className="eyebrow">LangGraph + Gemini</p>
            <h1>LangNerd</h1>
            <p className="subtitle">
              Strategie puntuali e guide complete direttamente dal web.
            </p>
            <div className="language-chip">Lingua attiva: {currentLanguage.toUpperCase()}</div>
          </div>
        </header>

        <div className="tabs">
          <button
            className={activeTab === 'qa' ? 'active' : ''}
            onClick={() => setActiveTab('qa')}
          >
            Domande veloci
          </button>
          <button
            className={activeTab === 'guide' ? 'active' : ''}
            onClick={() => setActiveTab('guide')}
          >
            Guida completa
          </button>
        </div>

        <section className="panel">
          {activeTab === 'qa' ? (
            <form onSubmit={handleAsk} className="form-grid">
              <label>
                Domanda
                <textarea
                  value={qaForm.question}
                  onChange={(e) => {
                    resetErrorOnInput()
                    setQaForm({ ...qaForm, question: e.target.value })
                  }}
                  placeholder="Esempio: Come sblocco la quest segreta in Final Fantasy XVI?"
                  rows={4}
                />
              </label>
              <label>
                Videogioco (facoltativo)
                <input
                  value={qaForm.game}
                  onChange={(e) => {
                    resetErrorOnInput()
                    setQaForm({ ...qaForm, game: e.target.value })
                  }}
                  placeholder="Final Fantasy XVI"
                />
              </label>
              <label>
                Focus / Obiettivo
                <input
                  value={qaForm.focus}
                  onChange={(e) => {
                    resetErrorOnInput()
                    setQaForm({ ...qaForm, focus: e.target.value })
                  }}
                  placeholder="strategia boss, farming, ecc."
                />
              </label>
              <label>
                Lingua
                <select
                  value={qaForm.language}
                  onChange={(e) => setQaForm({ ...qaForm, language: e.target.value })}
                >
                  {languageOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <button type="submit" className="primary" disabled={loading.qa}>
                {loading.qa ? 'Sto cercando...' : 'Rispondi'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleGuide} className="form-grid">
              <label>
                Titolo del gioco
                <input
                  value={guideForm.game}
                  onChange={(e) => {
                    resetErrorOnInput()
                    setGuideForm({ ...guideForm, game: e.target.value })
                  }}
                  placeholder="Marvel's Spider-Man 2"
                />
              </label>
              <label>
                Focus dettagliato
                <input
                  value={guideForm.focus}
                  onChange={(e) => setGuideForm({ ...guideForm, focus: e.target.value })}
                  placeholder="trofei, relazioni tra personaggi, ecc."
                />
              </label>
              <label>
                Note aggiuntive
                <textarea
                  value={guideForm.extra}
                  onChange={(e) => setGuideForm({ ...guideForm, extra: e.target.value })}
                  placeholder="Inserisci richieste speciali su missioni, build, ecc."
                  rows={3}
                />
              </label>
              <label>
                Lingua
                <select
                  value={guideForm.language}
                  onChange={(e) => setGuideForm({ ...guideForm, language: e.target.value })}
                >
                  {languageOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <button type="submit" className="primary" disabled={loading.guide}>
                {loading.guide ? 'Creo la guida...' : 'Genera guida + HTML'}
              </button>
            </form>
          )}
        </section>

        {error && <div className="alert error">{error}</div>}
      </div>

      <div className="output-panel">
        {activeTab === 'qa' ? (
          qaResult ? (
            <section className="result qa-result">
              <h2>Risposta</h2>
              <div className="answer-block rich-text" dangerouslySetInnerHTML={toHtml(qaResult.answer)} />
              {qaResult.sources?.length ? renderSources(qaResult.sources) : null}
            </section>
          ) : (
            renderEmptyState(
              'In attesa di una domanda',
              'Compila il pannello a sinistra e ottieni subito strategie, oggetti e missioni.'
            )
          )
        ) : guideResult ? (
          <section className="result guide-result">
            <div className="result-header">
              <div>
                <p className="eyebrow">Guida completa</p>
                <h2>{guideResult.guide.game_title || guideForm.game}</h2>
                <p className="subtitle small">Contenuto generato in tempo reale dal motore LangNerd.</p>
              </div>
              <a
                href={`${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'}${guideResult.document_url}`}
                target="_blank"
                rel="noreferrer"
                className="primary ghost"
              >
                Scarica guida HTML
              </a>
            </div>
            <div className="guide-grid">
              {guideResult.guide.elevator_pitch && (
                <div>
                  <h3>Descrizione</h3>
                  <div className="rich-text" dangerouslySetInnerHTML={toHtml(guideResult.guide.elevator_pitch)} />
                </div>
              )}
              {guideResult.guide.story_overview && (
                <div>
                  <h3>Trama</h3>
                  <div className="rich-text" dangerouslySetInnerHTML={toHtml(guideResult.guide.story_overview)} />
                </div>
              )}
              {guideResult.guide.world_setting && (
                <div>
                  <h3>Ambientazione</h3>
                  <div className="rich-text" dangerouslySetInnerHTML={toHtml(guideResult.guide.world_setting)} />
                </div>
              )}
              {Array.isArray(guideResult.guide.missions_and_tips) && (
                <div>
                  <h3>Missioni e strategie</h3>
                  <ul>
                    {guideResult.guide.missions_and_tips.map((mission: any) => (
                      <li key={mission.title}>
                        <strong>{mission.title}</strong>
                        <div className="rich-text" dangerouslySetInnerHTML={toHtml(mission.details)} />
                        <div className="rich-text muted" dangerouslySetInnerHTML={toHtml(mission.strategy)} />
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {Array.isArray(guideResult.guide.trophies) && (
                <div>
                  <h3>Trofei PlayStation</h3>
                  <ul>
                    {guideResult.guide.trophies.map((trophy: any) => (
                      <li key={trophy.name}>
                        <strong>
                          {trophy.name} <span>({trophy.tier})</span>
                        </strong>
                        <div className="rich-text" dangerouslySetInnerHTML={toHtml(trophy.description)} />
                        <div className="rich-text muted" dangerouslySetInnerHTML={toHtml(trophy.tips)} />
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {guideResult.guide.relationships && (
                <div>
                  <h3>Relazioni & Fazioni</h3>
                  <div className="rich-text" dangerouslySetInnerHTML={toHtml(guideResult.guide.relationships)} />
                </div>
              )}
              {guideResult.guide.advanced_insights && (
                <div>
                  <h3>Approfondimenti avanzati</h3>
                  <div className="rich-text" dangerouslySetInnerHTML={toHtml(guideResult.guide.advanced_insights)} />
                </div>
              )}
            </div>
            {guideResult.sources?.length ? renderSources(guideResult.sources) : null}
          </section>
        ) : (
          renderEmptyState(
            'Nessuna guida ancora',
            'Richiedi un gioco a sinistra per ottenere descrizione, trama e lista trofei dettagliata + esportazione HTML.'
          )
        )}
      </div>
    </div>
  )
}

export default App
