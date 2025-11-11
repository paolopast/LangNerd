import type { GuideResponse, QAResponse } from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}))
    const message = errorBody.detail || errorBody.message || res.statusText
    throw new Error(message)
  }
  return res.json() as Promise<T>
}

export const apiClient = {
  askQuestion: async (payload: {
    question: string
    game?: string
    focus?: string
    language?: string
  }): Promise<QAResponse> => {
    const res = await fetch(`${API_BASE_URL}/api/qa`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return handleResponse<QAResponse>(res)
  },

  generateGuide: async (payload: {
    game: string
    focus?: string
    extra?: string
    language?: string
  }): Promise<GuideResponse> => {
    const res = await fetch(`${API_BASE_URL}/api/guide`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return handleResponse<GuideResponse>(res)
  },
}
