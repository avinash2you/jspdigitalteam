'use client';

import React from 'react';
import { AssetType } from '@jsp/shared';

export interface DynamicMetadataFieldsProps {
  assetType: AssetType | string;
  values: Record<string, unknown>;
  errors: Record<string, string>;
  onChange: (field: string, value: unknown) => void;
  onBlurField?: (field: string, value: unknown) => void;
}

export function DynamicMetadataFields({
  assetType,
  values,
  errors,
  onChange,
  onBlurField,
}: DynamicMetadataFieldsProps) {
  const renderTextInput = (
    name: string,
    label: string,
    isRequired: boolean,
    placeholder = '',
    type = 'text'
  ) => {
    const error = errors[name];
    const rawVal = values[name];
    const val = typeof rawVal === 'string' || typeof rawVal === 'number' ? rawVal : '';

    return (
      <div style={{ marginBottom: '1rem' }} data-testid={`field-container-${name}`}>
        <label
          htmlFor={`meta-${name}`}
          style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.25rem' }}
        >
          {label} {isRequired && <span style={{ color: '#dc2626' }}>*</span>}
        </label>
        <input
          id={`meta-${name}`}
          name={name}
          type={type}
          value={val}
          placeholder={placeholder}
          onChange={(e) => onChange(name, e.target.value)}
          onBlur={() => onBlurField && onBlurField(name, val)}
          data-testid={`input-${name}`}
          style={{
            width: '100%',
            padding: '0.5rem 0.75rem',
            borderRadius: '4px',
            border: error ? '1px solid #dc2626' : '1px solid #d1d5db',
            fontSize: '0.875rem',
            outline: 'none',
          }}
        />
        {error && (
          <p
            data-testid={`error-${name}`}
            style={{ color: '#dc2626', fontSize: '0.75rem', marginTop: '0.25rem', marginBottom: 0 }}
          >
            {error}
          </p>
        )}
      </div>
    );
  };

  const renderTextarea = (
    name: string,
    label: string,
    isRequired: boolean,
    placeholder = '',
    rows = 3
  ) => {
    const error = errors[name];
    const rawVal = values[name];
    const val = typeof rawVal === 'string' ? rawVal : '';

    return (
      <div style={{ marginBottom: '1rem' }} data-testid={`field-container-${name}`}>
        <label
          htmlFor={`meta-${name}`}
          style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.25rem' }}
        >
          {label} {isRequired && <span style={{ color: '#dc2626' }}>*</span>}
        </label>
        <textarea
          id={`meta-${name}`}
          name={name}
          rows={rows}
          value={val}
          placeholder={placeholder}
          onChange={(e) => onChange(name, e.target.value)}
          onBlur={() => onBlurField && onBlurField(name, val)}
          data-testid={`input-${name}`}
          style={{
            width: '100%',
            padding: '0.5rem 0.75rem',
            borderRadius: '4px',
            border: error ? '1px solid #dc2626' : '1px solid #d1d5db',
            fontSize: '0.875rem',
            outline: 'none',
          }}
        />
        {error && (
          <p
            data-testid={`error-${name}`}
            style={{ color: '#dc2626', fontSize: '0.75rem', marginTop: '0.25rem', marginBottom: 0 }}
          >
            {error}
          </p>
        )}
      </div>
    );
  };

  const renderArrayInput = (
    name: string,
    label: string,
    isRequired: boolean,
    placeholder = 'Comma separated values...'
  ) => {
    const error = errors[name];
    const rawVal = values[name];
    const displayVal = Array.isArray(rawVal)
      ? rawVal.join(', ')
      : typeof rawVal === 'string'
        ? rawVal
        : '';

    return (
      <div style={{ marginBottom: '1rem' }} data-testid={`field-container-${name}`}>
        <label
          htmlFor={`meta-${name}`}
          style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.25rem' }}
        >
          {label} {isRequired && <span style={{ color: '#dc2626' }}>*</span>}
        </label>
        <input
          id={`meta-${name}`}
          name={name}
          type="text"
          value={displayVal}
          placeholder={placeholder}
          onChange={(e) => {
            const items = e.target.value
              .split(',')
              .map((s) => s.trim())
              .filter((s) => s.length > 0);
            onChange(name, items);
          }}
          onBlur={() => onBlurField && onBlurField(name, values[name])}
          data-testid={`input-${name}`}
          style={{
            width: '100%',
            padding: '0.5rem 0.75rem',
            borderRadius: '4px',
            border: error ? '1px solid #dc2626' : '1px solid #d1d5db',
            fontSize: '0.875rem',
            outline: 'none',
          }}
        />
        {error && (
          <p
            data-testid={`error-${name}`}
            style={{ color: '#dc2626', fontSize: '0.75rem', marginTop: '0.25rem', marginBottom: 0 }}
          >
            {error}
          </p>
        )}
      </div>
    );
  };

  switch (assetType) {
    case AssetType.GOVERNMENT_DOCUMENT:
      return (
        <div data-testid="fields-government-document">
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem', color: '#1f2937' }}>
            Government Document Details
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            {renderTextInput('go_number', 'GO Number', true, 'e.g. GO-MS-104')}
            {renderTextInput('issuing_department', 'Issuing Department', true, 'e.g. Revenue Department')}
            {renderTextInput('date_of_issue', 'Date of Issue', true, 'YYYY-MM-DD', 'date')}
            {renderTextInput('state', 'State', true, 'Andhra Pradesh')}
            {renderTextInput('district_local_body', 'District / Local Body', false, 'Optional district or municipality')}
            {renderTextInput('related_scheme', 'Related Scheme', false, 'Optional related scheme')}
            {renderTextInput('effective_date', 'Effective Date', false, 'YYYY-MM-DD', 'date')}
            {renderTextInput('supersedes_go_number', 'Supersedes GO Number', false, 'Optional previous GO #')}
          </div>
          {renderTextarea('subject', 'Subject / Summary', true, 'Official subject line or brief summary of the GO', 2)}
        </div>
      );

    case AssetType.NEWSPAPER_CLIPPING:
      return (
        <div data-testid="fields-newspaper-clipping">
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem', color: '#1f2937' }}>
            Newspaper Clipping Details
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            {renderTextInput('newspaper_name', 'Newspaper Name', true, 'e.g. Eenadu, Andhra Jyothy')}
            {renderTextInput('publication_date', 'Publication Date', true, 'YYYY-MM-DD', 'date')}
            {renderTextInput('edition', 'Edition', false, 'e.g. Amaravati, Visakhapatnam')}
            {renderTextInput('page_number', 'Page Number', false, 'e.g. 1')}
            {renderTextInput('column_byline', 'Column / Byline', false, 'e.g. Bureau')}
          </div>
          {renderTextarea('headline', 'Headline', true, 'Main article headline', 2)}
        </div>
      );

    case AssetType.ONLINE_NEWS_SOCIAL:
      return (
        <div data-testid="fields-online-news-social">
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem', color: '#1f2937' }}>
            Online News & Social Archive Details
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            {renderTextInput('platform_publisher', 'Platform / Publisher', true, 'e.g. Twitter/X, The Hindu')}
            {renderTextInput('source_url', 'Source URL', true, 'https://...', 'url')}
            {renderTextInput('published_date', 'Published Date', true, 'YYYY-MM-DD', 'date')}
            {renderTextInput('author_handle', 'Author / Handle', true, 'e.g. @JanaSenaParty')}
          </div>
          {renderTextarea('key_quote', 'Key Quote / Excerpt', false, 'Notable direct statement or excerpt')}
        </div>
      );

    case AssetType.VIDEO_AUDIO:
      return (
        <div data-testid="fields-video-audio">
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem', color: '#1f2937' }}>
            Video & Audio Details
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            {renderTextInput('source_channel_event', 'Source Channel / Event', true, 'e.g. Press Meet Kakinada')}
            {renderTextInput('recording_date', 'Recording Date', true, 'YYYY-MM-DD', 'date')}
            {renderTextInput('duration_sec', 'Duration (seconds)', false, 'e.g. 1800', 'number')}
            {renderTextInput('venue', 'Venue / Location', false, 'e.g. Mangalagiri')}
          </div>
          {renderArrayInput('speakers', 'Speakers', true, 'Pawan Kalyan, Nadendla Manohar')}
        </div>
      );

    case AssetType.IMAGE_INFOGRAPHIC:
      return (
        <div data-testid="fields-image-infographic">
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem', color: '#1f2937' }}>
            Image & Infographic Details
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            {renderTextInput('event_subject', 'Event / Subject', true, 'e.g. Varahi Yatra Phase 3')}
            {renderTextInput('capture_date', 'Capture Date', true, 'YYYY-MM-DD', 'date')}
            {renderTextInput('credit_source', 'Credit / Source', true, 'e.g. JSP Media Wing')}
            {renderTextInput('usage_rights', 'Usage Rights', false, 'e.g. Public Domain, Editorial')}
          </div>
          {renderArrayInput('people_depicted', 'People Depicted', false, 'e.g. Pawan Kalyan, Supporters')}
          {renderTextarea('caption', 'Caption / Description', false, 'Detailed image description')}
        </div>
      );

    case AssetType.RESEARCH_MATERIAL:
      return (
        <div data-testid="fields-research-material">
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem', color: '#1f2937' }}>
            Research Material Details
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            {renderTextInput('document_title', 'Document Title', true, 'e.g. AP Agricultural Debt Study')}
            {renderTextInput('authoring_body', 'Authoring Body / Institute', true, 'e.g. JSP Policy Cell')}
            {renderTextInput('publication_date', 'Publication Date', true, 'YYYY-MM-DD', 'date')}
          </div>
          {renderTextarea('sample_size_methodology', 'Sample Size & Methodology', false, 'e.g. Survey of 1,200 households')}
          {renderTextarea('executive_summary', 'Executive Summary', false, 'Key findings and policy impact')}
        </div>
      );

    default:
      return (
        <div data-testid="fields-unsupported" style={{ color: '#6b7280', fontStyle: 'italic', padding: '1rem' }}>
          Select a valid asset type to configure metadata.
        </div>
      );
  }
}
