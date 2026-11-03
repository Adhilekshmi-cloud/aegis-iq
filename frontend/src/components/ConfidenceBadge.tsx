import React, { useState } from 'react';

interface ConfidenceBadgeProps {
  confidence: number; // 0.0 - 1.0 or 0 - 100
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  confidence,
  size = 'md',
  showLabel = false,
  className = '',
}) => {
  const [showTooltip, setShowTooltip] = useState(false);

  // Normalize to 0-1 range
  const normalizedScore = confidence > 1 ? confidence / 100 : Math.max(0, Math.min(1, confidence));
  const percentage = Math.round(normalizedScore * 100);

  // Determine category and styling
  let colorClasses = '';
  let glowClasses = '';
  let strokeColor = '';
  let categoryLabel = '';
  const isLow = normalizedScore < 0.5;

  if (normalizedScore >= 0.8) {
    colorClasses = 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
    glowClasses = 'shadow-[0_0_10px_rgba(16,185,129,0.25)]';
    strokeColor = '#10b981';
    categoryLabel = 'High Confidence';
  } else if (normalizedScore >= 0.5) {
    colorClasses = 'text-amber-400 bg-amber-500/10 border-amber-500/30';
    glowClasses = 'shadow-[0_0_10px_rgba(245,158,11,0.25)]';
    strokeColor = '#f59e0b';
    categoryLabel = 'Moderate Confidence';
  } else {
    colorClasses = 'text-rose-400 bg-rose-500/10 border-rose-500/30';
    glowClasses = 'shadow-[0_0_10px_rgba(239,68,68,0.3)] animate-pulse';
    strokeColor = '#ef4444';
    categoryLabel = 'Low Confidence / Uncertain';
  }

  const dimensions = {
    sm: { circle: 28, radius: 11, stroke: 2.5, text: 'text-[10px]' },
    md: { circle: 38, radius: 15, stroke: 3, text: 'text-xs' },
    lg: { circle: 50, radius: 20, stroke: 3.5, text: 'text-sm font-semibold' },
  }[size];

  const circumference = 2 * Math.PI * dimensions.radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div
      className={`relative inline-flex items-center gap-2 select-none ${className}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <div
        className={`relative flex items-center justify-center rounded-full border ${colorClasses} ${glowClasses} transition-all duration-300`}
        style={{ width: dimensions.circle, height: dimensions.circle }}
      >
        <svg
          className="absolute -rotate-90 transform"
          width={dimensions.circle}
          height={dimensions.circle}
        >
          {/* Background circle track */}
          <circle
            cx={dimensions.circle / 2}
            cy={dimensions.circle / 2}
            r={dimensions.radius}
            fill="transparent"
            stroke="rgba(255, 255, 255, 0.08)"
            strokeWidth={dimensions.stroke}
          />
          {/* Progress circle */}
          <circle
            cx={dimensions.circle / 2}
            cy={dimensions.circle / 2}
            r={dimensions.radius}
            fill="transparent"
            stroke={strokeColor}
            strokeWidth={dimensions.stroke}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-700 ease-out"
          />
        </svg>

        <span className={`font-mono font-medium ${dimensions.text} tracking-tight`}>
          {percentage}%
        </span>
      </div>

      {showLabel && (
        <span className="text-xs font-medium text-aegis-text-muted">
          {categoryLabel}
        </span>
      )}

      {/* Tooltip */}
      {showTooltip && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 px-3 py-1.5 rounded-lg bg-aegis-surface border border-aegis-border shadow-xl backdrop-blur-md text-xs whitespace-nowrap pointer-events-none animate-fade-in">
          <div className="flex items-center gap-1.5">
            <span
              className="inline-block w-2 h-2 rounded-full"
              style={{ backgroundColor: strokeColor }}
            />
            <span className="font-semibold text-aegis-text">{categoryLabel}</span>
            <span className="text-aegis-text-muted">({(normalizedScore * 100).toFixed(1)}%)</span>
          </div>
          <p className="text-[10px] text-aegis-text-dim mt-0.5">
            {normalizedScore >= 0.8
              ? 'Strongly grounded by verifiable multi-source evidence'
              : normalizedScore >= 0.5
              ? 'Supported by single source or secondary reference'
              : 'Requires review — weak evidence or unresolved conflict'}
          </p>
        </div>
      )}
    </div>
  );
};
export default ConfidenceBadge;
