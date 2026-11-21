import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { AssetType } from '@jsp/shared';
import * as apiClient from '@/lib/api-client';
import UploadPage from '@/app/repository/upload/page';
import { DuplicateWarningBanner } from '@/components/upload/DuplicateWarningBanner';
import { DynamicMetadataFields } from '@/components/upload/DynamicMetadataFields';

describe('Upload Page & Components', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('DynamicMetadataFields Component', () => {
    it('switches and displays only configured fields for government_document', () => {
      render(
        <DynamicMetadataFields
          assetType={AssetType.GOVERNMENT_DOCUMENT}
          values={{}}
          errors={{}}
          onChange={vi.fn()}
        />
      );

      expect(screen.getByTestId('fields-government-document')).toBeDefined();
      expect(screen.getByTestId('input-go_number')).toBeDefined();
      expect(screen.getByTestId('input-issuing_department')).toBeDefined();
      expect(screen.getByTestId('input-date_of_issue')).toBeDefined();
      expect(screen.getByTestId('input-subject')).toBeDefined();
      expect(screen.getByTestId('input-state')).toBeDefined();
      expect(screen.getByTestId('input-district_local_body')).toBeDefined();
      expect(screen.getByTestId('input-supersedes_go_number')).toBeDefined();

      // Ensure other types' fields are not displayed
      expect(screen.queryByTestId('fields-newspaper-clipping')).toBeNull();
      expect(screen.queryByTestId('fields-online-news-social')).toBeNull();
    });

    it('switches and displays only configured fields for newspaper_clipping', () => {
      render(
        <DynamicMetadataFields
          assetType={AssetType.NEWSPAPER_CLIPPING}
          values={{}}
          errors={{}}
          onChange={vi.fn()}
        />
      );

      expect(screen.getByTestId('fields-newspaper-clipping')).toBeDefined();
      expect(screen.getByTestId('input-newspaper_name')).toBeDefined();
      expect(screen.getByTestId('input-publication_date')).toBeDefined();
      expect(screen.getByTestId('input-headline')).toBeDefined();
      expect(screen.getByTestId('input-edition')).toBeDefined();

      expect(screen.queryByTestId('fields-government-document')).toBeNull();
      expect(screen.queryByTestId('fields-video-audio')).toBeNull();
    });

    it('switches and displays only configured fields for online_news_social', () => {
      render(
        <DynamicMetadataFields
          assetType={AssetType.ONLINE_NEWS_SOCIAL}
          values={{}}
          errors={{}}
          onChange={vi.fn()}
        />
      );

      expect(screen.getByTestId('fields-online-news-social')).toBeDefined();
      expect(screen.getByTestId('input-platform_publisher')).toBeDefined();
      expect(screen.getByTestId('input-source_url')).toBeDefined();
      expect(screen.getByTestId('input-author_handle')).toBeDefined();
      expect(screen.getByTestId('input-key_quote')).toBeDefined();

      expect(screen.queryByTestId('fields-newspaper-clipping')).toBeNull();
    });

    it('switches and displays only configured fields for video_audio', () => {
      render(
        <DynamicMetadataFields
          assetType={AssetType.VIDEO_AUDIO}
          values={{}}
          errors={{}}
          onChange={vi.fn()}
        />
      );

      expect(screen.getByTestId('fields-video-audio')).toBeDefined();
      expect(screen.getByTestId('input-source_channel_event')).toBeDefined();
      expect(screen.getByTestId('input-recording_date')).toBeDefined();
      expect(screen.getByTestId('input-speakers')).toBeDefined();
      expect(screen.getByTestId('input-duration_sec')).toBeDefined();
      expect(screen.getByTestId('input-venue')).toBeDefined();
    });

    it('switches and displays only configured fields for image_infographic', () => {
      render(
        <DynamicMetadataFields
          assetType={AssetType.IMAGE_INFOGRAPHIC}
          values={{}}
          errors={{}}
          onChange={vi.fn()}
        />
      );

      expect(screen.getByTestId('fields-image-infographic')).toBeDefined();
      expect(screen.getByTestId('input-event_subject')).toBeDefined();
      expect(screen.getByTestId('input-capture_date')).toBeDefined();
      expect(screen.getByTestId('input-credit_source')).toBeDefined();
      expect(screen.getByTestId('input-people_depicted')).toBeDefined();
      expect(screen.getByTestId('input-caption')).toBeDefined();
    });

    it('switches and displays only configured fields for research_material', () => {
      render(
        <DynamicMetadataFields
          assetType={AssetType.RESEARCH_MATERIAL}
          values={{}}
          errors={{}}
          onChange={vi.fn()}
        />
      );

      expect(screen.getByTestId('fields-research-material')).toBeDefined();
      expect(screen.getByTestId('input-document_title')).toBeDefined();
      expect(screen.getByTestId('input-authoring_body')).toBeDefined();
      expect(screen.getByTestId('input-publication_date')).toBeDefined();
      expect(screen.getByTestId('input-sample_size_methodology')).toBeDefined();
      expect(screen.getByTestId('input-executive_summary')).toBeDefined();
    });

    it('renders inline error messages for invalid fields', () => {
      render(
        <DynamicMetadataFields
          assetType={AssetType.GOVERNMENT_DOCUMENT}
          values={{}}
          errors={{ go_number: 'GO number is required', issuing_department: 'Department is required' }}
          onChange={vi.fn()}
        />
      );

      expect(screen.getByTestId('error-go_number').textContent).toBe('GO number is required');
      expect(screen.getByTestId('error-issuing_department').textContent).toBe('Department is required');
    });
  });

  describe('DuplicateWarningBanner Component', () => {
    it('renders visible warning banner with clickable link to existing record', () => {
      const matches = [
        {
          id: 'asset-123',
          title: 'Existing Polavaram GO',
          asset_type: 'government_document',
          match_reason: 'go_number_match',
        },
      ];

      render(<DuplicateWarningBanner matches={matches} />);

      const banner = screen.getByTestId('duplicate-warning-banner');
      expect(banner).toBeDefined();
      expect(screen.getByText('Existing Polavaram GO')).toBeDefined();

      const link = screen.getByTestId('duplicate-link-asset-123') as HTMLAnchorElement;
      expect(link.getAttribute('href')).toBe('/repository/asset-123');
    });

    it('returns null when there are no matches', () => {
      const { container } = render(<DuplicateWarningBanner matches={[]} />);
      expect(container.firstChild).toBeNull();
    });
  });

  describe('UploadPage Integration', () => {
    it('blocks submission and shows inline validation errors when required fields are missing', async () => {
      const apiFetchSpy = vi.spyOn(apiClient, 'apiFetch');

      render(<UploadPage />);

      const submitBtn = screen.getByTestId('btn-submit-upload');
      await act(async () => {
        fireEvent.click(submitBtn);
      });

      // Assert inline validation errors are displayed
      expect(screen.getByTestId('error-title').textContent).toBe('Asset title is required');
      expect(screen.getByTestId('error-file').textContent).toBe('File upload is required');
      expect(screen.getByTestId('error-go_number')).toBeDefined();
      expect(screen.getByTestId('error-issuing_department')).toBeDefined();

      // Assert network request to create asset was BLOCKED
      expect(apiFetchSpy).not.toHaveBeenCalledWith('/api/v1/assets', expect.anything());
      expect(apiFetchSpy).not.toHaveBeenCalledWith('/api/v1/uploads/presign', expect.anything());
    });

    it('switches asset types and updates form fields dynamically', async () => {
      render(<UploadPage />);

      // Initially Government Document
      expect(screen.getByTestId('fields-government-document')).toBeDefined();

      // Change asset type to Newspaper Clipping
      const select = screen.getByTestId('select-asset-type');
      await act(async () => {
        fireEvent.change(select, { target: { value: AssetType.NEWSPAPER_CLIPPING } });
      });

      expect(screen.getByTestId('fields-newspaper-clipping')).toBeDefined();
      expect(screen.queryByTestId('fields-government-document')).toBeNull();
    });

    it('triggers duplicate check on GO number blur and displays duplicate warning banner', async () => {
      vi.spyOn(apiClient, 'apiFetch').mockResolvedValueOnce({
        is_duplicate: true,
        matches: [
          {
            id: 'asset-existing-99',
            title: 'Previous GO on Land Allotment',
            asset_type: 'government_document',
            match_reason: 'go_number_match',
          },
        ],
      });

      render(<UploadPage />);

      const goInput = screen.getByTestId('input-go_number');
      await act(async () => {
        fireEvent.change(goInput, { target: { value: 'GO-MS-104' } });
        fireEvent.blur(goInput);
      });

      expect(screen.getByTestId('duplicate-warning-banner')).toBeDefined();
      expect(screen.getByText('Previous GO on Land Allotment')).toBeDefined();
      const link = screen.getByTestId('duplicate-link-asset-existing-99') as HTMLAnchorElement;
      expect(link.getAttribute('href')).toBe('/repository/asset-existing-99');
    });

    it('completes happy path upload with presign, direct R2 upload, and asset creation', async () => {
      const apiFetchSpy = vi.spyOn(apiClient, 'apiFetch').mockImplementation(async (endpoint: string) => {
        if (endpoint.includes('/uploads/check-duplicate')) {
          return { is_duplicate: false, matches: [] };
        }
        if (endpoint.includes('/uploads/presign')) {
          return {
            object_key: 'raw/2024/03/abc_file.pdf',
            upload_url: 'https://r2.example.com/upload-presigned-url',
            expires_in: 300,
          };
        }
        if (endpoint.includes('/assets')) {
          return {
            id: 'new-asset-uuid-456',
            title: 'Valid Revenue GO Document',
          };
        }
        return {};
      });

      // Mock global fetch for direct R2 upload
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        status: 200,
      } as Response);

      render(<UploadPage />);

      // Fill in required fields
      const titleInput = screen.getByTestId('input-title');
      const fileInput = screen.getByTestId('input-file');
      const goInput = screen.getByTestId('input-go_number');
      const deptInput = screen.getByTestId('input-issuing_department');
      const dateInput = screen.getByTestId('input-date_of_issue');
      const subjectInput = screen.getByTestId('input-subject');

      const mockFile = new File(['dummy content'], 'test_go.pdf', { type: 'application/pdf' });

      await act(async () => {
        fireEvent.change(titleInput, { target: { value: 'Valid Revenue GO Document' } });
        fireEvent.change(fileInput, { target: { files: [mockFile] } });
        fireEvent.change(goInput, { target: { value: 'GO-MS-104' } });
        fireEvent.change(deptInput, { target: { value: 'Revenue Department' } });
        fireEvent.change(dateInput, { target: { value: '2024-03-01' } });
        fireEvent.change(subjectInput, { target: { value: 'Land regularisation order' } });
      });

      const submitBtn = screen.getByTestId('btn-submit-upload');
      await act(async () => {
        fireEvent.click(submitBtn);
      });

      // Verify presign was called
      expect(apiFetchSpy).toHaveBeenCalledWith(
        '/api/v1/uploads/presign',
        expect.objectContaining({ method: 'POST' })
      );

      // Verify direct R2 PUT upload was called
      expect(fetchSpy).toHaveBeenCalledWith(
        'https://r2.example.com/upload-presigned-url',
        expect.objectContaining({ method: 'PUT' })
      );

      // Verify asset creation was called
      expect(apiFetchSpy).toHaveBeenCalledWith(
        '/api/v1/assets',
        expect.objectContaining({ method: 'POST' })
      );

      // Verify success banner is rendered
      expect(screen.getByTestId('upload-success-banner')).toBeDefined();
      expect(screen.getByText(/Asset Uploaded Successfully!/)).toBeDefined();
    });
  });
});
