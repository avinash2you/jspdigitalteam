'use client';

import React from 'react';
import Link from 'next/link';
import { SearchResultItem, AssetType } from '@jsp/shared';

export interface SearchResultCardProps {
  item: SearchResultItem;
}

const ASSET_TYPE_LABELS: Record<string, { label: string; bg: string; text: string }> = {
  [AssetType.GOVERNMENT_DOCUMENT]: { label: 'Govt Document (GO)', bg: '#ede9fe', text: '#5b21b6' },
  [AssetType.NEWSPAPER_CLIPPING]: { label: 'Newspaper Clipping', bg: '#fef3c7', text: '#92400e' },
  [AssetType.ONLINE_NEWS_SOCIAL]: { label: 'Online / Social News', bg: '#e0f2fe', text: '#0369a1' },
  [AssetType.VIDEO_AUDIO]: { label: 'Video / Audio Speech', bg: '#fee2e2', text: '#991b1b' },
  [AssetType.IMAGE_INFOGRAPHIC]: { label: 'Image / Infographic', bg: '#fce7f3', text: '#9d174d' },
  [AssetType.RESEARCH_MATERIAL]: { label: 'Research Material', bg: '#dcfce7', text: '#166534' },
};

/**
 * Safely parse snippet text so only <mark>...</mark> tags render as highlighted React nodes,
 * preventing any raw HTML injection.
 */
function renderSafeHighlightedSnippet(text: string): React.ReactNode {
  if (!text) return null;

  const parts = text.split(/(<\/?mark>)/gi);
  let isMarked = false;

  return parts.map((part, index) => {
    const lower = part.toLowerCase();
    if (lower === '<mark>') {
      isMarked = true;
      return null;
    }
    if (lower === '</mark>') {
      isMarked = false;
      return null;
    }

    if (isMarked) {
      return (
        <mark
          key={index}
          style={{
            backgroundColor: '#fef08a',
            color: '#854d0e',
            fontWeight: 600,
            padding: '0 0.2rem',
            borderRadius: '2px',
          }}
        >
          {part}
        </mark>
      );
    }

    return <span key={index}>{part}</span>;
  });
}

export function SearchResultCard({ item }: SearchResultCardProps) {
  const typeConfig = ASSET_TYPE_LABELS[item.asset_type] || {
    label: item.asset_type,
    bg: '#f3f4f6',
    text: '#374151',
  };

  const snippetToDisplay = item.highlighted_snippet || item.snippet;

  return (
    <article
      data-testid={`search-card-${item.id}`}
      style={{
        backgroundColor: '#ffffff',
        border: '1px solid #e5e7eb',
        borderRadius: '8px',
        padding: '1.25rem',
        marginBottom: '1rem',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
      }}
    >
      {/* Top Header: Badge & Date */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span
            data-testid="asset-type-badge"
            style={{
              backgroundColor: typeConfig.bg,
              color: typeConfig.text,
              fontSize: '0.75rem',
              fontWeight: 600,
              padding: '0.2rem 0.5rem',
              borderRadius: '4px',
              textTransform: 'uppercase',
            }}
          >
            {typeConfig.label}
          </span>

          {item.go_number && (
            <span
              data-testid="go-number-badge"
              style={{
                backgroundColor: '#f1f5f9',
                color: '#0f172a',
                fontSize: '0.75rem',
                fontWeight: 700,
                padding: '0.2rem 0.5rem',
                borderRadius: '4px',
                border: '1px solid #cbd5e1',
              }}
            >
              {item.go_number}
            </span>
          )}
        </div>

        {item.publication_date && (
          <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>
            📅 {item.publication_date}
          </span>
        )}
      </div>

      {/* Main Title & Link */}
      <div>
        <h3 style={{ margin: '0 0 0.25rem 0', fontSize: '1.15rem', fontWeight: 600 }}>
          <Link
            href={`/repository/${item.id}`}
            data-testid={`result-link-${item.id}`}
            style={{
              color: '#1d4ed8',
              textDecoration: 'none',
            }}
          >
            {item.headline || item.title}
          </Link>
        </h3>
        {item.source_name && (
          <span style={{ fontSize: '0.8rem', color: '#4b5563' }}>
            Source: <strong>{item.source_name}</strong>
          </span>
        )}
      </div>

      {/* Highlighted Snippet */}
      {snippetToDisplay && (
        <p
          data-testid="search-snippet"
          style={{
            margin: 0,
            fontSize: '0.9rem',
            lineHeight: '1.5',
            color: '#374151',
          }}
        >
          {renderSafeHighlightedSnippet(snippetToDisplay)}
        </p>
      )}

      {/* Footer: Geographic Tags & Preview */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.5rem',
          borderTop: '1px solid #f3f4f6',
          paddingTop: '0.5rem',
          marginTop: 'auto',
        }}
      >
        {/* Geo Tags */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
          {item.geo_tags &&
            item.geo_tags.map((geo) => (
              <span
                key={geo.id}
                data-testid={`geo-badge-${geo.id}`}
                style={{
                  fontSize: '0.75rem',
                  backgroundColor: '#f0fdf4',
                  color: '#166534',
                  padding: '0.15rem 0.45rem',
                  borderRadius: '9999px',
                }}
              >
                📍 {geo.name} {geo.telugu_name ? `(${geo.telugu_name})` : ''}
              </span>
            ))}
        </div>

        {/* View Detail Link */}
        <Link
          href={`/repository/${item.id}`}
          style={{
            fontSize: '0.825rem',
            fontWeight: 600,
            color: '#dc2626',
            textDecoration: 'none',
          }}
        >
          View Full Asset →
        </Link>
      </div>
    </article>
  );
}
