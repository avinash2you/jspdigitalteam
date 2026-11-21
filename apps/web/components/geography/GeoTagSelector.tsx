'use client';

import React, { useState, useEffect, useRef } from 'react';
import { GeoEntity } from '@jsp/shared';
import { apiFetch } from '@/lib/api-client';

export interface GeoTagSelectorProps {
  value: GeoEntity[];
  onChange: (next: GeoEntity[]) => void;
  token?: string;
  disabled?: boolean;
  placeholder?: string;
}

const TIER_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  india: { bg: '#fee2e2', text: '#991b1b', label: 'Country' },
  state: { bg: '#ffedd5', text: '#9a3412', label: 'State' },
  district: { bg: '#fef3c7', text: '#92400e', label: 'District' },
  parliamentary_constituency: { bg: '#ecfccb', text: '#3f6212', label: 'Parliamentary' },
  assembly_constituency: { bg: '#dcfce7', text: '#166534', label: 'Assembly' },
  mandal: { bg: '#ccfbf1', text: '#115e59', label: 'Mandal' },
  village: { bg: '#e0e7ff', text: '#3730a3', label: 'Village' },
  municipal_corporation: { bg: '#f3e8ff', text: '#6b21a8', label: 'Corp' },
  municipality: { bg: '#fae8ff', text: '#86198f', label: 'Municipality' },
  ward: { bg: '#fce7f3', text: '#9d174d', label: 'Ward' },
};

export function GeoTagSelector({
  value,
  onChange,
  token,
  disabled = false,
  placeholder = 'Search locations by name or historical alias...',
}: GeoTagSelectorProps) {
  const [query, setQuery] = useState('');
  const [selectedTier, setSelectedTier] = useState<string>('');
  const [results, setResults] = useState<GeoEntity[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!query.trim() && !selectedTier) {
      setResults([]);
      setIsLoading(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const params = new URLSearchParams();
        if (query.trim()) params.set('q', query.trim());
        if (selectedTier) params.set('tier', selectedTier);
        params.set('limit', '20');

        const data = await apiFetch<GeoEntity[]>(`/api/v1/geography/search?${params.toString()}`, {
          token,
        });
        setResults(data);
        setIsOpen(true);
      } catch (err) {
        console.error('Failed to search geography:', err);
      } finally {
        setIsLoading(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [query, selectedTier, token]);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (entity: GeoEntity) => {
    if (!value.some((v) => v.id === entity.id)) {
      onChange([...value, entity]);
    }
    setQuery('');
    setIsOpen(false);
  };

  const handleRemove = (id: string) => {
    onChange(value.filter((v) => v.id !== id));
  };

  return (
    <div
      ref={containerRef}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
        position: 'relative',
        width: '100%',
        fontFamily: 'system-ui, sans-serif',
      }}
      data-testid="geography-tag-selector"
    >
      {/* Selected Tag Chips */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '0.5rem',
          minHeight: value.length > 0 ? 'auto' : '0px',
        }}
        data-testid="selected-tags-container"
      >
        {value.map((tag) => {
          const tierMeta = TIER_COLORS[tag.tier] || {
            bg: '#f3f4f6',
            text: '#374151',
            label: tag.tier,
          };
          const isAlias = Boolean(tag.matched_alias || tag.is_historical);

          return (
            <span
              key={tag.id}
              data-testid={`geo-chip-${tag.id}`}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.375rem',
                padding: '0.25rem 0.625rem',
                borderRadius: '9999px',
                backgroundColor: '#f3f4f6',
                border: '1px solid #e5e7eb',
                fontSize: '0.875rem',
              }}
            >
              <span style={{ fontWeight: 500, color: '#1f2937' }}>{tag.name}</span>
              {tag.telugu_name && (
                <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>({tag.telugu_name})</span>
              )}
              <span
                data-testid="tier-badge"
                style={{
                  backgroundColor: tierMeta.bg,
                  color: tierMeta.text,
                  padding: '0.125rem 0.375rem',
                  borderRadius: '4px',
                  fontSize: '0.6875rem',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                }}
              >
                {tierMeta.label}
              </span>
              {isAlias && (
                <span
                  data-testid="alias-badge"
                  style={{
                    backgroundColor: '#fee2e2',
                    color: '#b91c1c',
                    padding: '0.125rem 0.375rem',
                    borderRadius: '4px',
                    fontSize: '0.6875rem',
                    fontWeight: 600,
                  }}
                >
                  Pre-2022 Alias
                </span>
              )}
              {!disabled && (
                <button
                  type="button"
                  data-testid={`remove-tag-${tag.id}`}
                  aria-label={`Remove ${tag.name}`}
                  onClick={() => handleRemove(tag.id)}
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: '#9ca3af',
                    padding: '0 0.125rem',
                    display: 'inline-flex',
                    alignItems: 'center',
                    fontSize: '1.125rem',
                    lineHeight: 1,
                  }}
                >
                  &times;
                </button>
              )}
            </span>
          );
        })}
      </div>

      {/* Input Controls */}
      <div style={{ display: 'flex', gap: '0.5rem', width: '100%' }}>
        <input
          type="text"
          value={query}
          disabled={disabled}
          placeholder={placeholder}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => {
            if (results.length > 0) setIsOpen(true);
          }}
          style={{
            flex: 1,
            padding: '0.5rem 0.75rem',
            border: '1px solid #d1d5db',
            borderRadius: '6px',
            fontSize: '0.875rem',
            outline: 'none',
          }}
          data-testid="geo-search-input"
        />

        <select
          value={selectedTier}
          disabled={disabled}
          onChange={(e) => setSelectedTier(e.target.value)}
          style={{
            padding: '0.5rem 0.75rem',
            border: '1px solid #d1d5db',
            borderRadius: '6px',
            fontSize: '0.875rem',
            backgroundColor: '#ffffff',
            color: '#374151',
          }}
          data-testid="geo-tier-filter"
        >
          <option value="">All Tiers</option>
          <option value="state">State</option>
          <option value="district">District</option>
          <option value="parliamentary_constituency">Parliamentary</option>
          <option value="assembly_constituency">Assembly</option>
          <option value="mandal">Mandal</option>
          <option value="village">Village</option>
          <option value="municipal_corporation">Corporation</option>
          <option value="municipality">Municipality</option>
          <option value="ward">Ward</option>
        </select>
      </div>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          data-testid="geo-autocomplete-dropdown"
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            zIndex: 50,
            marginTop: '0.25rem',
            backgroundColor: '#ffffff',
            border: '1px solid #e5e7eb',
            borderRadius: '6px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
            maxHeight: '260px',
            overflowY: 'auto',
          }}
        >
          {isLoading ? (
            <div
              data-testid="geo-search-loading"
              style={{ padding: '0.75rem', textAlign: 'center', color: '#6b7280', fontSize: '0.875rem' }}
            >
              Searching locations...
            </div>
          ) : results.length === 0 ? (
            <div
              data-testid="geo-search-no-results"
              style={{ padding: '0.75rem', textAlign: 'center', color: '#9ca3af', fontSize: '0.875rem' }}
            >
              No matching locations found
            </div>
          ) : (
            <ul style={{ listStyle: 'none', margin: 0, padding: '0.25rem 0' }}>
              {results.map((entity) => {
                const isSelected = value.some((v) => v.id === entity.id);
                const tierMeta = TIER_COLORS[entity.tier] || {
                  bg: '#f3f4f6',
                  text: '#374151',
                  label: entity.tier,
                };

                return (
                  <li
                    key={entity.id}
                    data-testid={`geo-option-${entity.id}`}
                    onClick={() => !isSelected && handleSelect(entity)}
                    style={{
                      padding: '0.5rem 0.75rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: isSelected ? 'not-allowed' : 'pointer',
                      backgroundColor: isSelected ? '#f9fafb' : 'transparent',
                      opacity: isSelected ? 0.6 : 1,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontWeight: 500, fontSize: '0.875rem', color: '#111827' }}>
                        {entity.name}
                      </span>
                      {entity.telugu_name && (
                        <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                          ({entity.telugu_name})
                        </span>
                      )}
                      {entity.matched_alias && (
                        <span
                          data-testid="option-alias-hint"
                          style={{
                            fontSize: '0.75rem',
                            color: '#b91c1c',
                            backgroundColor: '#fee2e2',
                            padding: '0.125rem 0.375rem',
                            borderRadius: '4px',
                          }}
                        >
                          Alias: {entity.matched_alias}
                        </span>
                      )}
                    </div>

                    <span
                      style={{
                        backgroundColor: tierMeta.bg,
                        color: tierMeta.text,
                        padding: '0.125rem 0.375rem',
                        borderRadius: '4px',
                        fontSize: '0.6875rem',
                        fontWeight: 600,
                        textTransform: 'uppercase',
                      }}
                    >
                      {tierMeta.label}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
