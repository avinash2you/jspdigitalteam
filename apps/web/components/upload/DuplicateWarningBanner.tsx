'use client';

import React from 'react';
import Link from 'next/link';

export interface DuplicateMatch {
  id: string;
  title: string;
  asset_type: string;
  match_reason: string;
}

export interface DuplicateWarningBannerProps {
  matches: DuplicateMatch[];
  onDismiss?: () => void;
}

const REASON_LABELS: Record<string, string> = {
  checksum_match: 'Exact Checksum / File Match',
  go_number_match: 'Identical GO Number Match',
  source_url_match: 'Identical Source URL Match',
};

export function DuplicateWarningBanner({ matches, onDismiss }: DuplicateWarningBannerProps) {
  if (!matches || matches.length === 0) {
    return null;
  }

  return (
    <div
      role="alert"
      data-testid="duplicate-warning-banner"
      style={{
        backgroundColor: '#fffbeb',
        border: '1px solid #f59e0b',
        borderRadius: '6px',
        padding: '1rem',
        marginBottom: '1.5rem',
        color: '#92400e',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h4
            style={{
              margin: '0 0 0.5rem 0',
              fontWeight: 600,
              fontSize: '1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <span aria-hidden="true">⚠️</span> Potential Duplicate Assets Detected
          </h4>
          <p style={{ margin: '0 0 0.75rem 0', fontSize: '0.875rem' }}>
            The file or identifier you provided matches existing assets in the repository:
          </p>
        </div>
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            data-testid="btn-dismiss-duplicate"
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: '#92400e',
              fontWeight: 'bold',
              fontSize: '1rem',
              padding: '0.25rem',
            }}
            aria-label="Dismiss warning"
          >
            ×
          </button>
        )}
      </div>

      <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.875rem' }}>
        {matches.map((match) => (
          <li key={match.id} style={{ marginBottom: '0.25rem' }}>
            <Link
              href={`/repository/${match.id}`}
              data-testid={`duplicate-link-${match.id}`}
              style={{
                color: '#b45309',
                textDecoration: 'underline',
                fontWeight: 600,
              }}
            >
              {match.title || 'Untitled Asset'}
            </Link>{' '}
            <span style={{ fontSize: '0.75rem', color: '#78350f' }}>
              ({REASON_LABELS[match.match_reason] || match.match_reason} • {match.asset_type})
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
