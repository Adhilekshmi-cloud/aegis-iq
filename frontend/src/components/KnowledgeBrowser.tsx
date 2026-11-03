import { useState, useEffect } from 'react'
import { Search, CheckCircle, AlertTriangle, HelpCircle, FileText, ChevronDown, ChevronUp } from 'lucide-react'
import { api } from '../services/api'
import type { Fact } from '../types'

const statusColors: Record<string, string> = {
  verified: 'border-aegis-success/30 bg-aegis-success/5',
  conflicting: 'border-aegis-warning/30 bg-aegis-warning/5',
  unverified: 'border-aegis-text-dim/30 bg-aegis-card',
  superseded: 'border-aegis-danger/20 bg-aegis-danger/5',
}

const statusIcons: Record<string, React.ElementType> = {
  verified: CheckCircle,
  conflicting: AlertTriangle,
  unverified: HelpCircle,
  superseded: HelpCircle,
}

const statusLabels: Record<string, { text: string; color: string }> = {
  verified: { text: 'Verified', color: 'text-aegis-success' },
  conflicting: { text: 'Conflicting', color: 'text-aegis-warning' },
  unverified: { text: 'Unverified', color: 'text-aegis-text-dim' },
  superseded: { text: 'Superseded', color: 'text-aegis-danger' },
}

export default function KnowledgeBrowser() {
  const [facts, setFacts] = useState<Fact[]>([])
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const fetchFacts = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (filter !== 'all') params.status = filter
      const data = await api.getFacts(params)
      setFacts(Array.isArray(data) ? data : [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchFacts() }, [filter])

  const filtered = facts.filter(f => {
    if (!search) return true
    const s = search.toLowerCase()
    return (f.predicate?.toLowerCase().includes(s) || f.value?.toLowerCase().includes(s))
  })

  const toggleExpand = (id: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Knowledge Browser</h1>
        <p className="text-aegis-text-muted text-sm mt-1">Browse extracted facts with provenance and verification status</p>
      </div>

      {/* Search & Filter */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-aegis-text-dim" />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search facts..." className="w-full bg-aegis-card border border-aegis-border rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-aegis-text-dim focus:outline-none focus:border-aegis-accent/50" />
        </div>
        <div className="flex gap-1 bg-aegis-card rounded-lg border border-aegis-border p-1">
          {['all', 'verified', 'conflicting', 'unverified'].map(f => (
            <button key={f} onClick={() => setFilter(f)} className={`px-3 py-1.5 rounded text-xs font-medium capitalize transition-colors ${filter === f ? 'bg-aegis-accent text-white' : 'text-aegis-text-muted hover:text-white'}`}>
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Facts */}
      <div className="space-y-2">
        {loading ? (
          <div className="text-center py-12 text-aegis-text-muted">Loading facts...</div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="w-12 h-12 text-aegis-text-dim mx-auto mb-3" />
            <p className="text-aegis-text-muted">No facts found</p>
            <p className="text-aegis-text-dim text-sm">Ingest documents first to populate the knowledge base</p>
          </div>
        ) : filtered.map(fact => {
          const status = fact.verification_status || 'unverified'
          const Icon = statusIcons[status] || HelpCircle
          const label = statusLabels[status] || statusLabels.unverified
          const isExpanded = expanded.has(fact.fact_id)

          return (
            <div key={fact.fact_id} className={`border rounded-xl p-4 transition-colors hover:bg-white/[0.02] ${statusColors[status] || statusColors.unverified}`}>
              <div className="flex items-start justify-between cursor-pointer" onClick={() => toggleExpand(fact.fact_id)}>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <Icon className={`w-4 h-4 ${label.color}`} />
                    <span className={`text-xs font-semibold uppercase ${label.color}`}>{label.text}</span>
                    {fact.is_current && <span className="text-[10px] px-2 py-0.5 bg-aegis-accent/10 text-aegis-accent-light rounded-full border border-aegis-accent/20">current</span>}
                  </div>
                  <p className="text-white font-medium">
                    {fact.predicate.replace(/_/g, ' ')} = <span className="text-aegis-accent-light font-mono">{fact.value} {fact.unit || ''}</span>
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-aegis-text-dim">conf: {(fact.confidence_score * 100).toFixed(0)}%</span>
                  {isExpanded ? <ChevronUp className="w-4 h-4 text-aegis-text-dim" /> : <ChevronDown className="w-4 h-4 text-aegis-text-dim" />}
                </div>
              </div>

              {isExpanded && fact.evidence && fact.evidence.length > 0 && (
                <div className="mt-3 pl-6 space-y-2 border-l-2 border-aegis-accent/20">
                  {fact.evidence.map((ev, i) => (
                    <div key={i} className="text-xs text-aegis-text-muted">
                      <div className="flex items-center gap-2">
                        <FileText className="w-3 h-3" />
                        <span className="font-mono text-aegis-accent-light">{ev.extraction_method}</span>
                        {ev.page_number && <span>p.{ev.page_number}</span>}
                      </div>
                      {ev.snippet && <p className="mt-1 italic pl-5">"{ev.snippet.slice(0, 150)}"</p>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
