import { useState, useEffect } from 'react'
import { FileText, Box, BookOpen, AlertTriangle, Upload, Loader2, CheckCircle, XCircle, RefreshCw } from 'lucide-react'
import { api } from '../services/api'
import type { IngestionStatus, Document } from '../types'

interface StatCardProps {
  icon: React.ElementType
  label: string
  value: number | string
  gradient: string
}

function StatCard({ icon: Icon, label, value, gradient }: StatCardProps) {
  return (
    <div className={`rounded-xl p-5 ${gradient} relative overflow-hidden group hover:scale-[1.02] transition-transform duration-200`}>
      <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent" />
      <div className="relative flex items-center justify-between">
        <div>
          <p className="text-xs text-white/70 uppercase tracking-wider font-medium">{label}</p>
          <p className="text-3xl font-bold text-white mt-1">{value}</p>
        </div>
        <Icon className="w-10 h-10 text-white/20" />
      </div>
    </div>
  )
}

const statusIcon = (status: string) => {
  switch (status) {
    case 'completed': return <CheckCircle className="w-4 h-4 text-aegis-success" />
    case 'failed': return <XCircle className="w-4 h-4 text-aegis-danger" />
    case 'processing': return <Loader2 className="w-4 h-4 text-aegis-info animate-spin" />
    default: return <RefreshCw className="w-4 h-4 text-aegis-text-dim" />
  }
}

const trustBadge = (level: string) => {
  const colors: Record<string, string> = {
    high: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    medium: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    low: 'bg-red-500/20 text-red-400 border-red-500/30',
  }
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium uppercase ${colors[level] || 'bg-gray-500/20 text-gray-400 border-gray-500/30'}`}>
      {level}
    </span>
  )
}

export default function IngestionDashboard() {
  const [status, setStatus] = useState<IngestionStatus | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(false)
  const [ingesting, setIngesting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchStatus = async () => {
    setLoading(true)
    try {
      const data = await api.getIngestionStatus()
      setStatus(data)
      const docs = await api.getDocuments()
      setDocuments(Array.isArray(docs) ? docs : [])
      setError(null)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleIngest = async () => {
    setIngesting(true)
    setError(null)
    try {
      await api.ingestDocuments()
      await fetchStatus()
    } catch (e: any) {
      setError(e.message)
    } finally {
      setIngesting(false)
    }
  }

  useEffect(() => { fetchStatus() }, [])

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Ingestion Dashboard</h1>
          <p className="text-aegis-text-muted text-sm mt-1">Document processing status and knowledge statistics</p>
        </div>
        <button
          onClick={handleIngest}
          disabled={ingesting}
          className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-aegis-accent to-purple-500 text-white rounded-xl font-semibold text-sm hover:shadow-lg hover:shadow-aegis-accent/25 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {ingesting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
          {ingesting ? 'Ingesting...' : 'Ingest Documents'}
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-400 text-sm">{error}</div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={FileText} label="Documents" value={status?.total_documents ?? 0} gradient="bg-gradient-to-br from-blue-600 to-blue-800" />
        <StatCard icon={Box} label="Chunks" value={status?.total_chunks ?? 0} gradient="bg-gradient-to-br from-purple-600 to-purple-800" />
        <StatCard icon={BookOpen} label="Facts" value={status?.total_facts ?? 0} gradient="bg-gradient-to-br from-emerald-600 to-emerald-800" />
        <StatCard icon={AlertTriangle} label="Conflicts" value={status?.total_conflicts ?? 0} gradient="bg-gradient-to-br from-amber-600 to-amber-800" />
      </div>

      {/* Document Table */}
      <div className="glass rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-aegis-border flex items-center justify-between">
          <h2 className="font-semibold text-white">Ingested Documents</h2>
          <button onClick={fetchStatus} className="text-aegis-text-muted hover:text-white transition-colors">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {documents.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-aegis-border text-aegis-text-muted">
                  <th className="text-left px-6 py-3 font-medium">Filename</th>
                  <th className="text-left px-4 py-3 font-medium">Type</th>
                  <th className="text-left px-4 py-3 font-medium">Status</th>
                  <th className="text-left px-4 py-3 font-medium">Trust</th>
                  <th className="text-left px-4 py-3 font-medium">Chunks</th>
                  <th className="text-left px-4 py-3 font-medium">Facts</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.document_id} className="border-b border-aegis-border/50 hover:bg-white/[0.02] transition-colors">
                    <td className="px-6 py-3 text-white font-medium">{doc.filename}</td>
                    <td className="px-4 py-3">
                      <span className="text-xs px-2 py-0.5 rounded bg-aegis-accent/10 text-aegis-accent-light border border-aegis-accent/20 font-mono">
                        {doc.doc_type}
                      </span>
                    </td>
                    <td className="px-4 py-3"><div className="flex items-center gap-2">{statusIcon(doc.extraction_status)}<span>{doc.extraction_status}</span></div></td>
                    <td className="px-4 py-3">{trustBadge(doc.trust_level)}</td>
                    <td className="px-4 py-3 text-aegis-text-muted">{doc.chunk_count}</td>
                    <td className="px-4 py-3 text-aegis-text-muted">{doc.fact_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center">
            <FileText className="w-12 h-12 text-aegis-text-dim mx-auto mb-4" />
            <p className="text-aegis-text-muted">No documents ingested yet</p>
            <p className="text-aegis-text-dim text-sm mt-1">Click "Ingest Documents" to process the Aegis dataset</p>
          </div>
        )}
      </div>
    </div>
  )
}
