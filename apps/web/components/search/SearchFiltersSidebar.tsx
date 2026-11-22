'use client';

import React from 'react';
import { AssetType, GeoEntity } from '@jsp/shared';
import { GeoTagSelector } from '@/components/geography/GeoTagSelector';

export interface SearchFiltersSidebarProps {
  selectedAssetTypes: string[];
  onAssetTypesChange: (types: string[]) => void;
  dateFrom: string;
  onDateFromChange: (date: string) => void;
  dateTo: string;
  onDateToChange: (date: string) => void;
  department: string;
  onDepartmentChange: (dept: string) => void;
  selectedGeoEntities: GeoEntity[];
  onGeoEntitiesChange: (entities: GeoEntity[]) => void;
  onResetFilters: () => void;
}

const ALL_ASSET_TYPES = [
  { type: AssetType.GOVERNMENT_DOCUMENT, label: 'Government Document (GO)' },
  { type: AssetType.NEWSPAPER_CLIPPING, label: 'Newspaper Clipping' },
  { type: AssetType.ONLINE_NEWS_SOCIAL, label: 'Online / Social News' },
  { type: AssetType.VIDEO_AUDIO, label: 'Video / Audio Recording' },
  { type: AssetType.IMAGE_INFOGRAPHIC, label: 'Image / Infographic' },
  { type: AssetType.RESEARCH_MATERIAL, label: 'Research Material' },
];

export function SearchFiltersSidebar({
  selectedAssetTypes,
  onAssetTypesChange,
  dateFrom,
  onDateFromChange,
  dateTo,
  onDateToChange,
  department,
  onDepartmentChange,
  selectedGeoEntities,
  onGeoEntitiesChange,
  onResetFilters,
}: SearchFiltersSidebarProps) {
  const handleToggleAssetType = (type: string) => {
    if (selectedAssetTypes.includes(type)) {
      onAssetTypesChange(selectedAssetTypes.filter((t) => t !== type));
    } else {
      onAssetTypesChange([...selectedAssetTypes, type]);
    }
  };

  return (
    <aside
      data-testid="search-filters-sidebar"
      style={{
        width: '300px',
        flexShrink: 0,
        backgroundColor: '#ffffff',
        border: '1px solid #e5e7eb',
        borderRadius: '8px',
        padding: '1.25rem',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.5rem',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid #f3f4f6',
          paddingBottom: '0.75rem',
        }}
      >
        <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#111827', margin: 0 }}>
          Search Filters
        </h3>
        <button
          type="button"
          onClick={onResetFilters}
          data-testid="reset-filters-btn"
          style={{
            fontSize: '0.75rem',
            color: '#dc2626',
            backgroundColor: 'transparent',
            border: 'none',
            cursor: 'pointer',
            padding: 0,
            fontWeight: 500,
          }}
        >
          Reset All
        </button>
      </div>

      {/* Asset Type Checkboxes */}
      <div>
        <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: '#374151', margin: '0 0 0.5rem 0' }}>
          Asset Types
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          {ALL_ASSET_TYPES.map(({ type, label }) => {
            const isChecked = selectedAssetTypes.includes(type);
            return (
              <label
                key={type}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.85rem',
                  color: '#4b5563',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  data-testid={`checkbox-asset-type-${type}`}
                  checked={isChecked}
                  onChange={() => handleToggleAssetType(type)}
                  style={{ cursor: 'pointer' }}
                />
                <span>{label}</span>
              </label>
            );
          })}
        </div>
      </div>

      {/* Department Filter */}
      <div>
        <label
          htmlFor="filter-department"
          style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#374151', marginBottom: '0.35rem' }}
        >
          Issuing Department
        </label>
        <input
          id="filter-department"
          type="text"
          data-testid="filter-department"
          placeholder="e.g. Revenue, Agriculture"
          value={department}
          onChange={(e) => onDepartmentChange(e.target.value)}
          style={{
            width: '100%',
            padding: '0.45rem 0.65rem',
            fontSize: '0.85rem',
            border: '1px solid #d1d5db',
            borderRadius: '6px',
            boxSizing: 'border-box',
          }}
        />
      </div>

      {/* Date Range Inputs */}
      <div>
        <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: '#374151', margin: '0 0 0.5rem 0' }}>
          Publication Date Range
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div>
            <label
              htmlFor="filter-date-from"
              style={{ display: 'block', fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.2rem' }}
            >
              From:
            </label>
            <input
              id="filter-date-from"
              type="date"
              data-testid="filter-date-from"
              value={dateFrom}
              onChange={(e) => onDateFromChange(e.target.value)}
              style={{
                width: '100%',
                padding: '0.4rem 0.6rem',
                fontSize: '0.85rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                boxSizing: 'border-box',
              }}
            />
          </div>
          <div>
            <label
              htmlFor="filter-date-to"
              style={{ display: 'block', fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.2rem' }}
            >
              To:
            </label>
            <input
              id="filter-date-to"
              type="date"
              data-testid="filter-date-to"
              value={dateTo}
              onChange={(e) => onDateToChange(e.target.value)}
              style={{
                width: '100%',
                padding: '0.4rem 0.6rem',
                fontSize: '0.85rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                boxSizing: 'border-box',
              }}
            />
          </div>
        </div>
      </div>

      {/* Geography Selector */}
      <div style={{ borderTop: '1px solid #f3f4f6', paddingTop: '1rem' }}>
        <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: '#374151', margin: '0 0 0.35rem 0' }}>
          Geographic Hierarchy
        </h4>
        <p style={{ fontSize: '0.75rem', color: '#6b7280', margin: '0 0 0.5rem 0' }}>
          Automatically expands child mandals, villages, and pre-2022 historical district aliases.
        </p>
        <div data-testid="filter-geo">
          <GeoTagSelector
            value={selectedGeoEntities}
            onChange={onGeoEntitiesChange}
            placeholder="Search district, mandal, or alias..."
          />
        </div>
      </div>
    </aside>
  );
}
