'use client';

import React, { useState } from 'react';
import { NewspaperClippingItem } from '@jsp/shared';

export interface SideBySideClippingViewerProps {
  clipping: NewspaperClippingItem;
  onClose?: () => void;
}

export function SideBySideClippingViewer({ clipping, onClose }: SideBySideClippingViewerProps) {
  const [zoom, setZoom] = useState<number>(1.0);
  const [copied, setCopied] = useState<boolean>(false);

  const handleZoomIn = () => {
    setZoom((prev) => Math.min(Number((prev + 0.25).toFixed(2)), 4.0));
  };

  const handleZoomOut = () => {
    setZoom((prev) => Math.max(Number((prev - 0.25).toFixed(2)), 0.5));
  };

  const handleZoomReset = () => {
    setZoom(1.0);
  };

  const handleCopyText = async () => {
    if (clipping.extracted_text) {
      try {
        await navigator.clipboard.writeText(clipping.extracted_text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch {
        // Fallback or ignore in non-browser environments
      }
    }
  };

  return (
    <div
      data-testid="side-by-side-viewer"
      style={{
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: '#ffffff',
        borderRadius: '8px',
        border: '1px solid #e5e7eb',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
        marginBottom: '2rem',
        overflow: 'hidden',
      }}
    >
      {/* Top Header Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '0.75rem 1.25rem',
          backgroundColor: '#1f2937',
          color: '#ffffff',
          borderBottom: '1px solid #374151',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span
            style={{
              backgroundColor: '#dc2626',
              color: '#ffffff',
              fontSize: '0.75rem',
              fontWeight: 600,
              padding: '0.2rem 0.5rem',
              borderRadius: '4px',
              textTransform: 'uppercase',
            }}
          >
            Clipping Viewer
          </span>
          <h3
            data-testid="clipping-headline"
            style={{
              fontSize: '1.1rem',
              fontWeight: 600,
              margin: 0,
              color: '#f9fafb',
              maxWidth: '600px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {clipping.headline}
          </h3>
        </div>

        {onClose && (
          <button
            type="button"
            onClick={onClose}
            data-testid="close-viewer-btn"
            style={{
              backgroundColor: 'transparent',
              border: 'none',
              color: '#9ca3af',
              fontSize: '1.25rem',
              cursor: 'pointer',
              padding: '0.25rem 0.5rem',
              borderRadius: '4px',
            }}
            title="Close viewer"
          >
            ✕
          </button>
        )}
      </div>

      {/* Split-pane container */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'row',
          flexWrap: 'wrap',
          minHeight: '540px',
        }}
      >
        {/* Left Pane: Zoomable Scanned Clipping Image */}
        <div
          data-testid="viewer-left-pane"
          style={{
            flex: '1 1 50%',
            minWidth: '320px',
            display: 'flex',
            flexDirection: 'column',
            borderRight: '1px solid #e5e7eb',
            backgroundColor: '#f3f4f6',
          }}
        >
          {/* Zoom controls toolbar */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0.5rem 1rem',
              backgroundColor: '#e5e7eb',
              borderBottom: '1px solid #d1d5db',
            }}
          >
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#374151' }}>
              Scanned Clipping (Original)
            </span>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <button
                type="button"
                onClick={handleZoomOut}
                disabled={zoom <= 0.5}
                data-testid="zoom-out-btn"
                style={{
                  padding: '0.25rem 0.6rem',
                  fontSize: '0.875rem',
                  fontWeight: 700,
                  backgroundColor: '#ffffff',
                  border: '1px solid #cbd5e1',
                  borderRadius: '4px',
                  cursor: zoom <= 0.5 ? 'not-allowed' : 'pointer',
                  color: '#334155',
                }}
                title="Zoom Out"
              >
                −
              </button>

              <span
                data-testid="zoom-level"
                style={{
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  color: '#475569',
                  minWidth: '45px',
                  textAlign: 'center',
                }}
              >
                {Math.round(zoom * 100)}%
              </span>

              <button
                type="button"
                onClick={handleZoomIn}
                disabled={zoom >= 4.0}
                data-testid="zoom-in-btn"
                style={{
                  padding: '0.25rem 0.6rem',
                  fontSize: '0.875rem',
                  fontWeight: 700,
                  backgroundColor: '#ffffff',
                  border: '1px solid #cbd5e1',
                  borderRadius: '4px',
                  cursor: zoom >= 4.0 ? 'not-allowed' : 'pointer',
                  color: '#334155',
                }}
                title="Zoom In"
              >
                +
              </button>

              <button
                type="button"
                onClick={handleZoomReset}
                data-testid="zoom-reset-btn"
                style={{
                  padding: '0.25rem 0.5rem',
                  fontSize: '0.75rem',
                  fontWeight: 500,
                  backgroundColor: '#ffffff',
                  border: '1px solid #cbd5e1',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  color: '#334155',
                }}
              >
                Reset
              </button>
            </div>
          </div>

          {/* Image Container with scroll viewport */}
          <div
            data-testid="clipping-image-container"
            style={{
              flex: 1,
              overflow: 'auto',
              padding: '1.5rem',
              display: 'flex',
              alignItems: 'flex-start',
              justifyContent: 'center',
              backgroundColor: '#475569',
            }}
          >
            {clipping.preview_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={clipping.preview_url}
                alt={clipping.headline}
                data-testid="clipping-image"
                style={{
                  transform: `scale(${zoom})`,
                  transformOrigin: 'top center',
                  transition: 'transform 0.15s ease-out',
                  maxWidth: '100%',
                  borderRadius: '4px',
                  boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.3)',
                  objectFit: 'contain',
                }}
              />
            ) : (
              <div
                style={{
                  color: '#94a3b8',
                  padding: '2rem',
                  textAlign: 'center',
                }}
              >
                Image preview unavailable
              </div>
            )}
          </div>
        </div>

        {/* Right Pane: Extracted OCR Text & Metadata */}
        <div
          data-testid="viewer-right-pane"
          style={{
            flex: '1 1 50%',
            minWidth: '320px',
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: '#ffffff',
          }}
        >
          {/* Metadata Card Header */}
          <div
            style={{
              padding: '1rem 1.25rem',
              borderBottom: '1px solid #e5e7eb',
              backgroundColor: '#f9fafb',
            }}
          >
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                gap: '0.75rem',
                marginBottom: '0.75rem',
              }}
            >
              <div>
                <span style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block' }}>
                  Publication
                </span>
                <span
                  data-testid="clipping-newspaper"
                  style={{ fontSize: '0.9rem', fontWeight: 600, color: '#111827' }}
                >
                  {clipping.newspaper_name}
                </span>
              </div>

              {clipping.edition && (
                <div>
                  <span style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block' }}>
                    Edition
                  </span>
                  <span
                    data-testid="clipping-edition"
                    style={{ fontSize: '0.9rem', fontWeight: 600, color: '#111827' }}
                  >
                    {clipping.edition}
                  </span>
                </div>
              )}

              <div>
                <span style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block' }}>
                  Date
                </span>
                <span
                  data-testid="clipping-date"
                  style={{ fontSize: '0.9rem', fontWeight: 600, color: '#111827' }}
                >
                  {clipping.publication_date}
                </span>
              </div>

              {clipping.page_number && (
                <div>
                  <span style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block' }}>
                    Page
                  </span>
                  <span
                    data-testid="clipping-page"
                    style={{ fontSize: '0.9rem', fontWeight: 600, color: '#111827' }}
                  >
                    Page {clipping.page_number}
                  </span>
                </div>
              )}
            </div>

            {/* Geographic tags */}
            {clipping.geo_tags && clipping.geo_tags.length > 0 && (
              <div
                data-testid="clipping-geo-tags"
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '0.4rem',
                  alignItems: 'center',
                  marginTop: '0.5rem',
                }}
              >
                <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>Geography:</span>
                {clipping.geo_tags.map((geo) => (
                  <span
                    key={geo.id}
                    data-testid={`geo-badge-${geo.id}`}
                    style={{
                      fontSize: '0.75rem',
                      backgroundColor: '#e0f2fe',
                      color: '#0369a1',
                      padding: '0.15rem 0.5rem',
                      borderRadius: '9999px',
                      fontWeight: 500,
                    }}
                  >
                    {geo.name} {geo.telugu_name ? `(${geo.telugu_name})` : ''}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Extracted OCR Text Content */}
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              padding: '1rem 1.25rem',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '0.75rem',
              }}
            >
              <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#374151', margin: 0 }}>
                Extracted OCR Text (Telugu / English)
              </h4>

              {clipping.extracted_text && (
                <button
                  type="button"
                  onClick={handleCopyText}
                  data-testid="copy-ocr-btn"
                  style={{
                    fontSize: '0.75rem',
                    padding: '0.2rem 0.5rem',
                    backgroundColor: copied ? '#dcfce7' : '#f3f4f6',
                    color: copied ? '#15803d' : '#4b5563',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  {copied ? '✓ Copied' : 'Copy Text'}
                </button>
              )}
            </div>

            <div
              data-testid="extracted-ocr-text"
              style={{
                flex: 1,
                overflowY: 'auto',
                backgroundColor: '#f9fafb',
                border: '1px solid #e5e7eb',
                borderRadius: '6px',
                padding: '1rem',
                fontSize: '0.925rem',
                lineHeight: '1.6',
                color: '#1f2937',
                whiteSpace: 'pre-wrap',
                fontFamily:
                  'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans Telugu", sans-serif',
                maxHeight: '400px',
              }}
            >
              {clipping.extracted_text || 'No OCR text extracted yet.'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
