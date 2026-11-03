import React, { useState } from 'react';
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  FileText,
  CheckCircle2,
  Clock,
  ShieldAlert,
} from 'lucide-react';
import { Conflict, ConflictInfo } from '../types';

interface ConflictIndicatorProps {
  conflict: Conflict | ConflictInfo;
  defaultExpanded?: boolean;
}

export const ConflictIndicator: React.FC<ConflictIndicatorProps> = ({
  conflict,
  defaultExpanded = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // Normalize conflict attributes between backend Conflict and QueryResponse ConflictInfo
  const predicate = conflict.predicate;
  const description = conflict.description;
  const status = conflict.status;
  const conflictType = 'conflict_type' in conflict ? conflict.conflict_type : 'value_mismatch';
  const resolutionNotes = conflict.resolution_notes;

  // Extract conflicting facts/values
  const conflictingValues: Array<{
    value: string;
    source?: string;
    trust?: string;
    revision?: string;
  }> = [];

  if ('facts' in conflict && Array.isArray(conflict.facts)) {
    conflict.facts.forEach((f) => {
      const docName = (f.evidence?.[0] as any)?.document_name || f.evidence?.[0]?.document_id || 'Document';
      conflictingValues.push({
        value: `${f.value} ${f.unit || ''}`.trim(),
        source: docName,
        trust: (f.meta_info?.trust_level as string) || undefined,
        revision: (f.meta_info?.revision as string) || undefined,
      });
    });
  } else if ('conflicting_values' in conflict && Array.isArray(conflict.conflicting_values)) {
    conflict.conflicting_values.forEach((v) => {
      conflictingValues.push({ value: v });
    });
  }

  const getStatusBadge = () => {
    switch (status) {
      case 'resolved_by_revision':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-blue-500/10 text-blue-400 border border-blue-500/30">
            <CheckCircle2 className="w-3 h-3" /> Resolved (Revision)
          </span>
        );
      case 'resolved_by_trust':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3" /> Resolved (Trust Level)
          </span>
        );
      case 'needs_review':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-purple-500/10 text-purple-400 border border-purple-500/30">
            <Clock className="w-3 h-3" /> Needs Review
          </span>
        );
      case 'unresolved':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-500/15 text-amber-300 border border-amber-500/40 animate-pulse">
            <ShieldAlert className="w-3 h-3 text-amber-400" /> Unresolved Conflict
          </span>
        );
    }
  };

  const getConflictTypeBadge = () => {
    const formatted = conflictType.replace(/_/g, ' ');
    let color = 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    if (conflictType === 'version_difference') {
      color = 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30';
    } else if (conflictType === 'source_disagreement') {
      color = 'bg-rose-500/10 text-rose-300 border-rose-500/30';
    }
    return (
      <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider border ${color}`}>
        {formatted}
      </span>
    );
  };

  return (
    <div className="rounded-xl border border-amber-500/30 bg-gradient-to-r from-amber-500/10 via-aegis-surface to-aegis-surface p-3.5 shadow-[0_0_20px_rgba(245,158,11,0.1)] transition-all">
      <div
        className="flex items-center justify-between cursor-pointer select-none"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/30 shadow-[0_0_12px_rgba(245,158,11,0.3)]">
            <AlertTriangle className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-semibold text-amber-200">
                Conflict on: <code className="text-amber-400 font-mono">{predicate}</code>
              </span>
              {getConflictTypeBadge()}
              {getStatusBadge()}
            </div>
            <p className="text-xs text-aegis-text-muted mt-0.5">{description}</p>
          </div>
        </div>

        <button
          type="button"
          className="text-aegis-text-dim hover:text-aegis-text transition-colors p-1"
          aria-label={isExpanded ? 'Collapse conflict details' : 'Expand conflict details'}
        >
          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {isExpanded && (
        <div className="mt-3 pt-3 border-t border-aegis-border/60 space-y-2.5 animate-slide-up">
          <div className="text-[11px] font-medium text-aegis-text-dim uppercase tracking-wider">
            Conflicting Evidence & Values:
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {conflictingValues.map((item, idx) => (
              <div
                key={idx}
                className="rounded-lg bg-aegis-card/80 border border-aegis-border p-2.5 flex flex-col justify-between"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-amber-300">
                    {item.value}
                  </span>
                  {item.revision && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-aegis-surface text-aegis-text-dim border border-aegis-border font-mono">
                      {item.revision}
                    </span>
                  )}
                </div>
                {item.source && (
                  <div className="flex items-center gap-1.5 mt-2 text-[11px] text-aegis-text-muted truncate">
                    <FileText className="w-3 h-3 flex-shrink-0 text-aegis-accent-light" />
                    <span className="truncate">{item.source}</span>
                    {item.trust && (
                      <span className="ml-auto text-[10px] text-aegis-text-dim capitalize">
                        ({item.trust} trust)
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          {resolutionNotes && (
            <div className="rounded-lg bg-indigo-950/30 border border-indigo-500/20 p-2.5 mt-2">
              <span className="text-[11px] font-semibold text-indigo-300 block mb-0.5">
                Resolution Reasoning:
              </span>
              <p className="text-xs text-indigo-200/90 leading-relaxed">
                {resolutionNotes}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
export default ConflictIndicator;
