import { z } from 'zod';
import { AssetType } from '../index';

// ============================================================================
// 1. Government Document Schema
// ============================================================================
export const GovernmentDocumentMetadataSchema = z.object({
  go_number: z.string().min(1, 'GO number is required'),
  issuing_department: z.string().min(1, 'Issuing department is required'),
  date_of_issue: z.string().min(1, 'Date of issue is required'),
  subject: z.string().min(1, 'Subject is required'),
  state: z.string().min(1, 'State is required'),
  district_local_body: z.string().nullable().optional(),
  related_scheme: z.string().nullable().optional(),
  effective_date: z.string().nullable().optional(),
  supersedes_go_number: z.string().nullable().optional(),
});
export type GovernmentDocumentMetadata = z.infer<typeof GovernmentDocumentMetadataSchema>;

// ============================================================================
// 2. Newspaper Clipping Schema
// ============================================================================
export const NewspaperClippingMetadataSchema = z.object({
  newspaper_name: z.string().min(1, 'Newspaper name is required'),
  publication_date: z.string().min(1, 'Publication date is required'),
  headline: z.string().min(1, 'Headline is required'),
  edition: z.string().nullable().optional(),
  page_number: z.union([z.number(), z.string()]).nullable().optional(),
  column_byline: z.string().nullable().optional(),
});
export type NewspaperClippingMetadata = z.infer<typeof NewspaperClippingMetadataSchema>;

// ============================================================================
// 3. Online News & Social Archive Schema
// ============================================================================
export const OnlineNewsSocialMetadataSchema = z.object({
  platform_publisher: z.string().min(1, 'Platform/publisher is required'),
  source_url: z.string().min(1, 'Source URL is required'),
  published_date: z.string().min(1, 'Published date is required'),
  author_handle: z.string().min(1, 'Author/handle is required'),
  key_quote: z.string().nullable().optional(),
});
export type OnlineNewsSocialMetadata = z.infer<typeof OnlineNewsSocialMetadataSchema>;

// ============================================================================
// 4. Video & Audio Schema
// ============================================================================
export const VideoAudioMetadataSchema = z.object({
  source_channel_event: z.string().min(1, 'Source channel/event is required'),
  recording_date: z.string().min(1, 'Recording date is required'),
  speakers: z.array(z.string()).min(1, 'At least one speaker is required'),
  duration_sec: z.number().nullable().optional(),
  venue: z.string().nullable().optional(),
  key_timestamps: z.record(z.string(), z.any()).nullable().optional(),
});
export type VideoAudioMetadata = z.infer<typeof VideoAudioMetadataSchema>;

// ============================================================================
// 5. Image & Infographic Schema
// ============================================================================
export const ImageInfographicMetadataSchema = z.object({
  event_subject: z.string().min(1, 'Event/subject is required'),
  capture_date: z.string().min(1, 'Capture date is required'),
  credit_source: z.string().min(1, 'Credit/source is required'),
  people_depicted: z.array(z.string()).nullable().optional(),
  caption: z.string().nullable().optional(),
  usage_rights: z.string().nullable().optional(),
});
export type ImageInfographicMetadata = z.infer<typeof ImageInfographicMetadataSchema>;

// ============================================================================
// 6. Research Material Schema
// ============================================================================
export const ResearchMaterialMetadataSchema = z.object({
  document_title: z.string().min(1, 'Document title is required'),
  authoring_body: z.string().min(1, 'Authoring body is required'),
  publication_date: z.string().min(1, 'Publication date is required'),
  sample_size_methodology: z.string().nullable().optional(),
  executive_summary: z.string().nullable().optional(),
  key_metrics: z.record(z.string(), z.any()).nullable().optional(),
});
export type ResearchMaterialMetadata = z.infer<typeof ResearchMaterialMetadataSchema>;

// Dynamic metadata union type
export type DynamicMetadata =
  | GovernmentDocumentMetadata
  | NewspaperClippingMetadata
  | OnlineNewsSocialMetadata
  | VideoAudioMetadata
  | ImageInfographicMetadata
  | ResearchMaterialMetadata;

export const ASSET_TYPE_SCHEMA_MAP = {
  [AssetType.GOVERNMENT_DOCUMENT]: GovernmentDocumentMetadataSchema,
  [AssetType.NEWSPAPER_CLIPPING]: NewspaperClippingMetadataSchema,
  [AssetType.ONLINE_NEWS_SOCIAL]: OnlineNewsSocialMetadataSchema,
  [AssetType.VIDEO_AUDIO]: VideoAudioMetadataSchema,
  [AssetType.IMAGE_INFOGRAPHIC]: ImageInfographicMetadataSchema,
  [AssetType.RESEARCH_MATERIAL]: ResearchMaterialMetadataSchema,
} as const;

export function validateDynamicMetadata(
  assetType: AssetType | string,
  payload: unknown
): { success: true; data: DynamicMetadata } | { success: false; errors: Record<string, string> } {
  const schema = (ASSET_TYPE_SCHEMA_MAP as Record<string, z.ZodTypeAny>)[assetType];
  if (!schema) {
    return {
      success: false,
      errors: { _general: `Unsupported asset_type: '${assetType}'` },
    };
  }

  const result = schema.safeParse(payload);
  if (!result.success) {
    const fieldErrors: Record<string, string> = {};
    for (const issue of result.error.issues) {
      const field = issue.path.join('.') || '_general';
      fieldErrors[field] = issue.message;
    }
    return { success: false, errors: fieldErrors };
  }

  return { success: true, data: result.data as DynamicMetadata };
}
