'use client';

import React, { useState, useEffect, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { GeoEntity, SearchPaginationResponse, SearchResultItem, UserRole } from '@jsp/shared';
import { AppShell } from '@/components/AppShell';
import { SearchFiltersSidebar } from '@/components/search/SearchFiltersSidebar';
import { SearchResultCard } from '@/components/search/SearchResultCard';
import { apiFetch } from '@/lib/api-client';

function SearchPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Search input & filter states
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [selectedAssetTypes, setSelectedAssetTypes] = useState<string[]>(
    searchParams.get('asset_types') ? searchParams.get('asset_types')!.split(',') : []
  );
  const [dateFrom, setDateFrom] = useState(searchParams.get('date_from') || '');
  const [dateTo, setDateTo] = useState(searchParams.get('date_to') || '');
  const [department, setDepartment] = useState(searchParams.get('department') || '');
  const [selectedGeoEntities, setSelectedGeoEntities] = useState<GeoEntity[]>([]);

  // Results & UI states
  const [items, setItems] = useState<SearchResultItem[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Sync state to URL search parameters for shareable internal links
  const updateUrlParams = useCallback(
    (params: {
      q?: string;
      assetTypes?: string[];
      dateFrom?: string;
      dateTo?: string;
      department?: string;
      geoIds?: string[];
    }) => {
      const nextParams = new URLSearchParams();
      if (params.q) nextParams.set('q', params.q);
      if (params.assetTypes && params.assetTypes.length > 0) {
        nextParams.set('asset_types', params.assetTypes.join(','));
      }
      if (params.dateFrom) nextParams.set('date_from', params.dateFrom);
      if (params.dateTo) nextParams.set('date_to', params.dateTo);
      if (params.department) nextParams.set('department', params.department);
      if (params.geoIds && params.geoIds.length > 0) {
        nextParams.set('geo_ids', params.geoIds.join(','));
      }

      const queryString = nextParams.toString();
      router.push(queryString ? `/search?${queryString}` : '/search');
    },
    [router]
  );

  // Execute API Search
  const executeSearch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (query.trim()) params.set('q', query.trim());
      selectedAssetTypes.forEach((t) => params.append('asset_types', t));
      if (dateFrom) params.set('date_from', dateFrom);
      if (dateTo) params.set('date_to', dateTo);
      if (department.trim()) params.set('department', department.trim());
      selectedGeoEntities.forEach((g) => params.append('geo_ids', g.id));
      params.set('page_size', '20');

      const data = await apiFetch<SearchPaginationResponse>(`/api/v1/search?${params.toString()}`);
      setItems(data.items || []);
      setTotal(data.total || 0);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Search request failed';
      setError(msg);
      setItems([]);
      setTotal(0);
    } finally {
      setIsLoading(false);
    }
  }, [query, selectedAssetTypes, dateFrom, dateTo, department, selectedGeoEntities]);

  // Sync from URL changes
  useEffect(() => {
    const qParam = searchParams.get('q') || '';
    const typesParam = searchParams.get('asset_types');
    const dfParam = searchParams.get('date_from') || '';
    const dtParam = searchParams.get('date_to') || '';
    const deptParam = searchParams.get('department') || '';

    setQuery(qParam);
    setSelectedAssetTypes(typesParam ? typesParam.split(',') : []);
    setDateFrom(dfParam);
    setDateTo(dtParam);
    setDepartment(deptParam);
  }, [searchParams]);

  // Execute search when filters or search params trigger
  useEffect(() => {
    executeSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAssetTypes, dateFrom, dateTo, department, selectedGeoEntities]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateUrlParams({
      q: query.trim(),
      assetTypes: selectedAssetTypes,
      dateFrom,
      dateTo,
      department: department.trim(),
      geoIds: selectedGeoEntities.map((g) => g.id),
    });
    executeSearch();
  };

  const handleResetFilters = () => {
    setSelectedAssetTypes([]);
    setDateFrom('');
    setDateTo('');
    setDepartment('');
    setSelectedGeoEntities([]);
    updateUrlParams({ q: query.trim() });
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Page Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h1
          data-testid="search-title"
          style={{ fontSize: '1.75rem', fontWeight: 700, color: '#111827', margin: 0 }}
        >
          Multilingual Intelligence Search
        </h1>
        <p style={{ color: '#4b5563', fontSize: '0.95rem', marginTop: '0.25rem' }}>
          Query across English, Telugu Unicode, Tenglish keywords, and exact Government Order (GO)
          numbers with hybrid semantic ranking.
        </p>
      </div>

      {/* Main Search Bar Form */}
      <form
        onSubmit={handleSearchSubmit}
        data-testid="search-bar-form"
        style={{
          display: 'flex',
          gap: '0.75rem',
          marginBottom: '2rem',
        }}
      >
        <input
          type="text"
          data-testid="search-input"
          placeholder="Search in Telugu (రైతు భరోసా), English, Tenglish, or enter GO number (e.g. GO-MS-104)..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{
            flex: 1,
            padding: '0.85rem 1.25rem',
            fontSize: '1rem',
            border: '1px solid #d1d5db',
            borderRadius: '8px',
            boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)',
            outline: 'none',
          }}
        />

        <button
          type="submit"
          data-testid="search-submit-btn"
          style={{
            padding: '0.85rem 1.75rem',
            fontSize: '1rem',
            fontWeight: 600,
            color: '#ffffff',
            backgroundColor: '#dc2626',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            boxShadow: '0 1px 2px rgba(0, 0, 0, 0.1)',
          }}
        >
          Search 🔍
        </button>
      </form>

      {/* Main Content Layout: Sidebar + Results */}
      <div
        style={{
          display: 'flex',
          gap: '2rem',
          alignItems: 'flex-start',
        }}
      >
        {/* Left: Filter Sidebar */}
        <SearchFiltersSidebar
          selectedAssetTypes={selectedAssetTypes}
          onAssetTypesChange={(types) => {
            setSelectedAssetTypes(types);
            updateUrlParams({
              q: query.trim(),
              assetTypes: types,
              dateFrom,
              dateTo,
              department,
              geoIds: selectedGeoEntities.map((g) => g.id),
            });
          }}
          dateFrom={dateFrom}
          onDateFromChange={(df) => {
            setDateFrom(df);
            updateUrlParams({
              q: query.trim(),
              assetTypes: selectedAssetTypes,
              dateFrom: df,
              dateTo,
              department,
              geoIds: selectedGeoEntities.map((g) => g.id),
            });
          }}
          dateTo={dateTo}
          onDateToChange={(dt) => {
            setDateTo(dt);
            updateUrlParams({
              q: query.trim(),
              assetTypes: selectedAssetTypes,
              dateFrom,
              dateTo: dt,
              department,
              geoIds: selectedGeoEntities.map((g) => g.id),
            });
          }}
          department={department}
          onDepartmentChange={(dept) => {
            setDepartment(dept);
            updateUrlParams({
              q: query.trim(),
              assetTypes: selectedAssetTypes,
              dateFrom,
              dateTo,
              department: dept,
              geoIds: selectedGeoEntities.map((g) => g.id),
            });
          }}
          selectedGeoEntities={selectedGeoEntities}
          onGeoEntitiesChange={(geos) => {
            setSelectedGeoEntities(geos);
            updateUrlParams({
              q: query.trim(),
              assetTypes: selectedAssetTypes,
              dateFrom,
              dateTo,
              department,
              geoIds: geos.map((g) => g.id),
            });
          }}
          onResetFilters={handleResetFilters}
        />

        {/* Right: Results Area */}
        <main style={{ flex: 1, minWidth: 0 }}>
          {/* Results Count Header */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '1rem',
            }}
          >
            <span
              data-testid="search-results-count"
              style={{ fontSize: '0.9rem', color: '#4b5563' }}
            >
              Found <strong>{total}</strong> matching digital intelligence assets
            </span>
          </div>

          {/* Error Banner */}
          {error && (
            <div
              data-testid="search-error"
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

          {/* Loading Skeletons */}
          {isLoading && (
            <div data-testid="search-loading-skeleton" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {[1, 2, 3].map((n) => (
                <div
                  key={n}
                  style={{
                    height: '140px',
                    backgroundColor: '#f3f4f6',
                    borderRadius: '8px',
                    animation: 'pulse 1.5s infinite',
                  }}
                />
              ))}
            </div>
          )}

          {/* Empty State */}
          {!isLoading && items.length === 0 && (
            <div
              data-testid="search-empty-state"
              style={{
                textAlign: 'center',
                padding: '4rem 2rem',
                backgroundColor: '#f9fafb',
                borderRadius: '8px',
                border: '1px dashed #d1d5db',
                color: '#6b7280',
              }}
            >
              <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>🔎</div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 600, color: '#374151', margin: '0 0 0.5rem 0' }}>
                No assets matched your search
              </h3>
              <p style={{ margin: 0, fontSize: '0.9rem' }}>
                Try broadening your keywords, adjusting transliterated Telugu terms, or clearing active
                filters in the sidebar.
              </p>
            </div>
          )}

          {/* Search Result Cards List */}
          {!isLoading && items.length > 0 && (
            <div data-testid="search-results-list">
              {items.map((item) => (
                <SearchResultCard key={item.id} item={item} />
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <AppShell role={UserRole.VIEWER} userEmail="viewer@jsp.internal">
      <Suspense fallback={<div style={{ padding: '2rem' }}>Loading search...</div>}>
        <SearchPageContent />
      </Suspense>
    </AppShell>
  );
}
