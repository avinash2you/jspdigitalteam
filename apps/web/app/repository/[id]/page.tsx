'use client';

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { AssetDetailResponse, UserRole } from '@jsp/shared';
import { AppShell } from '@/components/AppShell';
import { AssetDetailView } from '@/components/assets/AssetDetailView';
import { apiFetch } from '@/lib/api-client';

export default function AssetDetailPage() {
  const params = useParams();
  const id = params?.id as string;

  const [asset, setAsset] = useState<AssetDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let isMounted = true;

    async function loadAsset() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await apiFetch<AssetDetailResponse>(`/api/v1/assets/${id}`);
        if (isMounted) {
          setAsset(data);
        }
      } catch (err: unknown) {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : 'Failed to load asset details';
          setError(msg);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadAsset();
    return () => {
      isMounted = false;
    };
  }, [id]);

  return (
    <AppShell role={UserRole.RESEARCHER} userEmail="researcher@jsp.internal">
      {isLoading && (
        <div
          data-testid="asset-loading"
          style={{ padding: '4rem', textAlign: 'center', color: '#6b7280' }}
        >
          Loading asset details...
        </div>
      )}

      {error && (
        <div
          data-testid="asset-error"
          style={{
            maxWidth: '800px',
            margin: '3rem auto',
            padding: '1.5rem',
            backgroundColor: '#fee2e2',
            color: '#991b1b',
            borderRadius: '8px',
          }}
        >
          <h3 style={{ margin: '0 0 0.5rem 0' }}>Error Loading Asset</h3>
          <p style={{ margin: 0 }}>{error}</p>
        </div>
      )}

      {!isLoading && !error && asset && (
        <AssetDetailView asset={asset} userRole={UserRole.RESEARCHER} />
      )}
    </AppShell>
  );
}
