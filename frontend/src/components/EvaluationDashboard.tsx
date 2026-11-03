import { useState, useEffect } from 'react'
import { Play, Loader2, CheckCircle, XCircle, Clock, ClipboardCheck, Target, BarChart3 } from 'lucide-react'
import { api } from '../services/api'
import type { EvaluationResult, QuestionResult } from '../types'

function MetricCard({ label, value, icon: Icon, color }: { label: string; value: string; icon: React.ElementType; color: string }) {
  return (
    <div className="glass rounded-xl p-4 hover:bg-white/[0.02] transition-colors">
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-4 h-4 ${color}`} />
        <span className="text-xs text-aegis-text-muted uppercase tracking-wider">{label}</span>
      </div>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  )
}

export default function EvaluationDashboard() {
  const [result, setResult] = useState<EvaluationResult | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchResults = async () => {
    try {
      const data = await api.getEvaluationResults()
      if (data && data.metrics) setResult(data)
    } catch {
      // No results yet — that's fine
    }
  }

  const runEvaluation = async () => {
    setRunning(true)
    setError(null)
    try {
      const data = await api.runEvaluation()
      if (data && data.metrics) setResult(data)
      else await fetchResults()
    } catch (e: any) {
      setError(e.message)
    } finally {
      setRunning(false)
    }
  }

  useEffect(() => { fetchResults() }, [])

  const m = result?.metrics
  const pct = (n: number) => `${(n * 100).toFixed(1)}%`

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Evaluation Dashboard</h1>
          <p className="text-aegis-text-muted text-sm mt-1">Automated testing against benchmark questions</p>
        </div>
        <button onClick={runEvaluation} disabled={running} className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-aegis-accent to-purple-500 text-white rounded-xl font-semibold text-sm hover:shadow-lg hover:shadow-aegis-accent/25 transition-all disabled:opacity-50">
          {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
          {running ? 'Running...' : 'Run Evaluation'}
        </button>
      </div>

      {error && <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-400 text-sm">{error}</div>}

      {!m ? (
        <div className="text-center py-20">
          <ClipboardCheck className="w-16 h-16 text-aegis-text-dim mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-aegis-text-muted">No evaluation results yet</h2>
          <p className="text-aegis-text-dim text-sm mt-2">Click "Run Evaluation" to test the system against benchmark questions</p>
        </div>
      ) : (
        <>
          {/* Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            <MetricCard label="Accuracy" value={pct(m.accuracy)} icon={Target} color="text-aegis-success" />
            <MetricCard label="Passed" value={`${m.passed_questions}/${m.total_questions}`} icon={CheckCircle} color="text-blue-400" />
            <MetricCard label="Evidence Grounding" value={pct(m.evidence_grounding_ratio)} icon={BarChart3} color="text-emerald-400" />
            <MetricCard label="Conflict Detection" value={pct(m.conflict_detection_rate)} icon={Target} color="text-amber-400" />
            <MetricCard label="Avg Latency" value={`${m.avg_latency_ms.toFixed(0)}ms`} icon={Clock} color="text-aegis-text-muted" />
          </div>

          {/* Per-Question Table */}
          <div className="glass rounded-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-aegis-border">
              <h2 className="font-semibold text-white">Per-Question Results ({m.total_questions} questions)</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-aegis-border text-aegis-text-muted text-xs">
                    <th className="text-left px-4 py-3">ID</th>
                    <th className="text-left px-4 py-3">Question</th>
                    <th className="text-center px-4 py-3">Passed</th>
                    <th className="text-center px-4 py-3">Accuracy</th>
                    <th className="text-center px-4 py-3">Grounding</th>
                    <th className="text-center px-4 py-3">Claims</th>
                    <th className="text-center px-4 py-3">Conflicts</th>
                    <th className="text-right px-4 py-3">Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {result.results.map((q: QuestionResult) => (
                    <tr key={q.question_id} className={`border-b border-aegis-border/30 ${q.passed ? 'bg-aegis-success/[0.03]' : 'bg-aegis-danger/[0.03]'}`}>
                      <td className="px-4 py-3 font-mono text-aegis-accent-light">{q.question_id}</td>
                      <td className="px-4 py-3 text-white max-w-xs truncate">{q.question}</td>
                      <td className="px-4 py-3 text-center">{q.passed ? <CheckCircle className="w-4 h-4 text-aegis-success inline" /> : <XCircle className="w-4 h-4 text-aegis-danger inline" />}</td>
                      <td className="px-4 py-3 text-center text-aegis-text-muted">{(q.accuracy_score * 100).toFixed(0)}%</td>
                      <td className="px-4 py-3 text-center text-aegis-text-muted">{(q.evidence_grounding_score * 100).toFixed(0)}%</td>
                      <td className="px-4 py-3 text-center text-aegis-text-muted">{q.claims_count}</td>
                      <td className="px-4 py-3 text-center text-aegis-text-muted">{q.conflicts_detected}</td>
                      <td className="px-4 py-3 text-right text-aegis-text-dim font-mono">{q.latency_ms.toFixed(0)}ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
