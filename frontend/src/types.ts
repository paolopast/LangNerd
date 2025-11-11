export type Source = {
  title: string
  url: string
  snippet?: string
}

export type QAResponse = {
  answer: string
  sources: Source[]
  mode: 'qa'
}

export type GuideResponse = {
  guide: Record<string, any>
  sources: Source[]
  mode: 'guide'
}

export type ApiError = {
  detail?: string
  message?: string
}
