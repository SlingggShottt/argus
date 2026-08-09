import { useState } from 'react'
import { useQueryAgent } from '../hooks/useQueryAgent'

export function ChatPanel() {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const { mutate, isPending } = useQueryAgent()

  function handleSubmit(e) {
    e.preventDefault()
    const trimmed = question.trim()
    if (!trimmed || isPending) return

    setMessages((prev) => [...prev, { role: 'user', text: trimmed }])
    setQuestion('')

    mutate(trimmed, {
      onSuccess: (result) => {
        setMessages((prev) => [...prev, { role: 'assistant', text: result.answer }])
      },
      onError: (err) => {
        setMessages((prev) => [...prev, { role: 'assistant', text: `Error: ${err.message}` }])
      },
    })
  }

  return (
    <div className="rounded-lg border border-hairline bg-surface p-4 flex flex-col h-96">
      <h2 className="text-base font-semibold text-ink-primary mb-3">Ask Argus</h2>

      <div className="flex-1 overflow-y-auto flex flex-col gap-2 mb-3">
        {messages.length === 0 && (
          <p className="text-sm text-ink-muted">
            Try: "Which SKUs are at high risk of stockout?" or "What should I reorder for store 1, item 1?"
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`text-sm rounded-lg px-3 py-2 max-w-[85%] whitespace-pre-wrap ${
              m.role === 'user'
                ? 'self-end bg-series-1 text-white'
                : 'self-start bg-page text-ink-primary border border-hairline'
            }`}
          >
            {m.text}
          </div>
        ))}
        {isPending && <p className="text-sm text-ink-muted self-start">Thinking...</p>}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about forecasts, risks, or recommendations..."
          className="flex-1 text-sm border border-hairline rounded px-3 py-2 bg-surface text-ink-primary"
        />
        <button
          type="submit"
          disabled={isPending}
          className="text-sm font-medium rounded px-4 py-2 bg-series-1 text-white disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  )
}
