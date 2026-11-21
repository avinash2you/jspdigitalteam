import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import { NewspaperClippingItem, NewspaperListResponse } from '@jsp/shared';
import * as apiClient from '@/lib/api-client';
import { SideBySideClippingViewer } from '@/components/newspapers/SideBySideClippingViewer';
import NewspaperArchivePage from '@/app/newspapers/page';

const mockPush = vi.fn();
let mockSearchParams = new URLSearchParams();

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useSearchParams: () => mockSearchParams,
  redirect: vi.fn(),
}));

const sampleClipping1: NewspaperClippingItem = {
  id: 'clipping-1',
  headline: 'Historic Godavari Barrage Modernization',
  newspaper_name: 'Eenadu',
  edition: 'Amaravati',
  publication_date: '2024-03-05',
  page_number: 1,
  extracted_text: 'గోదావరి బ్యారేజీ ఆధునీకరణ పనులు వేగవంతం. డెల్టా రైతులకు పుష్కలంగా సాగునీరు.',
  geo_tags: [
    {
      id: 'geo-1',
      name: 'East Godavari',
      telugu_name: 'తూర్పు గోదావరి',
      tier: 'district',
      code: 'AP-EGD',
    },
  ],
  preview_url: 'https://r2.storage.example/clippings/eenadu_20240305.jpg?presigned=true',
  created_at: '2024-03-05T08:00:00Z',
};

const sampleClipping2: NewspaperClippingItem = {
  id: 'clipping-2',
  headline: 'Visakhapatnam Port Expansion Completed',
  newspaper_name: 'Sakshi',
  edition: 'Visakhapatnam',
  publication_date: '2024-03-12',
  page_number: 3,
  extracted_text: 'విశాఖపట్నం పోర్టు ఆధునీకరణ ద్వారా కార్గో రవాణా రెట్టింపు.',
  geo_tags: [
    {
      id: 'geo-2',
      name: 'Visakhapatnam',
      telugu_name: 'విశాఖపట్నం',
      tier: 'district',
      code: 'AP-VSKP',
    },
  ],
  preview_url: 'https://r2.storage.example/clippings/sakshi_20240312.jpg?presigned=true',
  created_at: '2024-03-12T09:00:00Z',
};

describe('SideBySideClippingViewer Component', () => {
  it('renders both the scanned image and extracted OCR text simultaneously', () => {
    const handleClose = vi.fn();
    render(<SideBySideClippingViewer clipping={sampleClipping1} onClose={handleClose} />);

    // Container
    expect(screen.getByTestId('side-by-side-viewer')).toBeDefined();

    // Left pane with image and zoom controls
    expect(screen.getByTestId('viewer-left-pane')).toBeDefined();
    const image = screen.getByTestId('clipping-image') as HTMLImageElement;
    expect(image.src).toBe(sampleClipping1.preview_url);
    expect(screen.getByTestId('zoom-level').textContent).toBe('100%');

    // Right pane with extracted OCR text and metadata
    expect(screen.getByTestId('viewer-right-pane')).toBeDefined();
    expect(screen.getByTestId('clipping-headline').textContent).toBe(sampleClipping1.headline);
    expect(screen.getByTestId('clipping-newspaper').textContent).toBe('Eenadu');
    expect(screen.getByTestId('clipping-edition').textContent).toBe('Amaravati');
    expect(screen.getByTestId('clipping-date').textContent).toBe('2024-03-05');
    expect(screen.getByTestId('clipping-page').textContent).toBe('Page 1');
    expect(screen.getByTestId('extracted-ocr-text').textContent).toContain('గోదావరి బ్యారేజీ ఆధునీకరణ');
    expect(screen.getByTestId('geo-badge-geo-1')).toBeDefined();
  });

  it('updates zoom level on Zoom In, Zoom Out, and Reset clicks', async () => {
    render(<SideBySideClippingViewer clipping={sampleClipping1} />);

    const zoomInBtn = screen.getByTestId('zoom-in-btn');
    const zoomOutBtn = screen.getByTestId('zoom-out-btn');
    const zoomResetBtn = screen.getByTestId('zoom-reset-btn');
    const zoomLevel = screen.getByTestId('zoom-level');
    const image = screen.getByTestId('clipping-image') as HTMLImageElement;

    // Initial 100%
    expect(zoomLevel.textContent).toBe('100%');
    expect(image.style.transform).toBe('scale(1)');

    // Zoom In -> 125%
    await act(async () => {
      fireEvent.click(zoomInBtn);
    });
    expect(zoomLevel.textContent).toBe('125%');
    expect(image.style.transform).toBe('scale(1.25)');

    // Zoom In -> 150%
    await act(async () => {
      fireEvent.click(zoomInBtn);
    });
    expect(zoomLevel.textContent).toBe('150%');

    // Zoom Out -> 125%
    await act(async () => {
      fireEvent.click(zoomOutBtn);
    });
    expect(zoomLevel.textContent).toBe('125%');

    // Reset -> 100%
    await act(async () => {
      fireEvent.click(zoomResetBtn);
    });
    expect(zoomLevel.textContent).toBe('100%');
    expect(image.style.transform).toBe('scale(1)');
  });

  it('calls onClose when close button is clicked', async () => {
    const handleClose = vi.fn();
    render(<SideBySideClippingViewer clipping={sampleClipping1} onClose={handleClose} />);

    const closeBtn = screen.getByTestId('close-viewer-btn');
    await act(async () => {
      fireEvent.click(closeBtn);
    });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});

describe('NewspaperArchivePage Integration & Filtering', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams = new URLSearchParams();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders archive page and fetches initial newspaper clippings', async () => {
    vi.spyOn(apiClient, 'apiFetch').mockImplementation(async (endpoint: string) => {
      if (endpoint.startsWith('/api/v1/newspapers')) {
        const res: NewspaperListResponse = {
          items: [sampleClipping1, sampleClipping2],
          total: 2,
          page: 1,
          page_size: 20,
          total_pages: 1,
        };
        return res;
      }
      return {};
    });

    render(<NewspaperArchivePage />);

    expect(screen.getByTestId('archive-title').textContent).toBe('Newspaper Archive');
    expect(screen.getByTestId('newspaper-filter-bar')).toBeDefined();

    await waitFor(() => {
      expect(screen.getByTestId('clipping-card-clipping-1')).toBeDefined();
      expect(screen.getByTestId('clipping-card-clipping-2')).toBeDefined();
      expect(screen.getByTestId('total-clippings-count').textContent).toContain('2');
    });
  });

  it('updates query parameters and refetches when filter controls change', async () => {
    let capturedQuery = '';
    vi.spyOn(apiClient, 'apiFetch').mockImplementation(async (endpoint: string) => {
      if (endpoint.startsWith('/api/v1/newspapers')) {
        capturedQuery = endpoint;
        const res: NewspaperListResponse = {
          items: [sampleClipping1],
          total: 1,
          page: 1,
          page_size: 20,
          total_pages: 1,
        };
        return res;
      }
      return {};
    });

    render(<NewspaperArchivePage />);

    await waitFor(() => {
      expect(screen.getByTestId('clipping-card-clipping-1')).toBeDefined();
    });

    // Enter Newspaper Name
    const nameInput = screen.getByTestId('filter-newspaper-name');
    await act(async () => {
      fireEvent.change(nameInput, { target: { value: 'Eenadu' } });
    });

    // Enter Edition
    const editionInput = screen.getByTestId('filter-edition');
    await act(async () => {
      fireEvent.change(editionInput, { target: { value: 'Amaravati' } });
    });

    // Enter Date From & Date To
    const dateFromInput = screen.getByTestId('filter-date-from');
    const dateToInput = screen.getByTestId('filter-date-to');
    await act(async () => {
      fireEvent.change(dateFromInput, { target: { value: '2024-03-01' } });
      fireEvent.change(dateToInput, { target: { value: '2024-03-31' } });
    });

    // Verify router.push was called with updated query string
    expect(mockPush).toHaveBeenCalled();
    const lastPushCall = mockPush.mock.calls[mockPush.mock.calls.length - 1][0];
    expect(lastPushCall).toContain('newspaper_name=Eenadu');
    expect(lastPushCall).toContain('edition=Amaravati');
    expect(lastPushCall).toContain('date_from=2024-03-01');
    expect(lastPushCall).toContain('date_to=2024-03-31');

    // Click Filter button to submit
    const submitBtn = screen.getByTestId('apply-filters-btn');
    await act(async () => {
      fireEvent.click(submitBtn);
    });

    await waitFor(() => {
      expect(capturedQuery).toContain('newspaper_name=Eenadu');
      expect(capturedQuery).toContain('edition=Amaravati');
    });
  });

  it('opens side-by-side viewer when clicking View Side-by-Side on a clipping card', async () => {
    vi.spyOn(apiClient, 'apiFetch').mockImplementation(async (endpoint: string) => {
      if (endpoint.startsWith('/api/v1/newspapers')) {
        const res: NewspaperListResponse = {
          items: [sampleClipping1],
          total: 1,
          page: 1,
          page_size: 20,
          total_pages: 1,
        };
        return res;
      }
      return {};
    });

    render(<NewspaperArchivePage />);

    await waitFor(() => {
      expect(screen.getByTestId('select-clipping-clipping-1')).toBeDefined();
    });

    // Side-by-side viewer is not visible initially
    expect(screen.queryByTestId('side-by-side-viewer')).toBeNull();

    // Click View Side-by-Side
    const selectBtn = screen.getByTestId('select-clipping-clipping-1');
    await act(async () => {
      fireEvent.click(selectBtn);
    });

    // Side-by-side viewer is now rendered
    expect(screen.getByTestId('side-by-side-viewer')).toBeDefined();
    expect(screen.getByTestId('clipping-headline').textContent).toBe(sampleClipping1.headline);
    expect(screen.getByTestId('clipping-image')).toBeDefined();
    expect(screen.getByTestId('extracted-ocr-text')).toBeDefined();

    // Closing the viewer removes it
    const closeBtn = screen.getByTestId('close-viewer-btn');
    await act(async () => {
      fireEvent.click(closeBtn);
    });
    expect(screen.queryByTestId('side-by-side-viewer')).toBeNull();
  });

  it('renders empty state message when no clippings match filter criteria', async () => {
    vi.spyOn(apiClient, 'apiFetch').mockImplementation(async (endpoint: string) => {
      if (endpoint.startsWith('/api/v1/newspapers')) {
        const res: NewspaperListResponse = {
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
          total_pages: 0,
        };
        return res;
      }
      return {};
    });

    render(<NewspaperArchivePage />);

    await waitFor(() => {
      expect(screen.getByTestId('empty-clippings-message')).toBeDefined();
      expect(screen.getByText('No newspaper clippings found')).toBeDefined();
    });
  });
});
