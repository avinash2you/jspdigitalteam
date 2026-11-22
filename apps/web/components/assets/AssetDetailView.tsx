'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  AssetDetailResponse,
  DownloadUrlResponse,
  UserRole,
} from '@jsp/shared';
import { apiFetch } from '@/lib/api-client';

export interface AssetDetailViewProps {
  asset: AssetDetailResponse;
  userRole?: UserRole;
  canExport?: boolean;
  onRefresh?: () => void;
}

export function AssetDetailView({
  asset,
  userRole,
  canExport: canExportProp,
}: AssetDetailViewProps) {
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  // Check if role has export permission (SUPER_ADMIN, ADMIN, RESEARCHER, REVIEWER, CONTRIBUTOR, VIEWER have export)
  const canExport =
    canExportProp !== undefined
      ? canExportProp
      : userRole
      ? [
          UserRole.SUPER_ADMIN,
          UserRole.ADMIN,
          UserRole.RESEARCHER,
          UserRole.REVIEWER,
          UserRole.CONTRIBUTOR,
          UserRole.VIEWER,
        ].includes(userRole)
      : false;

  // Fetch short-lived presigned download/preview URL
  useEffect(() => {
    let isMounted = true;
    async function loadPreview() {
      try {
        const res = await apiFetch<DownloadUrlResponse>(
          `/api/v1/assets/${asset.id}/download-url`
        );
        if (isMounted && res.download_url) {
          setPreviewUrl(res.download_url);
        }
      } catch {
        // Preview fallback if presigned generation is restricted
      }
    }
    loadPreview();
    return () => {
      isMounted = false;
    };
  }, [asset.id]);

  const handleDownload = async () => {
    setDownloading(true);
    setDownloadError(null);
    try {
      // Always request a fresh short-lived presigned URL; never use a static URL
      const data = await apiFetch<DownloadUrlResponse>(
        `/api/v1/assets/${asset.id}/download-url`
      );
      if (data && data.download_url) {
        window.open(data.download_url, '_blank', 'noopener,noreferrer');
      } else {
        throw new Error('Download URL could not be generated');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to generate download URL';
      setDownloadError(msg);
    } finally {
      setDownloading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const isImageOrClipping =
    asset.mime_type.startsWith('image/') || asset.asset_type === 'newspaper_clipping';

  return (
    <div
      data-testid="asset-detail-container"
      style={{
        maxWidth: '1200px',
        margin: '0 auto',
        padding: '2rem 1.5rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '2rem',
      }}
    >
      {/* Top Breadcrumb & Actions Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          borderBottom: '1px solid #e5e7eb',
          paddingBottom: '1rem',
        }}
      >
        <div>
          <Link
            href="/repository"
            style={{ color: '#6b7280', textDecoration: 'none', fontSize: '0.85rem' }}
          >
            ← Back to Repository
          </Link>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '0.5rem' }}>
            <span
              data-testid="asset-type"
              style={{
                backgroundColor: '#fee2e2',
                color: '#991b1b',
                fontSize: '0.75rem',
                fontWeight: 600,
                padding: '0.2rem 0.6rem',
                borderRadius: '4px',
                textTransform: 'uppercase',
              }}
            >
              {asset.asset_type}
            </span>
            <span
              data-testid="asset-status"
              style={{
                backgroundColor: asset.status === 'published' ? '#dcfce7' : '#fef3c7',
                color: asset.status === 'published' ? '#166534' : '#92400e',
                fontSize: '0.75rem',
                fontWeight: 600,
                padding: '0.2rem 0.6rem',
                borderRadius: '4px',
                textTransform: 'uppercase',
              }}
            >
              {asset.status}
            </span>
            <span
              data-testid="asset-verification-status"
              style={{
                backgroundColor: asset.verification_status === 'verified' ? '#e0e7ff' : '#f3f4f6',
                color: asset.verification_status === 'verified' ? '#3730a3' : '#4b5563',
                fontSize: '0.75rem',
                fontWeight: 600,
                padding: '0.2rem 0.6rem',
                borderRadius: '4px',
                textTransform: 'uppercase',
              }}
            >
              {asset.verification_status}
            </span>
          </div>
        </div>

        {/* Export / Download Button (hidden if role lacks export permission) */}
        {canExport && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.25rem' }}>
            <button
              type="button"
              onClick={handleDownload}
              disabled={downloading}
              data-testid="download-btn"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.65rem 1.25rem',
                fontSize: '0.9rem',
                fontWeight: 600,
                color: '#ffffff',
                backgroundColor: '#dc2626',
                border: 'none',
                borderRadius: '6px',
                cursor: downloading ? 'not-allowed' : 'pointer',
                boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)',
              }}
            >
              {downloading ? 'Generating Presigned URL...' : 'Download Original File 📥'}
            </button>
            <span style={{ fontSize: '0.7rem', color: '#6b7280' }}>
              Private R2 presigned download (expires in 5 min)
            </span>
            {downloadError && (
              <span data-testid="download-error" style={{ fontSize: '0.75rem', color: '#dc2626' }}>
                {downloadError}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Main Asset Header */}
      <div>
        <h1
          data-testid="asset-title"
          style={{ fontSize: '1.85rem', fontWeight: 700, color: '#111827', margin: 0, lineHeight: 1.3 }}
        >
          {asset.title}
        </h1>

        {asset.go_number && (
          <div style={{ marginTop: '0.5rem' }}>
            <span
              data-testid="asset-go-number"
              style={{
                backgroundColor: '#f1f5f9',
                color: '#0f172a',
                fontSize: '0.85rem',
                fontWeight: 700,
                padding: '0.25rem 0.6rem',
                borderRadius: '4px',
                border: '1px solid #cbd5e1',
                display: 'inline-block',
              }}
            >
              Government Order: {asset.go_number}
            </span>
          </div>
        )}
      </div>

      {/* Source & Attribution Meta Bar */}
      <div
        data-testid="uploader-attribution"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          backgroundColor: '#f9fafb',
          border: '1px solid #e5e7eb',
          borderRadius: '8px',
          padding: '1rem 1.25rem',
        }}
      >
        <div>
          <span style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block' }}>
            Uploaded by Contributor
          </span>
          <span data-testid="uploader-name" style={{ fontSize: '0.95rem', fontWeight: 600, color: '#111827' }}>
            {asset.uploader?.full_name || asset.uploader?.email || 'Unknown User'}
          </span>
          {asset.uploader?.role && (
            <span
              data-testid="uploader-role"
              style={{
                marginLeft: '0.5rem',
                fontSize: '0.75rem',
                backgroundColor: '#e5e7eb',
                color: '#374151',
                padding: '0.1rem 0.4rem',
                borderRadius: '4px',
              }}
            >
              {asset.uploader.role}
            </span>
          )}
        </div>

        <div>
          <span style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block' }}>
            Ingestion Timestamp
          </span>
          <span data-testid="upload-timestamp" style={{ fontSize: '0.9rem', color: '#374151' }}>
            {new Date(asset.created_at).toLocaleString()}
          </span>
        </div>

        <div>
          <span style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block' }}>
            Copyright / Licensing
          </span>
          <span
            data-testid="asset-copyright"
            style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              backgroundColor: '#fee2e2',
              color: '#991b1b',
              padding: '0.15rem 0.45rem',
              borderRadius: '4px',
              textTransform: 'uppercase',
            }}
          >
            {asset.copyright_flag}
          </span>
        </div>

        <div>
          <span style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block' }}>
            Public Record
          </span>
          <span
            data-testid="asset-public-record"
            style={{ fontSize: '0.85rem', fontWeight: 600, color: asset.is_public_record ? '#166534' : '#991b1b' }}
          >
            {asset.is_public_record ? '✓ Public Domain' : '🔒 Confidential / Non-Public'}
          </span>
        </div>
      </div>

      {/* Multi-Tier Geographic Chips */}
      {asset.geo_entities && asset.geo_entities.length > 0 && (
        <div>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#374151', margin: '0 0 0.5rem 0' }}>
            Geographic Coverage
          </h3>
          <div
            data-testid="asset-geo-entities"
            style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}
          >
            {asset.geo_entities.map((geo) => (
              <span
                key={geo.id}
                data-testid={`geo-chip-${geo.id}`}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  fontSize: '0.85rem',
                  backgroundColor: '#e0f2fe',
                  color: '#0369a1',
                  border: '1px solid #bae6fd',
                  padding: '0.25rem 0.65rem',
                  borderRadius: '9999px',
                }}
              >
                <span
                  style={{
                    fontSize: '0.7rem',
                    textTransform: 'uppercase',
                    backgroundColor: '#0284c7',
                    color: '#ffffff',
                    padding: '0.1rem 0.35rem',
                    borderRadius: '4px',
                    fontWeight: 600,
                  }}
                >
                  {geo.tier}
                </span>
                <strong>{geo.name}</strong>
                {geo.telugu_name && <span>({geo.telugu_name})</span>}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* File Preview & Integrity Card */}
      <div
        style={{
          border: '1px solid #e5e7eb',
          borderRadius: '8px',
          overflow: 'hidden',
          backgroundColor: '#ffffff',
        }}
      >
        <div
          style={{
            padding: '0.75rem 1.25rem',
            backgroundColor: '#f9fafb',
            borderBottom: '1px solid #e5e7eb',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span style={{ fontSize: '0.9rem', fontWeight: 600, color: '#374151' }}>
            Source File & Cryptographic Integrity
          </span>
          <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>
            {asset.mime_type} • {formatFileSize(asset.file_size_bytes)}
          </span>
        </div>

        <div style={{ padding: '1.25rem' }}>
          <div style={{ marginBottom: '1rem' }}>
            <span style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block' }}>
              SHA256 File Checksum (Immutable)
            </span>
            <code
              data-testid="asset-sha256"
              style={{
                fontSize: '0.8rem',
                backgroundColor: '#f3f4f6',
                padding: '0.2rem 0.4rem',
                borderRadius: '4px',
                wordBreak: 'break-all',
              }}
            >
              {asset.file_sha256}
            </code>
          </div>

          {/* Presigned Media Preview */}
          {previewUrl && isImageOrClipping && (
            <div
              data-testid="preview-container"
              style={{
                marginTop: '1rem',
                textAlign: 'center',
                backgroundColor: '#475569',
                padding: '1.5rem',
                borderRadius: '6px',
              }}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={previewUrl}
                alt={asset.title}
                data-testid="asset-preview-image"
                style={{
                  maxWidth: '100%',
                  maxHeight: '480px',
                  borderRadius: '4px',
                  boxShadow: '0 4px 6px rgba(0, 0, 0, 0.2)',
                  objectFit: 'contain',
                }}
              />
            </div>
          )}
        </div>
      </div>

      {/* Clickable Document Relationships (Amends / Supersedes / Clarifies / Related) */}
      <div
        data-testid="asset-relationships"
        style={{
          border: '1px solid #e5e7eb',
          borderRadius: '8px',
          padding: '1.25rem',
          backgroundColor: '#ffffff',
        }}
      >
        <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#111827', margin: '0 0 0.75rem 0' }}>
          Document Relationships & Lineage
        </h3>

        {(!asset.relationships || asset.relationships.length === 0) ? (
          <p style={{ margin: 0, fontSize: '0.9rem', color: '#6b7280' }}>
            No related, amending, or superseding documents linked to this asset.
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {asset.relationships.map((rel) => {
              const relColors: Record<string, { bg: string; text: string }> = {
                amends: { bg: '#dbeafe', text: '#1d4ed8' },
                supersedes: { bg: '#fee2e2', text: '#b91c1c' },
                clarifies: { bg: '#fef3c7', text: '#b45309' },
                related: { bg: '#f3f4f6', text: '#374151' },
              };
              const style = relColors[rel.relation_type] || relColors.related;

              return (
                <div
                  key={rel.id}
                  data-testid={`rel-item-${rel.id}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    padding: '0.5rem 0.75rem',
                    backgroundColor: '#f9fafb',
                    borderRadius: '6px',
                    border: '1px solid #f3f4f6',
                  }}
                >
                  <span
                    style={{
                      backgroundColor: style.bg,
                      color: style.text,
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      padding: '0.15rem 0.5rem',
                      borderRadius: '4px',
                      textTransform: 'uppercase',
                    }}
                  >
                    {rel.relation_type} ({rel.direction})
                  </span>

                  <Link
                    href={`/repository/${rel.related_asset_id}`}
                    data-testid={`rel-link-${rel.id}`}
                    style={{
                      fontSize: '0.9rem',
                      fontWeight: 600,
                      color: '#2563eb',
                      textDecoration: 'none',
                    }}
                  >
                    {rel.related_asset_title}
                  </Link>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Dynamic Metadata Section */}
      {asset.dynamic_metadata && Object.keys(asset.dynamic_metadata).length > 0 && (
        <div
          data-testid="dynamic-metadata-section"
          style={{
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            padding: '1.25rem',
            backgroundColor: '#ffffff',
          }}
        >
          <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#111827', margin: '0 0 0.75rem 0' }}>
            Dynamic Metadata ({asset.asset_type})
          </h3>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '1rem',
            }}
          >
            {Object.entries(asset.dynamic_metadata).map(([key, val]) => (
              <div
                key={key}
                style={{
                  backgroundColor: '#f9fafb',
                  padding: '0.75rem',
                  borderRadius: '6px',
                  border: '1px solid #f3f4f6',
                }}
              >
                <span
                  style={{
                    fontSize: '0.75rem',
                    color: '#6b7280',
                    display: 'block',
                    textTransform: 'capitalize',
                  }}
                >
                  {key.replace(/_/g, ' ')}
                </span>
                <span
                  data-testid={`meta-val-${key}`}
                  style={{ fontSize: '0.9rem', fontWeight: 600, color: '#111827' }}
                >
                  {String(val)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* OCR & Intelligence Text Content */}
      <div
        style={{
          border: '1px solid #e5e7eb',
          borderRadius: '8px',
          padding: '1.25rem',
          backgroundColor: '#ffffff',
        }}
      >
        <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#111827', margin: '0 0 0.75rem 0' }}>
          Extracted OCR Text & Intelligence
        </h3>

        {asset.english_summary && (
          <div style={{ marginBottom: '1.25rem' }}>
            <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: '#4b5563', margin: '0 0 0.35rem 0' }}>
              English Summary
            </h4>
            <p
              data-testid="english-summary"
              style={{
                fontSize: '0.9rem',
                lineHeight: 1.6,
                color: '#1f2937',
                margin: 0,
                backgroundColor: '#f9fafb',
                padding: '0.75rem',
                borderRadius: '6px',
              }}
            >
              {asset.english_summary}
            </p>
          </div>
        )}

        <div>
          <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: '#4b5563', margin: '0 0 0.35rem 0' }}>
            Raw OCR Text (Telugu / English)
          </h4>
          <div
            data-testid="extracted-text"
            style={{
              backgroundColor: '#f9fafb',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              padding: '1rem',
              fontSize: '0.9rem',
              lineHeight: 1.6,
              color: '#1f2937',
              whiteSpace: 'pre-wrap',
              maxHeight: '400px',
              overflowY: 'auto',
            }}
          >
            {asset.extracted_text || 'No extracted OCR text available.'}
          </div>
        </div>
      </div>
    </div>
  );
}
