import { describe, it, expect } from 'vitest';
import {
  AssetType,
  validateDynamicMetadata,
  GovernmentDocumentMetadataSchema,
  NewspaperClippingMetadataSchema,
  OnlineNewsSocialMetadataSchema,
  VideoAudioMetadataSchema,
  ImageInfographicMetadataSchema,
  ResearchMaterialMetadataSchema,
} from '@jsp/shared';

describe('Asset Dynamic Metadata Zod Schemas', () => {
  describe('GovernmentDocumentMetadataSchema', () => {
    it('validates minimal required fields', () => {
      const data = {
        go_number: 'GO-MS-12',
        issuing_department: 'Water Resources',
        date_of_issue: '2024-02-10',
        subject: 'Polavaram Project Canals Maintenance',
        state: 'Andhra Pradesh',
      };
      const parsed = GovernmentDocumentMetadataSchema.parse(data);
      expect(parsed.go_number).toBe('GO-MS-12');
      expect(parsed.district_local_body).toBeUndefined();
    });

    it('validates full schema with optional fields', () => {
      const data = {
        go_number: 'GO-MS-12',
        issuing_department: 'Water Resources',
        date_of_issue: '2024-02-10',
        subject: 'Polavaram Project Canals Maintenance',
        state: 'Andhra Pradesh',
        district_local_body: 'Eluru',
        related_scheme: 'Irrigation Modernization',
        effective_date: '2024-03-01',
        supersedes_go_number: 'GO-MS-05',
      };
      const res = validateDynamicMetadata(AssetType.GOVERNMENT_DOCUMENT, data);
      expect(res.success).toBe(true);
      if (res.success) {
        expect(res.data).toMatchObject({
          go_number: 'GO-MS-12',
          district_local_body: 'Eluru',
        });
      }
    });

    it('fails when required fields are missing', () => {
      const res = validateDynamicMetadata(AssetType.GOVERNMENT_DOCUMENT, {
        go_number: 'GO-1',
      });
      expect(res.success).toBe(false);
      if (!res.success) {
        expect(res.errors.issuing_department).toBeDefined();
        expect(res.errors.date_of_issue).toBeDefined();
        expect(res.errors.subject).toBeDefined();
        expect(res.errors.state).toBeDefined();
      }
    });
  });

  describe('NewspaperClippingMetadataSchema', () => {
    it('validates valid newspaper metadata', () => {
      const data = {
        newspaper_name: 'Andhra Jyothy',
        publication_date: '2024-01-20',
        headline: 'Varahi Sabha Draws Massive Crowds in Godavari Districts',
        edition: 'Kakinada',
        page_number: 1,
        column_byline: 'Staff Reporter',
      };
      const direct = NewspaperClippingMetadataSchema.parse(data);
      expect(direct.newspaper_name).toBe('Andhra Jyothy');
      const res = validateDynamicMetadata(AssetType.NEWSPAPER_CLIPPING, data);
      expect(res.success).toBe(true);
    });

    it('fails missing required fields', () => {
      const res = validateDynamicMetadata(AssetType.NEWSPAPER_CLIPPING, {
        newspaper_name: 'Sakshi',
      });
      expect(res.success).toBe(false);
      if (!res.success) {
        expect(res.errors.headline).toBeDefined();
        expect(res.errors.publication_date).toBeDefined();
      }
    });
  });

  describe('OnlineNewsSocialMetadataSchema', () => {
    it('validates valid online news / social data', () => {
      const data = {
        platform_publisher: 'Twitter/X',
        source_url: 'https://x.com/JanaSenaParty/status/123456',
        published_date: '2024-04-01',
        author_handle: '@JanaSenaParty',
        key_quote: 'People first, politics next.',
      };
      const direct = OnlineNewsSocialMetadataSchema.parse(data);
      expect(direct.platform_publisher).toBe('Twitter/X');
      const res = validateDynamicMetadata(AssetType.ONLINE_NEWS_SOCIAL, data);
      expect(res.success).toBe(true);
    });

    it('fails missing source_url', () => {
      const res = validateDynamicMetadata(AssetType.ONLINE_NEWS_SOCIAL, {
        platform_publisher: 'X',
        published_date: '2024-04-01',
        author_handle: '@test',
      });
      expect(res.success).toBe(false);
      if (!res.success) {
        expect(res.errors.source_url).toBeDefined();
      }
    });
  });

  describe('VideoAudioMetadataSchema', () => {
    it('validates video / audio metadata', () => {
      const data = {
        source_channel_event: 'Press Conference Amaravati',
        recording_date: '2024-05-10',
        speakers: ['Pawan Kalyan'],
        duration_sec: 2400,
        venue: 'Mangalagiri',
        key_timestamps: { '05:00': 'Key declaration on farmers welfare' },
      };
      const direct = VideoAudioMetadataSchema.parse(data);
      expect(direct.source_channel_event).toBe('Press Conference Amaravati');
      const res = validateDynamicMetadata(AssetType.VIDEO_AUDIO, data);
      expect(res.success).toBe(true);
    });

    it('fails when speakers array is empty', () => {
      const res = validateDynamicMetadata(AssetType.VIDEO_AUDIO, {
        source_channel_event: 'Speech',
        recording_date: '2024-05-10',
        speakers: [],
      });
      expect(res.success).toBe(false);
      if (!res.success) {
        expect(res.errors.speakers).toBeDefined();
      }
    });
  });

  describe('ImageInfographicMetadataSchema', () => {
    it('validates image / infographic metadata', () => {
      const data = {
        event_subject: 'Pithapuram public rally',
        capture_date: '2024-04-15',
        credit_source: 'Media Bureau',
        people_depicted: ['Pawan Kalyan'],
        caption: 'Wave of supporters',
      };
      const direct = ImageInfographicMetadataSchema.parse(data);
      expect(direct.event_subject).toBe('Pithapuram public rally');
      const res = validateDynamicMetadata(AssetType.IMAGE_INFOGRAPHIC, data);
      expect(res.success).toBe(true);
    });

    it('fails missing credit_source', () => {
      const res = validateDynamicMetadata(AssetType.IMAGE_INFOGRAPHIC, {
        event_subject: 'Rally',
        capture_date: '2024-04-15',
      });
      expect(res.success).toBe(false);
      if (!res.success) {
        expect(res.errors.credit_source).toBeDefined();
      }
    });
  });

  describe('ResearchMaterialMetadataSchema', () => {
    it('validates research material metadata', () => {
      const data = {
        document_title: 'Socio-Economic Survey of North Andhra Fisherfolk',
        authoring_body: 'JSP Coastal Communities Cell',
        publication_date: '2023-11-15',
        sample_size_methodology: 'Surveys of 45 fishing hamlets across 3 districts',
        executive_summary: 'Livelihood vulnerability due to erratic harbor infrastructure',
        key_metrics: { hamlets_surveyed: 45, average_household_debt: 180000 },
      };
      const direct = ResearchMaterialMetadataSchema.parse(data);
      expect(direct.document_title).toBe('Socio-Economic Survey of North Andhra Fisherfolk');
      const res = validateDynamicMetadata(AssetType.RESEARCH_MATERIAL, data);
      expect(res.success).toBe(true);
    });

    it('fails missing authoring_body', () => {
      const res = validateDynamicMetadata(AssetType.RESEARCH_MATERIAL, {
        document_title: 'White Paper',
        publication_date: '2023-11-15',
      });
      expect(res.success).toBe(false);
      if (!res.success) {
        expect(res.errors.authoring_body).toBeDefined();
      }
    });
  });

  describe('Unsupported asset type handling', () => {
    it('returns error when asset type is unrecognized', () => {
      const res = validateDynamicMetadata('unknown_type', {});
      expect(res.success).toBe(false);
      if (!res.success) {
        expect(res.errors._general).toContain('Unsupported asset_type');
      }
    });
  });
});
