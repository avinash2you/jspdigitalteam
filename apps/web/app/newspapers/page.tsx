'use client';

import React, { useState, useEffect, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { GeoEntity, NewspaperClippingItem, NewspaperListResponse, UserRole } from '@jsp/shared';
import { AppShell } from '@/components/AppShell';
import { GeoTagSelector } from '@/components/geography/GeoTagSelector';
import { SideBySideClippingViewer } from '@/components/newspapers/SideBySideClippingViewer';
import { apiFetch } from '@/lib/api-client';

function NewspaperArchiveContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Filter states initialized from URL params
  const [newspaperName, setNewspaperName] = useState(searchParams.get('newspaper_name') || '');
  const [edition, setEdition] = useState(searchParams.get('edition') || '');
  const [dateFrom, setDateFrom] = useState(searchParams.get('date_from') || '');
  const [dateTo, setDateTo] = useState(searchParams.get('date_to') || '');
  const [selectedGeoTags, setSelectedGeoTags] = useState<GeoEntity[]>([]);

  // Results & UI states
  const [clippings, setClippings] = useState<NewspaperClippingItem[]>([]);
  const [selectedClipping, setSelectedClipping] = useState<NewspaperClippingItem | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [total, setTotal] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  // Sync state to URL search parameters
  const updateUrlParams = useCallback(
    (params: {
      newspaperName?: string;
      edition?: string;
      dateFrom?: string;
      dateTo?: string;
      geoId?: string;
    }) => {
      const nextParams = new URLSearchParams();
      if (params.newspaperName) nextParams.set('newspaper_name', params.newspaperName);
      if (params.edition) nextParams.set('edition', params.edition);
      if (params.dateFrom) nextParams.set('date_from', params.dateFrom);
      if (params.dateTo) nextParams.set('date_to', params.dateTo);
      if (params.geoId) nextParams.set('geo_id', params.geoId);

      const queryString = nextParams.toString();
      const nextUrl = queryString ? `/newspapers?${queryString}` : '/newspapers';
      router.push(nextUrl);
    },
    [router]
  );

  // Fetch clippings based on current query
  const fetchClippings = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const query = new URLSearchParams();
      if (newspaperName.trim()) query.set('newspaper_name', newspaperName.trim());
      if (edition.trim()) query.set('edition', edition.trim());
      if (dateFrom) query.set('date_from', dateFrom);
      if (dateTo) query.set('date_to', dateTo);
      if (selectedGeoTags.length > 0) query.set('geo_id', selectedGeoTags[0].id);

      const data = await apiFetch<NewspaperListResponse>(
        `/api/v1/newspapers?${query.toString()}`
      );
      setClippings(data.items || []);
      setTotal(data.total || 0);

      // If previously selected clipping is still in the results, update it; otherwise clear
      if (selectedClipping) {
        const found = (data.items || []).find((c) => c.id === selectedClipping.id);
        if (found) setSelectedClipping(found);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch newspaper clippings';
      setError(msg);
      setClippings([]);
      setTotal(0);
    } finally {
      setIsLoading(false);
    }
  }, [newspaperName, edition, dateFrom, dateTo, selectedGeoTags, selectedClipping]);

  // Initial load and when searchParams change externally
  useEffect(() => {
    const qName = searchParams.get('newspaper_name') || '';
    const qEdition = searchParams.get('edition') || '';
    const qDateFrom = searchParams.get('date_from') || '';
    const qDateTo = searchParams.get('date_to') || '';

    setNewspaperName(qName);
    setEdition(qEdition);
    setDateFrom(qDateFrom);
    setDateTo(qDateTo);
  }, [searchParams]);

  // Fetch on mount or when filters trigger
  useEffect(() => {
    fetchClippings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [newspaperName, edition, dateFrom, dateTo, selectedGeoTags]);

  const handleFilterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateUrlParams({
      newspaperName: newspaperName.trim(),
      edition: edition.trim(),
      dateFrom,
      dateTo,
      geoId: selectedGeoTags.length > 0 ? selectedGeoTags[0].id : undefined,
    });
    fetchClippings();
  };

  const handleClearFilters = () => {
    setNewspaperName('');
    setEdition('');
    setDateFrom('');
    setDateTo('');
    setSelectedGeoTags([]);
    router.push('/newspapers');
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Page Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h1
          data-testid="archive-title"
          style={{ fontSize: '1.75rem', fontWeight: 700, color: '#111827', margin: 0 }}
        >
          Newspaper Archive
        </h1>
        <p style={{ color: '#4b5563', fontSize: '0.95rem', marginTop: '0.25rem' }}>
          Browse, filter, and verify Telugu & English newspaper clippings with side-by-side OCR
          inspection.
        </p>
      </div>

      {/* Selected Clipping Side-by-Side Viewer */}
      {selectedClipping && (
        <SideBySideClippingViewer
          clipping={selectedClipping}
          onClose={() => setSelectedClipping(null)}
        />
      )}

      {/* Filter Bar */}
      <form
        onSubmit={handleFilterSubmit}
        data-testid="newspaper-filter-bar"
        style={{
          backgroundColor: '#ffffff',
          borderRadius: '8px',
          border: '1px solid #e5e7eb',
          padding: '1.25rem',
          marginBottom: '2rem',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
        }}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '1rem',
            alignItems: 'flex-end',
          }}
        >
          {/* Newspaper Name */}
          <div>
            <label
              htmlFor="filter-newspaper-name"
              style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#374151', marginBottom: '0.25rem' }}
            >
              Publication Name
            </label>
            <input
              id="filter-newspaper-name"
              type="text"
              data-testid="filter-newspaper-name"
              placeholder="e.g. Eenadu, Sakshi, Andhra Jyothy"
              value={newspaperName}
              onChange={(e) => {
                setNewspaperName(e.target.value);
                updateUrlParams({
                  newspaperName: e.target.value,
                  edition,
                  dateFrom,
                  dateTo,
                  geoId: selectedGeoTags.length > 0 ? selectedGeoTags[0].id : undefined,
                });
              }}
              style={{
                width: '100%',
                padding: '0.5rem 0.75rem',
                fontSize: '0.875rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                boxSizing: 'border-box',
              }}
            />
          </div>

          {/* Edition */}
          <div>
            <label
              htmlFor="filter-edition"
              style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#374151', marginBottom: '0.25rem' }}
            >
              Edition
            </label>
            <input
              id="filter-edition"
              type="text"
              data-testid="filter-edition"
              placeholder="e.g. Amaravati, Visakhapatnam"
              value={edition}
              onChange={(e) => {
                setEdition(e.target.value);
                updateUrlParams({
                  newspaperName,
                  edition: e.target.value,
                  dateFrom,
                  dateTo,
                  geoId: selectedGeoTags.length > 0 ? selectedGeoTags[0].id : undefined,
                });
              }}
              style={{
                width: '100%',
                padding: '0.5rem 0.75rem',
                fontSize: '0.875rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                boxSizing: 'border-box',
              }}
            />
          </div>

          {/* Date From */}
          <div>
            <label
              htmlFor="filter-date-from"
              style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#374151', marginBottom: '0.25rem' }}
            >
              Date From
            </label>
            <input
              id="filter-date-from"
              type="date"
              data-testid="filter-date-from"
              value={dateFrom}
              onChange={(e) => {
                setDateFrom(e.target.value);
                updateUrlParams({
                  newspaperName,
                  edition,
                  dateFrom: e.target.value,
                  dateTo,
                  geoId: selectedGeoTags.length > 0 ? selectedGeoTags[0].id : undefined,
                });
              }}
              style={{
                width: '100%',
                padding: '0.5rem 0.75rem',
                fontSize: '0.875rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                boxSizing: 'border-box',
              }}
            />
          </div>

          {/* Date To */}
          <div>
            <label
              htmlFor="filter-date-to"
              style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#374151', marginBottom: '0.25rem' }}
            >
              Date To
            </label>
            <input
              id="filter-date-to"
              type="date"
              data-testid="filter-date-to"
              value={dateTo}
              onChange={(e) => {
                setDateTo(e.target.value);
                updateUrlParams({
                  newspaperName,
                  edition,
                  dateFrom,
                  dateTo: e.target.value,
                  geoId: selectedGeoTags.length > 0 ? selectedGeoTags[0].id : undefined,
                });
              }}
              style={{
                width: '100%',
                padding: '0.5rem 0.75rem',
                fontSize: '0.875rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                boxSizing: 'border-box',
              }}
            />
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              type="submit"
              data-testid="apply-filters-btn"
              style={{
                padding: '0.5rem 1rem',
                fontSize: '0.875rem',
                fontWeight: 600,
                color: '#ffffff',
                backgroundColor: '#dc2626',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
            >
              Filter
            </button>
            <button
              type="button"
              onClick={handleClearFilters}
              data-testid="clear-filters-btn"
              style={{
                padding: '0.5rem 0.85rem',
                fontSize: '0.875rem',
                fontWeight: 500,
                color: '#4b5563',
                backgroundColor: '#f3f4f6',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
            >
              Clear
            </button>
          </div>
        </div>

        {/* Geographic Selector Filter */}
        <div style={{ marginTop: '1rem', borderTop: '1px solid #f3f4f6', paddingTop: '0.75rem' }}>
          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#374151', marginBottom: '0.25rem' }}>
            Filter by Geography (India / AP / District / Constituency)
          </label>
          <div data-testid="filter-geo">
            <GeoTagSelector
              value={selectedGeoTags}
              onChange={(next) => {
                setSelectedGeoTags(next);
                updateUrlParams({
                  newspaperName,
                  edition,
                  dateFrom,
                  dateTo,
                  geoId: next.length > 0 ? next[0].id : undefined,
                });
              }}
              placeholder="Search district, mandal, or historical alias to filter clippings..."
            />
          </div>
        </div>
      </form>

      {/* Results Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1rem',
        }}
      >
        <span data-testid="total-clippings-count" style={{ fontSize: '0.9rem', color: '#6b7280' }}>
          Found <strong>{total}</strong> published newspaper clippings
        </span>
      </div>

      {/* Error state */}
      {error && (
        <div
          data-testid="error-message"
          style={{
            padding: '1rem',
            backgroundColor: '#fee2e2',
            color: '#991b1b',
            borderRadius: '6px',
            marginBottom: '1.5rem',
          }}
        >
          {error}
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div
          data-testid="loading-indicator"
          style={{
            textAlign: 'center',
            padding: '3rem',
            color: '#6b7280',
            fontSize: '1rem',
          }}
        >
          Loading newspaper clippings...
        </div>
      )}

      {/* Empty State */}
      {!isLoading && clippings.length === 0 && (
        <div
          data-testid="empty-clippings-message"
          style={{
            textAlign: 'center',
            padding: '4rem 2rem',
            backgroundColor: '#f9fafb',
            borderRadius: '8px',
            border: '1px dashed #d1d5db',
            color: '#6b7280',
          }}
        >
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📰</div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#374151', margin: '0 0 0.5rem 0' }}>
            No newspaper clippings found
          </h3>
          <p style={{ margin: 0, fontSize: '0.9rem' }}>
            Try adjusting your search filters or clearing the date and geographic constraints.
          </p>
        </div>
      )}

      {/* Clippings Grid */}
      {!isLoading && clippings.length > 0 && (
        <div
          data-testid="clippings-grid"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
            gap: '1.5rem',
          }}
        >
          {clippings.map((clipping) => (
            <div
              key={clipping.id}
              data-testid={`clipping-card-${clipping.id}`}
              style={{
                backgroundColor: '#ffffff',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                overflow: 'hidden',
                boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              {/* Preview Thumbnail */}
              <div
                style={{
                  height: '180px',
                  backgroundColor: '#f3f4f6',
                  overflow: 'hidden',
                  position: 'relative',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {clipping.preview_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={clipping.preview_url}
                    alt={clipping.headline}
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  />
                ) : (
                  <span style={{ color: '#9ca3af', fontSize: '0.85rem' }}>No preview</span>
                )}
                <span
                  style={{
                    position: 'absolute',
                    top: '8px',
                    left: '8px',
                    backgroundColor: 'rgba(17, 24, 39, 0.85)',
                    color: '#ffffff',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    padding: '0.2rem 0.5rem',
                    borderRadius: '4px',
                  }}
                >
                  {clipping.newspaper_name}
                </span>
              </div>

              {/* Card Body */}
              <div style={{ padding: '1rem', flex: 1, display: 'flex', flexDirection: 'column' }}>
                <h4
                  style={{
                    fontSize: '1rem',
                    fontWeight: 600,
                    color: '#111827',
                    margin: '0 0 0.5rem 0',
                    lineHeight: '1.4',
                  }}
                >
                  {clipping.headline}
                </h4>

                <div
                  style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '0.5rem',
                    fontSize: '0.75rem',
                    color: '#6b7280',
                    marginBottom: '0.75rem',
                  }}
                >
                  <span>📅 {clipping.publication_date}</span>
                  {clipping.edition && <span>📍 {clipping.edition}</span>}
                  {clipping.page_number && <span>📄 Page {clipping.page_number}</span>}
                </div>

                {/* Geo tags */}
                {clipping.geo_tags && clipping.geo_tags.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem', marginBottom: '0.75rem' }}>
                    {clipping.geo_tags.map((geo) => (
                      <span
                        key={geo.id}
                        style={{
                          fontSize: '0.7rem',
                          backgroundColor: '#f0fdf4',
                          color: '#166534',
                          padding: '0.1rem 0.4rem',
                          borderRadius: '4px',
                        }}
                      >
                        {geo.name}
                      </span>
                    ))}
                  </div>
                )}

                {/* OCR snippet */}
                {clipping.extracted_text && (
                  <p
                    style={{
                      fontSize: '0.8rem',
                      color: '#4b5563',
                      lineHeight: '1.4',
                      margin: '0 0 1rem 0',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                      flex: 1,
                    }}
                  >
                    {clipping.extracted_text}
                  </p>
                )}

                <button
                  type="button"
                  data-testid={`select-clipping-${clipping.id}`}
                  onClick={() => setSelectedClipping(clipping)}
                  style={{
                    marginTop: 'auto',
                    width: '100%',
                    padding: '0.5rem',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    color: '#dc2626',
                    backgroundColor: '#fef2f2',
                    border: '1px solid #fecaca',
                    borderRadius: '6px',
                    cursor: 'pointer',
                  }}
                >
                  View Side-by-Side 🔍
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function NewspaperArchivePage() {
  return (
    <AppShell role={UserRole.VIEWER} userEmail="viewer@jsp.internal">
      <Suspense fallback={<div style={{ padding: '2rem' }}>Loading archive...</div>}>
        <NewspaperArchiveContent />
      </Suspense>
    </AppShell>
  );
}
