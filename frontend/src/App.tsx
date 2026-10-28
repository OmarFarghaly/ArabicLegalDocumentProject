import { useEffect, useRef, useState } from 'react'
import {
  ArrowUp,
  BookOpen,
  CircleHelp,
  Plus,
  Scale,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'
import './App.css'

type Message = {
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
}

type AnswerResponse = {
  answer: string
  sources: string[]
}

function isAnswerResponse(value: unknown): value is AnswerResponse {
  if (typeof value !== 'object' || value === null || !('answer' in value)) {
    return false
  }

  return (
    typeof value.answer === 'string' &&
    (!('sources' in value) ||
      (Array.isArray(value.sources) &&
        value.sources.every((source) => typeof source === 'string')))
  )
}

const suggestions = [
  'What are the essential elements of a contract?',
  'When can a contract be rescinded?',
  'ما هي آثار العقد بالنسبة للمتعاقدين؟',
]

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [pendingQuestion, setPendingQuestion] = useState('')
  const [error, setError] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  function startNewChat() {
    if (loading) return
    setMessages([])
    setQuestion('')
    setError('')
  }

  async function submitQuestion(text = question) {
    const currentQuestion = text.trim()
    if (!currentQuestion || loading) return

    setLoading(true)
    setPendingQuestion(currentQuestion)
    setQuestion('')
    setError('')

    try {
      const baseUrl = (
        import.meta.env.VITE_API_BASE_URL || 'http://localhost:4000'
      ).replace(/\/$/, '')

      const response = await fetch(`${baseUrl}/api/v1/rag/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: currentQuestion,
          chat_history: messages.slice(-10).map(({ role, content }) => ({
            role,
            content,
          })),
        }),
      })

      const body: unknown = await response.json()

      if (!response.ok) {
        const detail =
          typeof body === 'object' &&
          body !== null &&
          'detail' in body &&
          typeof body.detail === 'string'
            ? body.detail
            : `The request failed (${response.status}).`
        throw new Error(detail)
      }

      if (!isAnswerResponse(body)) {
        throw new Error('The server returned an unexpected response.')
      }

      setMessages((current) => [
        ...current,
        { role: 'user', content: currentQuestion },
        {
          role: 'assistant',
          content: body.answer,
          sources: body.sources ?? [],
        },
      ])
      setPendingQuestion('')
    } catch (requestError) {
      setQuestion(currentQuestion)
      setPendingQuestion('')
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Could not reach the server. Please try again.',
      )
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void submitQuestion()
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" aria-label="Civic home">
          <span className="brand-mark">
            <Scale size={21} strokeWidth={1.8} />
          </span>
          <span className="brand-name">Civic</span>
        </a>

        <button
          className="new-chat-button"
          type="button"
          onClick={startNewChat}
          disabled={loading}
        >
          <Plus size={18} />
          <span>New conversation</span>
        </button>

        <div className="sidebar-label">YOUR LEGAL ASSISTANT</div>
        <div className="sidebar-info">
          <span className="sidebar-info-icon">
            <BookOpen size={17} />
          </span>
          <span>
            <strong>Egyptian Civil Code</strong>
            <small>Legal answers with citations</small>
          </span>
        </div>

        <div className="sidebar-spacer" />

        <div className="privacy-note">
          <ShieldCheck size={17} />
          <span>Your questions stay in this session.</span>
        </div>
        <div className="sidebar-footer">A legal research companion</div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div className="mobile-brand">
            <span className="brand-mark">
              <Scale size={19} />
            </span>
            <span>Civic</span>
          </div>
          <div className="topbar-context">
            <span className="status-dot" />
            Egyptian Civil Code
          </div>
          <button
            className="topbar-help"
            type="button"
            title="Answers are based on retrieved Civil Code articles"
            aria-label="About this assistant"
          >
            <CircleHelp size={19} />
          </button>
        </header>

        <section className="chat-area">
          {messages.length === 0 && !pendingQuestion ? (
            <div className="welcome">
              <div className="welcome-icon">
                <Sparkles size={21} />
              </div>
              <p className="eyebrow">YOUR LEGAL RESEARCH COMPANION</p>
              <h1>
                Clarity on the law,
                <br />
                <span>grounded in the articles.</span>
              </h1>
              <p className="welcome-description">
                Ask a question about the Egyptian Civil Code. Get a clear
                answer supported by relevant legal articles.
              </p>

              <div className="suggestion-heading">TRY ASKING</div>
              <div className="suggestion-list">
                {suggestions.map((suggestion) => (
                  <button
                    className="suggestion-card"
                    key={suggestion}
                    type="button"
                    onClick={() => setQuestion(suggestion)}
                  >
                    <span>{suggestion}</span>
                    <ArrowUp className="suggestion-arrow" size={16} />
                  </button>
                ))}
              </div>
              <div className="welcome-footnote">
                <ShieldCheck size={15} />
                Answers are generated from retrieved legal text
              </div>
            </div>
          ) : (
            <div className="conversation">
              {messages.map((message, index) => (
                <article
                  className={`message-row message-${message.role}`}
                  key={`${message.role}-${index}`}
                >
                  {message.role === 'assistant' && (
                    <div className="assistant-avatar">
                      <Scale size={17} />
                    </div>
                  )}
                  <div className="message-content">
                    {message.role === 'assistant' && (
                      <div className="message-author">Civic</div>
                    )}
                    <div className="message-text" dir="auto">
                      {message.content}
                    </div>
                    {message.sources && message.sources.length > 0 && (
                      <details className="sources-panel">
                        <summary>
                          <BookOpen size={15} />
                          Legal sources
                          <span>{message.sources.length}</span>
                        </summary>
                        <ul>
                          {message.sources.map((source, sourceIndex) => (
                            <li key={sourceIndex} dir="auto">
                              {source}
                            </li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </div>
                </article>
              ))}

              {pendingQuestion && (
                <article className="message-row message-user">
                  <div className="message-content">
                    <div className="message-text" dir="auto">
                      {pendingQuestion}
                    </div>
                  </div>
                </article>
              )}

              {loading && (
                <div className="loading-row">
                  <div className="assistant-avatar">
                    <Scale size={17} />
                  </div>
                  <div>
                    <div className="message-author">Civic is researching</div>
                    <div className="loading-indicator">
                      <span />
                      <span />
                      <span />
                    </div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </section>

        <footer className="composer-area">
          {error && (
            <div className="error-message" role="alert">
              {error}
            </div>
          )}
          <form className="composer" onSubmit={handleSubmit}>
            <textarea
              aria-label="Ask a legal question"
              dir="auto"
              placeholder="Ask a question about the Civil Code..."
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  void submitQuestion()
                }
              }}
              rows={1}
              disabled={loading}
            />
            <button
              className="send-button"
              type="submit"
              aria-label="Send question"
              disabled={loading || !question.trim()}
            >
              <ArrowUp size={19} />
            </button>
          </form>
          <div className="composer-caption">
            <span>Enter to send</span>
            <span className="caption-divider">·</span>
            <span>Shift + Enter for a new line</span>
            <span className="caption-note">
              AI can make mistakes. Verify important legal information.
            </span>
          </div>
        </footer>
      </main>
    </div>
  )
}

export default App