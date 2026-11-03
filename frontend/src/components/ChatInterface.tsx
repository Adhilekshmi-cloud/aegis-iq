import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, AlertTriangle, ChevronDown, ChevronUp, FileText, Shield } from 'lucide-react'
import { api } from '../services/api'
import type { ChatMessage, QueryResponse } from '../types'

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100)
  const color = pct >= 80 ? 'text-aegis-success border-aegis-success/30 bg-aegis-success/10'
    : pct >= 50 ? 'text-aegis-warning border-aegis-warning/30 bg-aegis-warning/10'
    : 'text-aegis-danger border-aegis-danger/30 bg-aegis-danger/10'
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-bold ${color}`}>
      {pct}%
    </span>
  )
}

function EvidencePanel({ response }: { response: QueryResponse }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="mt-3 space-y-2">
      <button onClick={() => setExpanded(!expanded)} className="flex items-center gap-1 text-xs text-aegis-accent-light hover:text-white transition-colors">
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        {response.claims.length} claim(s) · {response.evidence.length} source(s) · <ConfidenceBadge confidence={response.confidence} />
      </button>

      {expanded && (
        <div className="space-y-2 pl-2 border-l-2 border-aegis-accent/20">
          {/* Claims */}
          {response.claims.map((claim, i) => (
            <div key={i} className="bg-aegis-bg/50 rounded-lg p-3 text-xs space-y-1">
              <p className="text-aegis-text">
                <span className="font-semibold text-white">{claim.entity_name}:</span>{' '}
                {claim.predicate} = <span className="font-mono text-aegis-accent-light">{claim.value} {claim.unit || ''}</span>
                {claim.source_doc && <span className="text-aegis-text-dim ml-2">— {claim.source_doc}</span>}
              </p>
            </div>
          ))}

          {/* Evidence snippets */}
          {response.evidence.length > 0 && (
            <div className="space-y-1">
              <p className="text-[10px] uppercase tracking-wider text-aegis-text-dim font-semibold">Evidence</p>
              {response.evidence.map((ev, j) => (
                <div key={j} className="flex items-start gap-2 text-xs text-aegis-text-muted bg-aegis-bg/30 rounded p-2">
                  <FileText className="w-3 h-3 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-mono text-aegis-accent-light">{ev.document_name}</span>
                    {ev.page_number && <span className="ml-1">p.{ev.page_number}</span>}
                    {ev.snippet && <p className="italic mt-0.5 text-aegis-text-dim">"{ev.snippet.slice(0, 120)}"</p>}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Conflicts */}
          {response.conflicts.length > 0 && (
            <div className="bg-amber-500/5 border border-amber-500/20 rounded-lg p-3 text-xs">
              <div className="flex items-center gap-1 text-amber-400 font-semibold mb-1">
                <AlertTriangle className="w-3 h-3" /> Conflicts Detected
              </div>
              {response.conflicts.map((c, i) => (
                <div key={i} className="text-aegis-text-muted mt-1">
                  <p>{c.description}</p>
                  {c.conflicting_values.map((v, j) => (
                    <p key={j} className="pl-2">• {v}</p>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const sendMessage = async () => {
    const q = input.trim()
    if (!q || loading) return
    setInput('')

    const userMsg: ChatMessage = { id: Date.now().toString(), role: 'user', content: q }
    const loadingMsg: ChatMessage = { id: (Date.now() + 1).toString(), role: 'assistant', content: '', loading: true }
    setMessages(prev => [...prev, userMsg, loadingMsg])
    setLoading(true)

    try {
      const response: QueryResponse = await api.submitQuery(q)
      setMessages(prev => prev.map(m => m.id === loadingMsg.id
        ? { ...m, content: response.answer, response, loading: false }
        : m
      ))
    } catch (e: any) {
      setMessages(prev => prev.map(m => m.id === loadingMsg.id
        ? { ...m, content: `Error: ${e.message}`, loading: false }
        : m
      ))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="p-6 border-b border-aegis-border">
        <h1 className="text-xl font-bold text-white">Ask Aegis</h1>
        <p className="text-aegis-text-muted text-sm mt-0.5">Evidence-grounded answers from the Aegis Series-7 knowledge base</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-aegis-accent to-purple-500 flex items-center justify-center mb-4 shadow-lg shadow-aegis-accent/20">
              <Shield className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-lg font-semibold text-white">Aegis Knowledge System</h2>
            <p className="text-aegis-text-muted text-sm mt-2 max-w-md">
              Ask questions about the Aegis Series-7 Hydraulic Control System. Answers are grounded in ingested documentation with full evidence citations.
            </p>
            <div className="mt-6 space-y-2">
              {['What is the operating pressure of the HPU-5000?', 'What housing material is specified?', 'What is the flow rate of the PRV-200?'].map(q => (
                <button key={q} onClick={() => setInput(q)} className="block text-sm text-aegis-accent-light hover:text-white bg-aegis-accent/5 hover:bg-aegis-accent/10 border border-aegis-accent/10 rounded-lg px-4 py-2 transition-colors w-full text-left">
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map(msg => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-2xl rounded-xl px-4 py-3 ${
              msg.role === 'user'
                ? 'bg-aegis-accent text-white rounded-br-sm'
                : 'glass rounded-bl-sm'
            }`}>
              {msg.loading ? (
                <div className="flex items-center gap-2 text-aegis-text-muted">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Analyzing evidence...</span>
                </div>
              ) : (
                <>
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  {msg.response && <EvidencePanel response={msg.response} />}
                </>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-aegis-border">
        <div className="max-w-3xl mx-auto flex gap-2">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() } }}
            placeholder="Ask about the Aegis Series-7..."
            className="flex-1 bg-aegis-card border border-aegis-border rounded-xl px-4 py-3 text-sm text-white placeholder-aegis-text-dim focus:outline-none focus:border-aegis-accent/50 focus:ring-1 focus:ring-aegis-accent/20 transition-colors"
          />
          <button onClick={sendMessage} disabled={loading || !input.trim()} className="px-4 py-3 bg-aegis-accent rounded-xl text-white hover:bg-aegis-accent-light transition-colors disabled:opacity-40">
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
