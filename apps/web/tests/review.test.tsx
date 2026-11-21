import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import { AssetType } from '@jsp/shared';
import * as apiClient from '@/lib/api-client';
import { ExtractionReviewPanel } from '@/components/upload/ExtractionReviewPanel';

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

describe('ExtractionReviewPanel Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders non-public record banner explaining free-tier AI skip while allowing editing & publishing', async () => {
    const assetId = 'non-pub-asset-123';
    vi.spyOn(apiClient, 'apiFetch').mockImplementation(async (endpoint: string) => {
      if (endpoint === `/api/v1/assets/${assetId}`) {
        return {
          id: assetId,
          title: 'Confidential Internal Review Doc',
          asset_type: AssetType.GOVERNMENT_DOCUMENT,
          primary_language: 'telugu',
          is_public_record: false,
          status: 'pending_review',
          extracted_text: 'Raw OCR text from confidential document without AI processing.',
          english_summary: '',
          tenglish_keywords: [],
          dynamic_metadata: {
            go_number: 'GO-MS-999',
            issuing_department: 'Confidential Cell',
            date_of_issue: '2024-03-01',
            subject: 'Confidential Land Survey',
            state: 'Andhra Pradesh',
          },
          geo_entities: [],
        };
      }
      if (endpoint === `/api/v1/assets/${assetId}/publish`) {
        return { id: assetId, status: 'published' };
      }
      return {};
    });

    render(<ExtractionReviewPanel assetId={assetId} />);

    // Wait for asset details to load
    await waitFor(() => {
      expect(screen.queryByTestId('loading-indicator')).toBeNull();
    });

    // Verify non-public record banner is displayed
    const banner = screen.getByTestId('non-public-ai-skipped-banner');
    expect(banner).toBeDefined();
    expect(banner.textContent).toContain('Confidential Record — Free-Tier AI Extraction Skipped');

    // Verify user can edit the fields
    const ocrTextarea = screen.getByTestId('textarea-extracted-text') as HTMLTextAreaElement;
    expect(ocrTextarea.value).toBe('Raw OCR text from confidential document without AI processing.');

    const summaryTextarea = screen.getByTestId('textarea-english-summary') as HTMLTextAreaElement;
    await act(async () => {
      fireEvent.change(summaryTextarea, { target: { value: 'Manually authored English summary.' } });
    });
    expect(summaryTextarea.value).toBe('Manually authored English summary.');

    // Publish
    const publishBtn = screen.getByTestId('btn-approve-publish');
    await act(async () => {
      fireEvent.click(publishBtn);
    });

    // Verify publish was called
    expect(apiClient.apiFetch).toHaveBeenCalledWith(
      `/api/v1/assets/${assetId}/publish`,
      expect.objectContaining({
        method: 'POST',
      })
    );

    // Verify publish success banner is rendered
    expect(screen.getByTestId('publish-success-banner')).toBeDefined();
  });

  it('allows editing extracted text and pre-filled metadata before clicking Approve & Publish', async () => {
    const assetId = 'pub-asset-456';
    const apiFetchSpy = vi.spyOn(apiClient, 'apiFetch').mockImplementation(async (endpoint: string) => {
      if (endpoint === `/api/v1/assets/${assetId}`) {
        return {
          id: assetId,
          title: 'Public Polavaram Project Order',
          asset_type: AssetType.GOVERNMENT_DOCUMENT,
          primary_language: 'telugu',
          is_public_record: true,
          status: 'pending_review',
          extracted_text: 'Initial OCR Text for Polavaram works.',
          english_summary: 'AI Generated Summary.',
          tenglish_keywords: ['polavaram', 'rythu'],
          dynamic_metadata: {
            go_number: 'GO-MS-104',
            issuing_department: 'Water Resources',
            date_of_issue: '2024-03-01',
            subject: 'Canal review order',
            state: 'Andhra Pradesh',
          },
          geo_entities: [],
        };
      }
      if (endpoint === `/api/v1/assets/${assetId}/publish`) {
        return { id: assetId, status: 'published' };
      }
      return {};
    });

    render(<ExtractionReviewPanel assetId={assetId} />);

    await waitFor(() => {
      expect(screen.queryByTestId('loading-indicator')).toBeNull();
    });

    // Public record does not display non-public skip banner
    expect(screen.queryByTestId('non-public-ai-skipped-banner')).toBeNull();

    // Edit extracted text
    const ocrTextarea = screen.getByTestId('textarea-extracted-text') as HTMLTextAreaElement;
    await act(async () => {
      fireEvent.change(ocrTextarea, { target: { value: 'Edited and verified human OCR text.' } });
    });

    // Edit metadata subject
    const subjectInput = screen.getByTestId('input-subject') as HTMLTextAreaElement;
    await act(async () => {
      fireEvent.change(subjectInput, { target: { value: 'Approved subject line for Polavaram canals.' } });
    });

    // Submit publish
    const publishBtn = screen.getByTestId('btn-approve-publish');
    await act(async () => {
      fireEvent.click(publishBtn);
    });

    // Verify publish payload contains the edited fields
    expect(apiFetchSpy).toHaveBeenCalledWith(
      `/api/v1/assets/${assetId}/publish`,
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('Edited and verified human OCR text.'),
      })
    );

    expect(screen.getByTestId('publish-success-banner')).toBeDefined();
  });

  it('triggers extraction automatically for newly uploaded draft asset without extracted_text', async () => {
    const assetId = 'draft-asset-789';
    const apiFetchSpy = vi.spyOn(apiClient, 'apiFetch').mockImplementation(async (endpoint: string) => {
      if (endpoint === `/api/v1/assets/${assetId}`) {
        return {
          id: assetId,
          title: 'Brand New Draft GO',
          asset_type: AssetType.GOVERNMENT_DOCUMENT,
          primary_language: 'telugu',
          is_public_record: true,
          status: 'draft',
          extracted_text: null,
          english_summary: null,
          tenglish_keywords: [],
          dynamic_metadata: {
            go_number: 'GO-MS-50',
            issuing_department: 'Revenue',
            date_of_issue: '2024-02-15',
            subject: 'Revenue land allotment',
            state: 'Andhra Pradesh',
          },
          geo_entities: [],
        };
      }
      if (endpoint === `/api/v1/assets/${assetId}/extract`) {
        return {
          asset_id: assetId,
          extracted_text: 'Freshly extracted text via automated trigger.',
          english_summary: 'Automated executive summary.',
          tenglish_keywords: ['revenue', 'bhoomi'],
          suggested_metadata: { district_local_body: 'Krishna' },
          suggested_geo_names: ['Vijayawada'],
          ai_skipped: false,
          ai_notice: null,
          status: 'pending_review',
        };
      }
      return {};
    });

    render(<ExtractionReviewPanel assetId={assetId} />);

    await waitFor(() => {
      expect(screen.queryByTestId('loading-indicator')).toBeNull();
    });

    // Verify extract was automatically invoked on mount
    expect(apiFetchSpy).toHaveBeenCalledWith(
      `/api/v1/assets/${assetId}/extract`,
      expect.objectContaining({ method: 'POST' })
    );

    // Verify extracted text and AI fields were loaded into inputs
    const ocrTextarea = screen.getByTestId('textarea-extracted-text') as HTMLTextAreaElement;
    expect(ocrTextarea.value).toBe('Freshly extracted text via automated trigger.');
  });
});
