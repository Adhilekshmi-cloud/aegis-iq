import React, { useState } from 'react';
import {
  FileText,
  Quote,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Cpu,
  BookmarkCheck,
} from 'lucide-react';
import { Claim, EvidenceItem, ConflictInfo } from '../types';
import ConfidenceBadge from './ConfidenceBadge';
import ConflictIndicator from './ConflictIndicator';

interface EvidencePanelProps {
  claims?: Claim[];
  evidence?: EvidenceItem[];
  conflicts?: ConflictInfo[];
  confidence?: number;
  defaultExpanded?: boolean;
  className?: string;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  claims = [],
  evidence = [],
  conflicts = [],
  confidence,
  defaultExpanded = false,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null);

  const totalClaims = claims.length;
  const totalEvidence = evidence.length;
  const totalConflicts = conflicts.length;

  if (totalClaims === 0 && totalEvidence === 0 && totalConflicts === 0) {
    return null;
  }

  return (
    <div
      className={`rounded-xl glass-card border border-aegis-border/80 overflow-hidden transition-all duration-300 ${
        isExpanded ? 'shadow-[0_4px_24px_rgba(99,102,241,0.12)] border-indigo-500/40' : ''
      } ${className}`}
    >
      {/* Header bar / toggle */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="flex items-center justify-center w-6 h-6 rounded-md bg-indigo-500/20 text-aegis-accent-light border border-indigo-500/30">
            <ShieldCheck className="w-3.5 h-3.5" />
          </div>

          <span className="text-xs font-semibold tracking-wide text-aegis-text uppercase">
            Grounding & Provenance
          </span>

          <div className="flex items-center gap-1.5 ml-2">
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-aegis-surface text-aegis-text-muted border border-aegis-border font-mono">
              {totalClaims} {totalClaims === 1 ? 'claim' : 'claims'}
            </span>
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-aegis-surface text-aegis-text-muted border border-aegis-border font-mono">
              {totalEvidence} {totalEvidence === 1 ? 'source' : 'sources'}
            </span>
            {totalConflicts > 0 && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 font-medium">
                {totalConflicts} conflict{totalConflicts > 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          {confidence !== undefined && (
            <ConfidenceBadge confidence={confidence} size="sm" />
          )}
          <span className="text-aegis-text-dim hover:text-aegis-text transition-colors">
            {isExpanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </span>
        </div>
      </button>

      {/* Expandable Content */}
      {isExpanded && (
        <div className="px-4 pb-4 pt-1 space-y-4 border-t border-aegis-border/50 animate-fade-in">
          {/* Conflicts Section if any */}
          {conflicts.length > 0 && (
            <div className="space-y-2">
              <span className="text-[11px] font-semibold tracking-wider uppercase text-amber-400/90 flex items-center gap-1.5">
                Attention: Detected Conflicts
              </span>
              <div className="space-y-2">
                {conflicts.map((conflict, index) => (
                  <ConflictIndicator key={conflict.conflict_id || index} conflict={conflict} />
                ))}
              </div>
            </div>
          )}

          {/* Claims breakdown */}
          {claims.length > 0 && (
            <div className="space-y-2">
              <span className="text-[11px] font-semibold tracking-wider uppercase text-aegis-text-dim flex items-center gap-1.5">
                <BookmarkCheck className="w-3.5 h-3.5 text-aegis-accent-light" /> Extracted
                Claims
              </span>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {claims.map((claim) => {
                  const isSelected = selectedClaimId === claim.claim_id;
                  return (
                    <div
                      key={claim.claim_id}
                      onClick={() =>
                        setSelectedClaimId(isSelected ? null : claim.claim_id)
                      }
                      className={`p-2.5 rounded-lg border cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-indigo-950/40 border-indigo-500/50 shadow-[0_0_12px_rgba(99,102,241,0.2)]'
                          : 'bg-aegis-surface/60 border-aegis-border/80 hover:border-aegis-accent/40'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-1.5 text-xs font-medium text-aegis-text truncate">
                          <Cpu className="w-3 h-3 text-aegis-accent-light flex-shrink-0" />
                          <span className="truncate">{claim.entity_name}</span>
                        </div>
                        <ConfidenceBadge confidence={claim.confidence} size="sm" />
                      </div>

                      <div className="mt-1.5 flex items-baseline gap-1.5 font-mono text-xs">
                        <span className="text-aegis-text-muted">{claim.predicate}:</span>
                        <span className="font-semibold text-emerald-400">
                          {claim.value} {claim.unit || ''}
                        </span>
                      </div>

                      {claim.source_doc && (
                        <div className="mt-1.5 text-[10px] text-aegis-text-dim flex items-center gap-1 truncate">
                          <FileText className="w-2.5 h-2.5 text-aegis-text-dim flex-shrink-0" />
                          <span className="truncate">{claim.source_doc}</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Evidence Citations */}
          {evidence.length > 0 && (
            <div className="space-y-2">
              <span className="text-[11px] font-semibold tracking-wider uppercase text-aegis-text-dim flex items-center gap-1.5">
                <Quote className="w-3.5 h-3.5 text-indigo-400" /> Source Evidence & Citations
              </span>
              <div className="space-y-2">
                {evidence.map((item, idx) => (
                  <div
                    key={item.evidence_id || idx}
                    className="p-3 rounded-lg bg-aegis-surface/70 border border-aegis-border hover:border-aegis-border/80 transition-colors"
                  >
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-2 text-xs font-medium text-aegis-text-muted truncate">
                        <FileText className="w-3.5 h-3.5 text-aegis-accent flex-shrink-0" />
                        <span className="text-aegis-text font-semibold truncate">
                          {item.document_name || 'Technical Documentation'}
                        </span>
                        {item.page_number && (
                          <span className="px-1.5 py-0.2 rounded bg-aegis-card text-[10px] font-mono border border-aegis-border">
                            Page {item.page_number}
                          </span>
                        )}
                        {item.extraction_method && (
                          <span className="text-[10px] uppercase font-mono text-aegis-text-dim">
                            [{item.extraction_method}]
                          </span>
                        )}
                      </div>

                      <ConfidenceBadge confidence={item.confidence_score} size="sm" />
                    </div>

                    <blockquote className="text-xs text-aegis-text/90 italic pl-2.5 border-l-2 border-indigo-500/60 font-sans leading-relaxed bg-black/10 py-1 rounded-r">
                      "{item.snippet}"
                    </blockquote>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
export default EvidencePanel;
