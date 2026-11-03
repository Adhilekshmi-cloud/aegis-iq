import { useState, useEffect } from 'react'
import { Search, Network, ChevronDown, ChevronUp, Tag } from 'lucide-react'
import { api } from '../services/api'
import type { Entity } from '../types'

const entityTypeColors: Record<string, string> = {
  component: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  system: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  subsystem: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
  parameter: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  material: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  fluid: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
}

const methodBadge = (method: string) => {
  const colors: Record<string, string> = {
    exact: 'bg-emerald-500/10 text-emerald-400',
    normalized: 'bg-blue-500/10 text-blue-400',
    fuzzy: 'bg-amber-500/10 text-amber-400',
    hmi_mapping: 'bg-purple-500/10 text-purple-400',
    model: 'bg-red-500/10 text-red-400',
  }
  return <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${colors[method] || 'bg-gray-500/10 text-gray-400'}`}>{method}</span>
}

export default function EntityBrowser() {
  const [entities, setEntities] = useState<Entity[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const fetchEntities = async () => {
    setLoading(true)
    try {
      const data = await api.getEntities()
      setEntities(Array.isArray(data) ? data : [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchEntities() }, [])

  const toggleExpand = (id: string) => {
    setExpanded(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n })
  }

  const filtered = entities.filter(e => {
    if (!search) return true
    const s = search.toLowerCase()
    return e.canonical_name?.toLowerCase().includes(s) || e.aliases?.some(a => a.alias_name?.toLowerCase().includes(s))
  })

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Entity Browser</h1>
        <p className="text-aegis-text-muted text-sm mt-1">Components, systems, and their alias mappings</p>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-aegis-text-dim" />
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search entities or aliases..." className="w-full bg-aegis-card border border-aegis-border rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-aegis-text-dim focus:outline-none focus:border-aegis-accent/50" />
      </div>

      <div className="space-y-2">
        {loading ? (
          <div className="text-center py-12 text-aegis-text-muted">Loading entities...</div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12">
            <Network className="w-12 h-12 text-aegis-text-dim mx-auto mb-3" />
            <p className="text-aegis-text-muted">No entities found</p>
          </div>
        ) : filtered.map(entity => {
          const isExpanded = expanded.has(entity.entity_id)
          const typeColor = entityTypeColors[entity.entity_type] || 'bg-gray-500/20 text-gray-400 border-gray-500/30'

          return (
            <div key={entity.entity_id} className="glass rounded-xl overflow-hidden">
              <div className="p-4 cursor-pointer hover:bg-white/[0.02] transition-colors" onClick={() => toggleExpand(entity.entity_id)}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium uppercase ${typeColor}`}>{entity.entity_type}</span>
                    <h3 className="text-white font-semibold">{entity.canonical_name}</h3>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-aegis-text-dim">{entity.aliases?.length || 0} alias(es)</span>
                    {isExpanded ? <ChevronUp className="w-4 h-4 text-aegis-text-dim" /> : <ChevronDown className="w-4 h-4 text-aegis-text-dim" />}
                  </div>
                </div>
                {entity.description && <p className="text-sm text-aegis-text-muted mt-1 pl-20">{entity.description}</p>}
              </div>

              {isExpanded && entity.aliases?.length > 0 && (
                <div className="border-t border-aegis-border px-4 py-3 space-y-1.5 bg-aegis-bg/30">
                  <p className="text-[10px] uppercase tracking-wider text-aegis-text-dim font-semibold mb-2 flex items-center gap-1">
                    <Tag className="w-3 h-3" /> Aliases
                  </p>
                  {entity.aliases.map((alias) => (
                    <div key={alias.alias_id} className="flex items-center gap-3 text-sm">
                      <span className="text-white font-mono">{alias.alias_name}</span>
                      {methodBadge(alias.resolution_method)}
                      <span className="text-[10px] text-aegis-text-dim">conf: {(alias.confidence_score * 100).toFixed(0)}%</span>
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
