'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { AssetType, GeoEntity, validateDynamicMetadata } from '@jsp/shared';
import { apiFetch } from '@/lib/api-client';
import { DynamicMetadataFields } from '@/components/upload/DynamicMetadataFields';
import { DuplicateWarningBanner, DuplicateMatch } from '@/components/upload/DuplicateWarningBanner';
import { GeoTagSelector } from '@/components/geography/GeoTagSelector';

export async function computeFileSha256(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  if (typeof crypto !== 'undefined' && crypto.subtle) {
    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
  }
  return '';
}

interface PresignResponse {
  object_key: string;
  upload_url: string;
  expires_in: number;
}

interface CheckDuplicateResponse {
  is_duplicate: boolean;
  matches: DuplicateMatch[];
}

interface AssetCreateResponse {
  id: string;
  title: string;
}

const ASSET_TYPE_OPTIONS = [
  { value: AssetType.GOVERNMENT_DOCUMENT, label: 'Government Document (GO)' },
  { value: AssetType.NEWSPAPER_CLIPPING, label: 'Newspaper Clipping' },
  { value: AssetType.ONLINE_NEWS_SOCIAL, label: 'Online News & Social Archive' },
  { value: AssetType.VIDEO_AUDIO, label: 'Video & Audio' },
  { value: AssetType.IMAGE_INFOGRAPHIC, label: 'Image & Infographic' },
  { value: AssetType.RESEARCH_MATERIAL, label: 'Research Material' },
];

export default function UploadPage() {
  const [assetType, setAssetType] = useState<AssetType>(AssetType.GOVERNMENT_DOCUMENT);
  const [title, setTitle] = useState('');
  const [primaryLanguage, setPrimaryLanguage] = useState('telugu');
  const [sourceName, setSourceName] = useState('');
  const [copyrightFlag, setCopyrightFlag] = useState('public_domain');
  const [isPublicRecord, setIsPublicRecord] = useState(false);

  const [file, setFile] = useState<File | null>(null);
  const [fileSha256, setFileSha256] = useState('');
  const [geoEntities, setGeoEntities] = useState<GeoEntity[]>([]);
  const [dynamicMetadata, setDynamicMetadata] = useState<Record<string, unknown>>({
    state: 'Andhra Pradesh',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [duplicateMatches, setDuplicateMatches] = useState<DuplicateMatch[]>([]);
  const [isCheckingDuplicate, setIsCheckingDuplicate] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState<AssetCreateResponse | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Handle switching asset type
  const handleAssetTypeChange = (newType: AssetType) => {
    setAssetType(newType);
    setErrors({});
    if (newType === AssetType.GOVERNMENT_DOCUMENT) {
      setDynamicMetadata({ state: 'Andhra Pradesh' });
    } else {
      setDynamicMetadata({});
    }
  };

  // Perform duplicate check
  const checkDuplicates = async (params: {
    file_sha256?: string;
    go_number?: string;
    source_url?: string;
  }) => {
    if (!params.file_sha256 && !params.go_number && !params.source_url) return;
    setIsCheckingDuplicate(true);
    try {
      const res = await apiFetch<CheckDuplicateResponse>('/api/v1/uploads/check-duplicate', {
        method: 'POST',
        body: JSON.stringify(params),
      });
      if (res && res.matches && res.matches.length > 0) {
        setDuplicateMatches((prev) => {
          const existingIds = new Set(prev.map((m) => m.id));
          const newMatches = res.matches.filter((m) => !existingIds.has(m.id));
          return [...prev, ...newMatches];
        });
      }
    } catch {
      // Ignore background duplicate check failure
    } finally {
      setIsCheckingDuplicate(false);
    }
  };

  // Handle file selection & compute SHA-256
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) {
      setFile(null);
      setFileSha256('');
      return;
    }
    setFile(selectedFile);
    if (!title) {
      setTitle(selectedFile.name.replace(/\.[^/.]+$/, ''));
    }
    setErrors((prev) => {
      const copy = { ...prev };
      delete copy.file;
      return copy;
    });

    try {
      const sha = await computeFileSha256(selectedFile);
      setFileSha256(sha);
      if (sha) {
        await checkDuplicates({ file_sha256: sha });
      }
    } catch (err) {
      console.error('Failed computing SHA-256:', err);
    }
  };

  // Handle blur for GO number and URL deduplication
  const handleMetadataBlur = (field: string, value: unknown) => {
    if (field === 'go_number' && typeof value === 'string' && value.trim()) {
      checkDuplicates({ go_number: value.trim() });
    } else if (field === 'source_url' && typeof value === 'string' && value.trim()) {
      checkDuplicates({ source_url: value.trim() });
    }
  };

  // Update dynamic metadata field
  const handleMetadataChange = (field: string, value: unknown) => {
    setDynamicMetadata((prev) => ({
      ...prev,
      [field]: value,
    }));
    setErrors((prev) => {
      const copy = { ...prev };
      delete copy[field];
      return copy;
    });
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);
    setSubmitSuccess(null);

    const validationErrors: Record<string, string> = {};

    if (!title.trim()) {
      validationErrors.title = 'Asset title is required';
    }

    if (!file) {
      validationErrors.file = 'File upload is required';
    }

    // Dynamic metadata validation using shared Zod schemas
    const metadataValidation = validateDynamicMetadata(assetType, dynamicMetadata);
    if (!metadataValidation.success) {
      for (const [k, msg] of Object.entries(metadataValidation.errors)) {
        validationErrors[k] = msg;
      }
    }

    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return; // BLOCKS SUBMISSION & NETWORK POST
    }

    setIsSubmitting(true);

    try {
      // 1. Presign upload URL
      const presignRes = await apiFetch<PresignResponse>('/api/v1/uploads/presign', {
        method: 'POST',
        body: JSON.stringify({
          filename: file!.name,
          mime_type: file!.type || 'application/octet-stream',
          file_size_bytes: file!.size,
        }),
      });

      // 2. Direct upload to Cloudflare R2
      const uploadRes = await fetch(presignRes.upload_url, {
        method: 'PUT',
        body: file!,
        headers: {
          'Content-Type': file!.type || 'application/octet-stream',
        },
      });

      if (!uploadRes.ok) {
        throw new Error(`Direct storage upload failed with status ${uploadRes.status}`);
      }

      // 3. Create Asset in API
      const assetPayload = {
        title: title.trim(),
        asset_type: assetType,
        primary_language: primaryLanguage,
        source_name: sourceName.trim() || null,
        source_url: dynamicMetadata.source_url || null,
        r2_object_key: presignRes.object_key,
        file_sha256: fileSha256 || '0'.repeat(64),
        mime_type: file!.type || 'application/octet-stream',
        file_size_bytes: file!.size,
        go_number: dynamicMetadata.go_number || null,
        copyright_flag: copyrightFlag,
        is_public_record: isPublicRecord,
        dynamic_metadata: dynamicMetadata,
        geo_entity_ids: geoEntities.map((g) => g.id),
        status: 'draft',
      };

      const assetRes = await apiFetch<AssetCreateResponse>('/api/v1/assets', {
        method: 'POST',
        body: JSON.stringify(assetPayload),
      });

      setSubmitSuccess(assetRes);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to complete upload';
      setSubmitError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto', padding: '2rem 1rem' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, margin: 0, color: '#111827' }}>
          Ingest & Upload Digital Asset
        </h1>
        <p style={{ color: '#6b7280', marginTop: '0.5rem', fontSize: '0.875rem' }}>
          Upload documents, clippings, social archives, or media with dynamic metadata validation and deduplication.
        </p>
      </div>

      {/* Duplicate warning banner */}
      <DuplicateWarningBanner
        matches={duplicateMatches}
        onDismiss={() => setDuplicateMatches([])}
      />

      {isCheckingDuplicate && (
        <div style={{ fontSize: '0.875rem', color: '#b45309', marginBottom: '1rem' }}>
          Checking repository for duplicates...
        </div>
      )}

      {/* Success banner */}
      {submitSuccess && (
        <div
          role="status"
          data-testid="upload-success-banner"
          style={{
            backgroundColor: '#ecfdf5',
            border: '1px solid #10b981',
            borderRadius: '6px',
            padding: '1rem',
            marginBottom: '1.5rem',
            color: '#065f46',
          }}
        >
          <h4 style={{ margin: '0 0 0.5rem 0', fontWeight: 600 }}>Asset Uploaded Successfully!</h4>
          <p style={{ margin: 0, fontSize: '0.875rem' }}>
            Draft asset created:{' '}
            <Link
              href={`/repository/${submitSuccess.id}`}
              style={{ fontWeight: 600, textDecoration: 'underline', color: '#047857' }}
            >
              {submitSuccess.title} (ID: {submitSuccess.id})
            </Link>
          </p>
        </div>
      )}

      {/* Submission error */}
      {submitError && (
        <div
          role="alert"
          data-testid="upload-error-banner"
          style={{
            backgroundColor: '#fef2f2',
            border: '1px solid #ef4444',
            borderRadius: '6px',
            padding: '1rem',
            marginBottom: '1.5rem',
            color: '#991b1b',
          }}
        >
          <strong>Upload Failed:</strong> {submitError}
        </div>
      )}

      <form onSubmit={handleSubmit} data-testid="asset-upload-form" noValidate>
        {/* Asset Type Selector */}
        <div style={{ marginBottom: '1.5rem' }}>
          <label
            htmlFor="asset-type-select"
            style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.5rem' }}
          >
            Asset Type <span style={{ color: '#dc2626' }}>*</span>
          </label>
          <select
            id="asset-type-select"
            value={assetType}
            onChange={(e) => handleAssetTypeChange(e.target.value as AssetType)}
            data-testid="select-asset-type"
            style={{
              width: '100%',
              padding: '0.625rem 0.75rem',
              borderRadius: '4px',
              border: '1px solid #d1d5db',
              fontSize: '0.875rem',
              backgroundColor: '#fff',
            }}
          >
            {ASSET_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* File Upload Input */}
        <div style={{ marginBottom: '1.5rem' }}>
          <label
            htmlFor="file-upload"
            style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.5rem' }}
          >
            File Upload <span style={{ color: '#dc2626' }}>*</span>
          </label>
          <input
            id="file-upload"
            type="file"
            onChange={handleFileChange}
            data-testid="input-file"
            style={{
              width: '100%',
              padding: '0.5rem',
              borderRadius: '4px',
              border: errors.file ? '1px solid #dc2626' : '1px solid #d1d5db',
              fontSize: '0.875rem',
            }}
          />
          {errors.file && (
            <p
              data-testid="error-file"
              style={{ color: '#dc2626', fontSize: '0.75rem', marginTop: '0.25rem', marginBottom: 0 }}
            >
              {errors.file}
            </p>
          )}
          {fileSha256 && (
            <p style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem', marginBottom: 0 }}>
              SHA-256: <code>{fileSha256}</code>
            </p>
          )}
        </div>

        {/* Core Common Fields */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
          <div>
            <label
              htmlFor="asset-title"
              style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.25rem' }}
            >
              Asset Title <span style={{ color: '#dc2626' }}>*</span>
            </label>
            <input
              id="asset-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. GO MS 104 Revenue Allotment"
              data-testid="input-title"
              style={{
                width: '100%',
                padding: '0.5rem 0.75rem',
                borderRadius: '4px',
                border: errors.title ? '1px solid #dc2626' : '1px solid #d1d5db',
                fontSize: '0.875rem',
              }}
            />
            {errors.title && (
              <p
                data-testid="error-title"
                style={{ color: '#dc2626', fontSize: '0.75rem', marginTop: '0.25rem', marginBottom: 0 }}
              >
                {errors.title}
              </p>
            )}
          </div>

          <div>
            <label
              htmlFor="primary-language"
              style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.25rem' }}
            >
              Primary Language
            </label>
            <select
              id="primary-language"
              value={primaryLanguage}
              onChange={(e) => setPrimaryLanguage(e.target.value)}
              data-testid="select-primary-language"
              style={{
                width: '100%',
                padding: '0.5rem 0.75rem',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                fontSize: '0.875rem',
                backgroundColor: '#fff',
              }}
            >
              <option value="telugu">Telugu</option>
              <option value="english">English</option>
              <option value="mixed">Mixed</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="source-name"
              style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.25rem' }}
            >
              Source / Archive Name
            </label>
            <input
              id="source-name"
              type="text"
              value={sourceName}
              onChange={(e) => setSourceName(e.target.value)}
              placeholder="e.g. AP Gazette, Party Archive"
              data-testid="input-source-name"
              style={{
                width: '100%',
                padding: '0.5rem 0.75rem',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                fontSize: '0.875rem',
              }}
            />
          </div>

          <div>
            <label
              htmlFor="copyright-flag"
              style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.25rem' }}
            >
              Copyright Flag
            </label>
            <select
              id="copyright-flag"
              value={copyrightFlag}
              onChange={(e) => setCopyrightFlag(e.target.value)}
              data-testid="select-copyright-flag"
              style={{
                width: '100%',
                padding: '0.5rem 0.75rem',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                fontSize: '0.875rem',
                backgroundColor: '#fff',
              }}
            >
              <option value="public_domain">Public Domain</option>
              <option value="internal_research_only">Internal Research Only</option>
              <option value="restricted_copyright">Restricted Copyright</option>
            </select>
          </div>
        </div>

        {/* Public Record Toggle */}
        <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <input
            id="is-public-record"
            type="checkbox"
            checked={isPublicRecord}
            onChange={(e) => setIsPublicRecord(e.target.checked)}
            data-testid="checkbox-is-public-record"
            style={{ width: '1rem', height: '1rem' }}
          />
          <label htmlFor="is-public-record" style={{ fontSize: '0.875rem', color: '#374151' }}>
            Mark as Public Record (suitable for non-confidential public policy research)
          </label>
        </div>

        {/* Geographic Multi-Tag Selector */}
        <div style={{ marginBottom: '1.5rem' }}>
          <label
            style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.5rem' }}
          >
            Geographic Hierarchy Tags
          </label>
          <GeoTagSelector
            value={geoEntities}
            onChange={setGeoEntities}
            placeholder="Tag districts, constituencies, mandals, or villages..."
          />
        </div>

        {/* Dynamic Type-Specific Metadata Fields */}
        <div
          style={{
            backgroundColor: '#f9fafb',
            border: '1px solid #e5e7eb',
            borderRadius: '6px',
            padding: '1.25rem',
            marginBottom: '1.5rem',
          }}
        >
          <DynamicMetadataFields
            assetType={assetType}
            values={dynamicMetadata}
            errors={errors}
            onChange={handleMetadataChange}
            onBlurField={handleMetadataBlur}
          />
        </div>

        {/* Submit Button */}
        <div>
          <button
            type="submit"
            disabled={isSubmitting}
            data-testid="btn-submit-upload"
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: isSubmitting ? '#9ca3af' : '#dc2626',
              color: '#fff',
              fontWeight: 600,
              fontSize: '0.875rem',
              borderRadius: '6px',
              border: 'none',
              cursor: isSubmitting ? 'not-allowed' : 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            {isSubmitting ? 'Uploading & Creating Asset...' : 'Ingest Asset'}
          </button>
        </div>
      </form>
    </div>
  );
}
