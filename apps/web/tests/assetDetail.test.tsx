import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import {
  AssetDetailResponse,
  AssetType,
  CopyrightFlag,
  DownloadUrlResponse,
  RelationType,
  UserRole,
  VerificationStatus,
} from '@jsp/shared';
import * as apiClient from '@/lib/api-client';
import { AssetDetailView } from '@/components/assets/AssetDetailView';
import AssetDetailPage from '@/app/repository/[id]/page';

const mockParams = { id: 'asset-test-123' };
vi.mock('next/navigation', () => ({
  useParams: () => mockParams,
  useRouter: () => ({ push: vi.fn() }),
}));

const sampleAsset: AssetDetailResponse = {
  id: 'asset-test-123',
  title: 'Government Order on Godavari Irrigation Works',
  asset_type: AssetType.GOVERNMENT_DOCUMENT,
  primary_language: 'telugu',
  source_name: 'Water Resources Department',
  source_url: 'https://goir.ap.gov.in/orders/104',
  r2_object_key: 'raw/2024/03/godavari_order.pdf',
  file_sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  mime_type: 'application/pdf',
  file_size_bytes: 1048576, // 1 MB
  go_number: 'GO-MS-104',
  copyright_flag: CopyrightFlag.PUBLIC_DOMAIN,
  is_public_record: true,
  extracted_text: 'గోదావరి బ్యారేజీ ఆధునీకరణ నిధుల విడుదల ఉత్తర్వులు.',
  english_summary: 'Executive order sanctioning funds for Godavari barrage modernization.',
  tenglish_keywords: ['godavari', 'barrage', 'irrigation'],
  subject_tags: ['irrigation', 'budget'],
  dynamic_metadata: {
    go_number: 'GO-MS-104',
    issuing_department: 'Water Resources',
    date_of_issue: '2024-03-05',
    subject: 'Barrage Modernization',
    state: 'Andhra Pradesh',
  },
  status: 'published',
  verification_status: VerificationStatus.VERIFIED,
  uploaded_by: 'user-contributor-1',
  uploader: {
    id: 'user-contributor-1',
    full_name: 'Avinash Contributor',
    email: 'contributor@jsp.internal',
    role: UserRole.CONTRIBUTOR,
  },
  geo_entities: [
    {
      id: 'geo-1',
      name: 'East Godavari',
      telugu_name: 'తూర్పు గోదావరి',
      tier: 'district',
      code: 'AP-EGD',
    },
    {
      id: 'geo-2',
      name: 'Rajamahendravaram',
      telugu_name: 'రాజమహేంద్రవరం',
      tier: 'mandal',
    },
  ],
  relationships: [
    {
      id: 'rel-1',
      relation_type: RelationType.SUPERSEDES,
      direction: 'outgoing',
      source_asset_id: 'asset-test-123',
      target_asset_id: 'asset-target-456',
      related_asset_id: 'asset-target-456',
      related_asset_title: 'Previous Draft Order GO-RT-55',
      related_asset_type: AssetType.GOVERNMENT_DOCUMENT,
      created_at: '2024-03-05T10:00:00Z',
    },
  ],
  created_at: '2024-03-05T09:30:00Z',
  updated_at: '2024-03-05T09:30:00Z',
};

describe('AssetDetailView Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders complete base metadata, contributor attribution, geo tags, and clickable relationship links', () => {
    render(<AssetDetailView asset={sampleAsset} userRole={UserRole.RESEARCHER} />);

    // Title & GO Number
    expect(screen.getByTestId('asset-title').textContent).toBe(sampleAsset.title);
    expect(screen.getByTestId('asset-go-number').textContent).toContain('GO-MS-104');

    // Type, Status, Verification Status Badges
    expect(screen.getByTestId('asset-type').textContent).toBe(sampleAsset.asset_type);
    expect(screen.getByTestId('asset-status').textContent).toBe('published');
    expect(screen.getByTestId('asset-verification-status').textContent).toBe('verified');

    // Contributor Attribution
    expect(screen.getByTestId('uploader-attribution')).toBeDefined();
    expect(screen.getByTestId('uploader-name').textContent).toBe('Avinash Contributor');
    expect(screen.getByTestId('uploader-role').textContent).toBe(UserRole.CONTRIBUTOR);

    // Integrity & Checksum
    expect(screen.getByTestId('asset-sha256').textContent).toBe(sampleAsset.file_sha256);

    // Multi-tier Geographic Chips
    expect(screen.getByTestId('geo-chip-geo-1').textContent).toContain('East Godavari');
    expect(screen.getByTestId('geo-chip-geo-1').textContent).toContain('తూర్పు గోదావరి');
    expect(screen.getByTestId('geo-chip-geo-2').textContent).toContain('Rajamahendravaram');

    // Dynamic Metadata
    expect(screen.getByTestId('dynamic-metadata-section')).toBeDefined();
    expect(screen.getByTestId('meta-val-issuing_department').textContent).toBe('Water Resources');
    expect(screen.getByTestId('meta-val-date_of_issue').textContent).toBe('2024-03-05');

    // Clickable Relationships
    expect(screen.getByTestId('asset-relationships')).toBeDefined();
    const relLink = screen.getByTestId('rel-link-rel-1') as HTMLAnchorElement;
    expect(relLink.getAttribute('href')).toBe('/repository/asset-target-456');
    expect(relLink.textContent).toBe('Previous Draft Order GO-RT-55');

    // OCR Text and Summary
    expect(screen.getByTestId('extracted-text').textContent).toContain('గోదావరి బ్యారేజీ ఆధునీకరణ');
    expect(screen.getByTestId('english-summary').textContent).toContain('Executive order sanctioning');
  });

  it('requests fresh presigned download URL when download button is clicked', async () => {
    const mockWindowOpen = vi.spyOn(window, 'open').mockImplementation(() => null);

    const presignedResponse: DownloadUrlResponse = {
      download_url: 'https://r2.storage.example/signed/godavari_order.pdf?token=fresh_short_lived_token',
      expires_in: 300,
    };

    vi.spyOn(apiClient, 'apiFetch').mockImplementation(async (endpoint: string) => {
      if (endpoint === `/api/v1/assets/${sampleAsset.id}/download-url`) {
        return presignedResponse;
      }
      return {};
    });

    render(<AssetDetailView asset={sampleAsset} userRole={UserRole.RESEARCHER} />);

    const downloadBtn = screen.getByTestId('download-btn');
    expect(downloadBtn).toBeDefined();

    // Click Download Button
    await act(async () => {
      fireEvent.click(downloadBtn);
    });

    // Verifies fresh presigned URL was requested from server
    expect(apiClient.apiFetch).toHaveBeenCalledWith(`/api/v1/assets/${sampleAsset.id}/download-url`);
    expect(mockWindowOpen).toHaveBeenCalledWith(
      presignedResponse.download_url,
      '_blank',
      'noopener,noreferrer'
    );
  });

  it('hides download button when user lacks export access', () => {
    render(<AssetDetailView asset={sampleAsset} canExport={false} />);
    expect(screen.queryByTestId('download-btn')).toBeNull();
  });
});

describe('AssetDetailPage Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches asset details and renders AssetDetailView', async () => {
    vi.spyOn(apiClient, 'apiFetch').mockImplementation(async (endpoint: string) => {
      if (endpoint === `/api/v1/assets/${sampleAsset.id}`) {
        return sampleAsset;
      }
      if (endpoint === `/api/v1/assets/${sampleAsset.id}/download-url`) {
        return { download_url: 'https://presigned.preview.url', expires_in: 300 };
      }
      return {};
    });

    render(<AssetDetailPage />);

    // Initially loading
    expect(screen.getByTestId('asset-loading')).toBeDefined();

    // After fetch completes
    await waitFor(() => {
      expect(screen.queryByTestId('asset-loading')).toBeNull();
      expect(screen.getByTestId('asset-title').textContent).toBe(sampleAsset.title);
      expect(screen.getByTestId('asset-relationships')).toBeDefined();
    });
  });

  it('renders error message when asset fetch fails', async () => {
    vi.spyOn(apiClient, 'apiFetch').mockRejectedValue(new Error('Asset not found in database'));

    render(<AssetDetailPage />);

    await waitFor(() => {
      expect(screen.getByTestId('asset-error')).toBeDefined();
      expect(screen.getByText('Asset not found in database')).toBeDefined();
    });
  });
});
