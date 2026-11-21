'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { AssetType, GeoEntity, validateDynamicMetadata } from '@jsp/shared';
import { apiFetch } from '@/lib/api-client';
import { DynamicMetadataFields } from '@/components/upload/DynamicMetadataFields';
import { GeoTagSelector } from '@/components/geography/GeoTagSelector';

export interface ExtractionReviewPanelProps {
  assetId: string;
}

interface AssetDetails {
  id: string;
  title: string;
  asset_type: AssetType;
  primary_language: string;
  is_public_record: boolean;
  status: string;
  extracted_text: string | null;
  english_summary: string | null;
  tenglish_keywords: string[];
  dynamic_metadata: Record<string, unknown>;
  geo_entities: GeoEntity[];
}

interface ExtractionResponse {
  asset_id: string;
  extracted_text: string;
  english_summary: string | null;
  tenglish_keywords: string[];
  suggested_metadata: Record<string, unknown>;
  suggested_geo_names: string[];
  ai_skipped: boolean;
  ai_notice: string | null;
  status: string;
}

export function ExtractionReviewPanel({ assetId }: ExtractionReviewPanelProps) {
  const router = useRouter();

  const [asset, setAsset] = useState<AssetDetails | null>(null);
  const [extractedText, setExtractedText] = useState('');
  const [englishSummary, setEnglishSummary] = useState('');
  const [tenglishKeywords, setTenglishKeywords] = useState<string[]>([]);
  const [dynamicMetadata, setDynamicMetadata] = useState<Record<string, unknown>>({});
  const [geoEntities, setGeoEntities] = useState<GeoEntity[]>([]);

  const [aiSkipped, setAiSkipped] = useState(false);
  const [aiNotice, setAiNotice] = useState<string | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [isExtracting, setIsExtracting] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [publishSuccess, setPublishSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Trigger OCR & AI extraction via API
  const runExtraction = useCallback(async () => {
    setIsExtracting(true);
    setError(null);
    try {
      const res = await apiFetch<ExtractionResponse>(`/api/v1/assets/${assetId}/extract`, {
        method: 'POST',
      });
      setExtractedText(res.extracted_text || '');
      setEnglishSummary(res.english_summary || '');
      setTenglishKeywords(res.tenglish_keywords || []);
      setAiSkipped(res.ai_skipped);
      setAiNotice(res.ai_notice);

      setDynamicMetadata((prev) => ({
        ...res.suggested_metadata,
        ...prev,
      }));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Extraction failed';
      setError(msg);
    } finally {
      setIsExtracting(false);
    }
  }, [assetId]);

  // Load asset on mount
  useEffect(() => {
    let isMounted = true;
    async function loadAsset() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await apiFetch<AssetDetails>(`/api/v1/assets/${assetId}`);
        if (!isMounted) return;
        setAsset(data);
        setExtractedText(data.extracted_text || '');
        setEnglishSummary(data.english_summary || '');
        setTenglishKeywords(data.tenglish_keywords || []);
        setDynamicMetadata(data.dynamic_metadata || {});
        setGeoEntities(data.geo_entities || []);

        if (!data.is_public_record) {
          setAiSkipped(true);
          setAiNotice(
            'AI extraction skipped for non-public confidential record to protect data privacy on free-tier.'
          );
        }

        // If asset is brand new draft with no extraction yet, trigger automatically
        if (data.status === 'draft' && !data.extracted_text) {
          await runExtraction();
        }
      } catch (err: unknown) {
        if (!isMounted) return;
        const msg = err instanceof Error ? err.message : 'Failed to load asset details';
        setError(msg);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    loadAsset();
    return () => {
      isMounted = false;
    };
  }, [assetId, runExtraction]);

  const handleMetadataChange = (field: string, value: unknown) => {
    setDynamicMetadata((prev) => ({
      ...prev,
      [field]: value,
    }));
    setValidationErrors((prev) => {
      const copy = { ...prev };
      delete copy[field];
      return copy;
    });
  };

  const handlePublish = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!asset) return;

    setError(null);
    setValidationErrors({});

    if (!extractedText.trim()) {
      setValidationErrors({ extractedText: 'Extracted text is required before publishing' });
      return;
    }

    // Validate metadata against schema
    const validation = validateDynamicMetadata(asset.asset_type, dynamicMetadata);
    if (!validation.success) {
      setValidationErrors(validation.errors);
      return;
    }

    setIsPublishing(true);
    try {
      await apiFetch(`/api/v1/assets/${assetId}/publish`, {
        method: 'POST',
        body: JSON.stringify({
          extracted_text: extractedText.trim(),
          english_summary: englishSummary.trim() || null,
          tenglish_keywords: tenglishKeywords,
          dynamic_metadata: dynamicMetadata,
          geo_entity_ids: geoEntities.map((g) => g.id),
        }),
      });

      setPublishSuccess(true);
      setTimeout(() => {
        router.push(`/repository/${assetId}`);
      }, 1000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Publishing failed';
      setError(msg);
    } finally {
      setIsPublishing(false);
    }
  };

  if (isLoading) {
    return (
      <div style={{ padding: '3rem 1rem', textAlign: 'center', color: '#6b7280' }} data-testid="loading-indicator">
        Loading asset and extraction pipeline...
      </div>
    );
  }

  if (error && !asset) {
    return (
      <div style={{ maxWidth: '800px', margin: '2rem auto', padding: '1.5rem', backgroundColor: '#fef2f2', border: '1px solid #ef4444', borderRadius: '6px', color: '#991b1b' }}>
        <h3 style={{ margin: '0 0 0.5rem 0' }}>Error Loading Asset</h3>
        <p style={{ margin: 0 }}>{error}</p>
        <Link href="/repository" style={{ display: 'inline-block', marginTop: '1rem', color: '#b91c1c', textDecoration: 'underline' }}>
          Back to Digital Repository
        </Link>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem 1rem' }}>
      {/* Header bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0, color: '#111827' }}>
              Review & Approve Extraction
            </h1>
            <span
              style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                padding: '0.2rem 0.5rem',
                borderRadius: '4px',
                backgroundColor: '#e5e7eb',
                color: '#374151',
              }}
            >
              {asset?.asset_type}
            </span>
            <span
              style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                padding: '0.2rem 0.5rem',
                borderRadius: '4px',
                backgroundColor: '#fef3c7',
                color: '#92400e',
              }}
            >
              {asset?.status}
            </span>
          </div>
          <p style={{ margin: 0, fontSize: '0.875rem', color: '#4b5563' }}>
            Asset: <strong>{asset?.title}</strong> (ID: {assetId})
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            type="button"
            onClick={runExtraction}
            disabled={isExtracting}
            data-testid="btn-re-extract"
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#f3f4f6',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              fontSize: '0.875rem',
              fontWeight: 500,
              cursor: isExtracting ? 'not-allowed' : 'pointer',
            }}
          >
            {isExtracting ? 'Extracting...' : 'Re-run Extraction'}
          </button>
        </div>
      </div>

      {/* Non-public record banner */}
      {aiSkipped && (
        <div
          role="alert"
          data-testid="non-public-ai-skipped-banner"
          style={{
            backgroundColor: '#eff6ff',
            border: '1px solid #3b82f6',
            borderRadius: '6px',
            padding: '1rem',
            marginBottom: '1.5rem',
            color: '#1e40af',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>
            <span>🔒</span>
            <span>Confidential Record — Free-Tier AI Extraction Skipped</span>
          </div>
          <p style={{ margin: 0, fontSize: '0.875rem', color: '#1e3a8a' }}>
            {aiNotice ||
              'To protect confidential party documents from third-party model training, automated AI metadata pre-fill was skipped. OCR text was extracted below. You can manually edit the summary, keywords, and metadata fields before publishing.'}
          </p>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div
          role="alert"
          data-testid="review-error-banner"
          style={{
            backgroundColor: '#fef2f2',
            border: '1px solid #ef4444',
            borderRadius: '6px',
            padding: '1rem',
            marginBottom: '1.5rem',
            color: '#991b1b',
          }}
        >
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Success banner */}
      {publishSuccess && (
        <div
          role="status"
          data-testid="publish-success-banner"
          style={{
            backgroundColor: '#ecfdf5',
            border: '1px solid #10b981',
            borderRadius: '6px',
            padding: '1rem',
            marginBottom: '1.5rem',
            color: '#065f46',
          }}
        >
          <strong>Published Successfully!</strong> Document chunks generated. Redirecting to Asset Detail view...
        </div>
      )}

      {/* Main Review Form */}
      <form onSubmit={handlePublish} noValidate>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: '1.5rem' }}>
          {/* Left Column: Text & Content Intelligence */}
          <div
            style={{
              backgroundColor: '#fff',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              padding: '1.25rem',
            }}
          >
            <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem', color: '#111827' }}>
              Extracted Content & Intelligence
            </h2>

            {/* Extracted OCR text */}
            <div style={{ marginBottom: '1.25rem' }}>
              <label
                htmlFor="extracted-text-area"
                style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.25rem' }}
              >
                Extracted Text (OCR) <span style={{ color: '#dc2626' }}>*</span>
              </label>
              <textarea
                id="extracted-text-area"
                data-testid="textarea-extracted-text"
                rows={12}
                value={extractedText}
                onChange={(e) => setExtractedText(e.target.value)}
                placeholder="OCR text extracted from document..."
                style={{
                  width: '100%',
                  padding: '0.625rem 0.75rem',
                  borderRadius: '4px',
                  border: validationErrors.extractedText ? '1px solid #dc2626' : '1px solid #d1d5db',
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                  lineHeight: '1.4',
                }}
              />
              {validationErrors.extractedText && (
                <p style={{ color: '#dc2626', fontSize: '0.75rem', marginTop: '0.25rem', marginBottom: 0 }}>
                  {validationErrors.extractedText}
                </p>
              )}
            </div>

            {/* English Executive Summary */}
            <div style={{ marginBottom: '1.25rem' }}>
              <label
                htmlFor="english-summary-area"
                style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.25rem' }}
              >
                English Executive Summary
              </label>
              <textarea
                id="english-summary-area"
                data-testid="textarea-english-summary"
                rows={4}
                value={englishSummary}
                onChange={(e) => setEnglishSummary(e.target.value)}
                placeholder="2-4 sentence executive summary in English..."
                style={{
                  width: '100%',
                  padding: '0.625rem 0.75rem',
                  borderRadius: '4px',
                  border: '1px solid #d1d5db',
                  fontSize: '0.875rem',
                }}
              />
            </div>

            {/* Tenglish search keywords */}
            <div style={{ marginBottom: '1.25rem' }}>
              <label
                htmlFor="tenglish-keywords-input"
                style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.25rem' }}
              >
                Tenglish Search Keywords (Phonetic Telugu in Latin script)
              </label>
              <input
                id="tenglish-keywords-input"
                data-testid="input-tenglish-keywords"
                type="text"
                value={tenglishKeywords.join(', ')}
                onChange={(e) => {
                  const items = e.target.value
                    .split(',')
                    .map((s) => s.trim())
                    .filter((s) => s.length > 0);
                  setTenglishKeywords(items);
                }}
                placeholder="e.g. rythu, polavaram, panta bima, varahi yatra"
                style={{
                  width: '100%',
                  padding: '0.625rem 0.75rem',
                  borderRadius: '4px',
                  border: '1px solid #d1d5db',
                  fontSize: '0.875rem',
                }}
              />
              <span style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem', display: 'block' }}>
                Separate keywords with commas. Used for conversational and phonetic search.
              </span>
            </div>
          </div>

          {/* Right Column: Pre-filled Dynamic Metadata & Geo Tags */}
          <div
            style={{
              backgroundColor: '#fff',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              padding: '1.25rem',
            }}
          >
            <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem', color: '#111827' }}>
              Structured Metadata Verification
            </h2>

            {/* Dynamic fields */}
            {asset && (
              <DynamicMetadataFields
                assetType={asset.asset_type}
                values={dynamicMetadata}
                errors={validationErrors}
                onChange={handleMetadataChange}
              />
            )}

            {/* Geographic hierarchy tags */}
            <div style={{ marginTop: '1.5rem' }}>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.5rem' }}>
                Geographic Hierarchy Tags
              </label>
              <GeoTagSelector
                value={geoEntities}
                onChange={setGeoEntities}
                placeholder="Verify or add location tags..."
              />
            </div>
          </div>
        </div>

        {/* Bottom submit action bar */}
        <div
          style={{
            marginTop: '2rem',
            paddingTop: '1.5rem',
            borderTop: '1px solid #e5e7eb',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '1rem',
          }}
        >
          <Link
            href={`/repository/${assetId}`}
            style={{
              padding: '0.75rem 1.25rem',
              backgroundColor: '#fff',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              color: '#374151',
              fontWeight: 500,
              fontSize: '0.875rem',
              textDecoration: 'none',
              display: 'inline-flex',
              alignItems: 'center',
            }}
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={isPublishing}
            data-testid="btn-approve-publish"
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: isPublishing ? '#9ca3af' : '#059669',
              color: '#fff',
              fontWeight: 600,
              fontSize: '0.875rem',
              borderRadius: '6px',
              border: 'none',
              cursor: isPublishing ? 'not-allowed' : 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            {isPublishing ? 'Publishing & Chunking...' : 'Approve & Publish Asset'}
          </button>
        </div>
      </form>
    </div>
  );
}
