import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { GeoTagSelector } from './GeoTagSelector';
import { GeoEntity, GeoTier } from '@jsp/shared';
import * as apiClient from '@/lib/api-client';

describe('GeoTagSelector', () => {
  const sampleDistrict: GeoEntity = {
    id: 'geo-1',
    name: 'East Godavari',
    telugu_name: 'తూర్పు గోదావరి',
    tier: GeoTier.DISTRICT,
    code: 'AP-EGD',
  };

  const sampleACWithAlias: GeoEntity = {
    id: 'geo-2',
    name: 'Kovvur Assembly Constituency',
    telugu_name: 'కొవ్వూరు',
    tier: GeoTier.ASSEMBLY_CONSTITUENCY,
    code: 'AP-AC-054',
    matched_alias: 'West Godavari (Undivided)',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders selected tags with tier badges and alias indicators', () => {
    const onChange = vi.fn();
    render(
      <GeoTagSelector
        value={[sampleDistrict, sampleACWithAlias]}
        onChange={onChange}
      />
    );

    expect(screen.getByText('East Godavari')).toBeDefined();
    expect(screen.getByText('Kovvur Assembly Constituency')).toBeDefined();

    const tierBadges = screen.getAllByTestId('tier-badge');
    expect(tierBadges.length).toBe(2);
    expect(tierBadges[0]?.textContent).toBe('District');
    expect(tierBadges[1]?.textContent).toBe('Assembly');

    const aliasBadge = screen.getByTestId('alias-badge');
    expect(aliasBadge).toBeDefined();
    expect(aliasBadge.textContent).toBe('Pre-2022 Alias');
  });

  it('removes tag when remove button is clicked', () => {
    const onChange = vi.fn();
    render(
      <GeoTagSelector
        value={[sampleDistrict, sampleACWithAlias]}
        onChange={onChange}
      />
    );

    const removeButton = screen.getByTestId('remove-tag-geo-1');
    fireEvent.click(removeButton);

    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith([sampleACWithAlias]);
  });

  it('executes debounced search and allows selecting an alias match', async () => {
    vi.useFakeTimers();

    const mockSearchResults: GeoEntity[] = [
      {
        id: 'geo-3',
        name: 'West Godavari',
        tier: GeoTier.DISTRICT,
        code: 'AP-WGD',
      },
      {
        id: 'geo-2',
        name: 'Kovvur Assembly Constituency',
        tier: GeoTier.ASSEMBLY_CONSTITUENCY,
        code: 'AP-AC-054',
        matched_alias: 'West Godavari (Undivided)',
      },
    ];

    const apiFetchSpy = vi
      .spyOn(apiClient, 'apiFetch')
      .mockResolvedValue(mockSearchResults);

    const onChange = vi.fn();
    render(<GeoTagSelector value={[]} onChange={onChange} />);

    const input = screen.getByTestId('geo-search-input');
    fireEvent.change(input, { target: { value: 'West Godavari' } });

    // Verify debounce: apiFetch should NOT be called immediately
    expect(apiFetchSpy).not.toHaveBeenCalled();

    // Fast-forward by 250ms debounce time
    await act(async () => {
      vi.advanceTimersByTime(250);
    });

    expect(apiFetchSpy).toHaveBeenCalledTimes(1);
    expect(apiFetchSpy).toHaveBeenCalledWith(
      '/api/v1/geography/search?q=West+Godavari&limit=20',
      { token: undefined }
    );

    // Dropdown should be open with results
    expect(screen.getByTestId('geo-autocomplete-dropdown')).toBeDefined();
    expect(screen.getByText('Alias: West Godavari (Undivided)')).toBeDefined();

    // Click the alias match item
    const option = screen.getByTestId('geo-option-geo-2');
    fireEvent.click(option);

    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith([mockSearchResults[1]]);

    vi.useRealTimers();
  });

  it('prevents duplicate tag selection when entity already exists in value', async () => {
    vi.useFakeTimers();

    const mockSearchResults: GeoEntity[] = [sampleDistrict];
    vi.spyOn(apiClient, 'apiFetch').mockResolvedValue(mockSearchResults);

    const onChange = vi.fn();
    render(<GeoTagSelector value={[sampleDistrict]} onChange={onChange} />);

    const input = screen.getByTestId('geo-search-input');
    fireEvent.change(input, { target: { value: 'East Godavari' } });

    await act(async () => {
      vi.advanceTimersByTime(250);
    });

    const option = screen.getByTestId('geo-option-geo-1');
    fireEvent.click(option);

    // onChange should not be called because geo-1 is already in value
    expect(onChange).not.toHaveBeenCalled();

    vi.useRealTimers();
  });
});
