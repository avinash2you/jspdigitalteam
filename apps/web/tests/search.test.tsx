import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import { AssetType, SearchPaginationResponse, SearchResultItem } from '@jsp/shared';
import * as apiClient from '@/lib/api-client';
import { SearchResultCard } from '@/components/search/SearchResultCard';
import { SearchFiltersSidebar } from '@/components/search/SearchFiltersSidebar';
import SearchPage from '@/app/search/page';

const mockPush = vi.fn();
let mockSearchParams = new URLSearchParams();

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useSearchParams: () => mockSearchParams,
}));

const sampleResult1: SearchResultItem = {
  id: 'asset-doc-1',
  title: 'Polavaram Irrigation Project Funds Release',
  snippet: 'ఆంధ్రప్రదేశ్ ప్రభుత్వం <mark>రైతు</mark> <mark>భరోసా</mark> పథకం కింద నిధులు విడుదల చేసింది.',
  highlighted_snippet: 'ఆంధ్రప్రదేశ్ ప్రభుత్వం <mark>రైతు</mark> <mark>భరోసా</mark> పథకం కింద నిధులు విడుదల చేసింది.',
  score: 12.5,
  asset_type: AssetType.GOVERNMENT_DOCUMENT,
  go_number: 'GO-MS-104',
  publication_date: '2024-03-05',
  source_name: 'Water Resources Dept',
  geo_tags: [
    {
      id: 'geo-1',
      name: 'East Godavari',
      telugu_name: 'తూర్పు గోదావరి',
      tier: 'district',
      code: 'AP-EGD',
    },
  ],
};

const sampleResult2: SearchResultItem = {
  id: 'asset-news-2',
  title: 'Varahi Yatra Public Meeting Kakinada',
  snippet: 'Massive public meeting during <mark>varahi</mark> yatra tour in Kakinada district.',
  highlighted_snippet: 'Massive public meeting during <mark>varahi</mark> yatra tour in Kakinada district.',
  score: 8.2,
  asset_type: AssetType.NEWSPAPER_CLIPPING,
  publication_date: '2024-03-20',
  source_name: 'Eenadu',
  geo_tags: [
    {
      id: 'geo-2',
      name: 'Kakinada',
      tier: 'district',
      code: 'AP-KKD',
    },
  ],
};

describe('SearchResultCard Component', () => {
  it('renders card with link to /repository/[id], badges, and safe <mark> highlighted snippet', () => {
    render(<SearchResultCard item={sampleResult1} />);

    // Card exists
    expect(screen.getByTestId('search-card-asset-doc-1')).toBeDefined();

    // Link points to /repository/asset-doc-1
    const link = screen.getByTestId('result-link-asset-doc-1') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toBe('/repository/asset-doc-1');
    expect(link.textContent).toBe(sampleResult1.title);

    // Badges
    expect(screen.getByTestId('asset-type-badge').textContent).toContain('Govt Document');
    expect(screen.getByTestId('go-number-badge').textContent).toBe('GO-MS-104');

    // Snippet renders mark elements
    const snippetElem = screen.getByTestId('search-snippet');
    expect(snippetElem.textContent).toContain('రైతు భరోసా');
    const markTags = snippetElem.querySelectorAll('mark');
    expect(markTags.length).toBe(2);
    expect(markTags[0].textContent).toBe('రైతు');
    expect(markTags[1].textContent).toBe('భరోసా');

    // Geo tag
    expect(screen.getByTestId('geo-badge-geo-1')).toBeDefined();
  });
});

describe('SearchFiltersSidebar Component', () => {
  it('toggles asset type checkboxes and triggers callback', async () => {
    const handleTypesChange = vi.fn();
    const handleReset = vi.fn();

    render(
      <SearchFiltersSidebar
        selectedAssetTypes={[AssetType.GOVERNMENT_DOCUMENT]}
        onAssetTypesChange={handleTypesChange}
        dateFrom=""
        onDateFromChange={vi.fn()}
        dateTo=""
        onDateToChange={vi.fn()}
        department=""
        onDepartmentChange={vi.fn()}
        selectedGeoEntities={[]}
        onGeoEntitiesChange={vi.fn()}
        onResetFilters={handleReset}
      />
    );

    const govCheckbox = screen.getByTestId(`checkbox-asset-type-${AssetType.GOVERNMENT_DOCUMENT}`) as HTMLInputElement;
    expect(govCheckbox.checked).toBe(true);

    const newsCheckbox = screen.getByTestId(`checkbox-asset-type-${AssetType.NEWSPAPER_CLIPPING}`) as HTMLInputElement;
    expect(newsCheckbox.checked).toBe(false);

    // Toggle news checkbox
    await act(async () => {
      fireEvent.click(newsCheckbox);
    });
    expect(handleTypesChange).toHaveBeenCalledWith([
      AssetType.GOVERNMENT_DOCUMENT,
      AssetType.NEWSPAPER_CLIPPING,
    ]);

    // Click Reset
    const resetBtn = screen.getByTestId('reset-filters-btn');
    await act(async () => {
      fireEvent.click(resetBtn);
    });
    expect(handleReset).toHaveBeenCalledTimes(1);
  });
});

describe('SearchPage Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams = new URLSearchParams();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders search page and triggers search on query submit with highlighted snippets', async () => {
    let capturedEndpoint = '';
    vi.spyOn(apiClient, 'apiFetch').mockImplementation(async (endpoint: string) => {
      if (endpoint.startsWith('/api/v1/search')) {
        capturedEndpoint = endpoint;
        const resp: SearchPaginationResponse = {
          items: [sampleResult1, sampleResult2],
          total: 2,
          page: 1,
          page_size: 20,
          total_pages: 1,
        };
        return resp;
      }
      return {};
    });

    render(<SearchPage />);

    expect(screen.getByTestId('search-title')).toBeDefined();
    expect(screen.getByTestId('search-input')).toBeDefined();
    expect(screen.getByTestId('search-filters-sidebar')).toBeDefined();

    // Type query into search bar
    const searchInput = screen.getByTestId('search-input');
    await act(async () => {
      fireEvent.change(searchInput, { target: { value: 'రైతు భరోసా' } });
    });

    // Click Search submit
    const submitBtn = screen.getByTestId('search-submit-btn');
    await act(async () => {
      fireEvent.click(submitBtn);
    });

    // Wait for results
    await waitFor(() => {
      expect(capturedEndpoint).toContain('q=');
      expect(screen.getByTestId('search-card-asset-doc-1')).toBeDefined();
      expect(screen.getByTestId('search-card-asset-news-2')).toBeDefined();
      expect(screen.getByTestId('search-results-count').textContent).toContain('2');
    });

    // Verify URL was pushed
    expect(mockPush).toHaveBeenCalled();
  });

  it('renders empty state when search returns no matching assets', async () => {
    vi.spyOn(apiClient, 'apiFetch').mockImplementation(async (endpoint: string) => {
      if (endpoint.startsWith('/api/v1/search')) {
        const resp: SearchPaginationResponse = {
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
          total_pages: 0,
        };
        return resp;
      }
      return {};
    });

    render(<SearchPage />);

    await waitFor(() => {
      expect(screen.getByTestId('search-empty-state')).toBeDefined();
      expect(screen.getByText('No assets matched your search')).toBeDefined();
    });
  });
});
