export enum UserRole {
  SUPER_ADMIN = 'super_admin',
  ADMIN = 'admin',
  RESEARCHER = 'researcher',
  REVIEWER = 'reviewer',
  CONTRIBUTOR = 'contributor',
  VIEWER = 'viewer',
}

export enum AssetType {
  GOVERNMENT_DOCUMENT = 'government_document',
  NEWSPAPER_CLIPPING = 'newspaper_clipping',
  ONLINE_NEWS_SOCIAL = 'online_news_social',
  VIDEO_AUDIO = 'video_audio',
  IMAGE_INFOGRAPHIC = 'image_infographic',
  RESEARCH_MATERIAL = 'research_material',
  // Legacy aliases
  DOCUMENT = 'document',
  IMAGE = 'image',
  VIDEO = 'video',
  AUDIO = 'audio',
  PRESS_CLIPPING = 'press_clipping',
  SOCIAL_ARCHIVE = 'social_archive',
}

export enum VerificationStatus {
  UNPROCESSED = 'unprocessed',
  PENDING_REVIEW = 'pending_review',
  VERIFIED = 'verified',
  FLAGGED = 'flagged',
  REJECTED = 'rejected',
}

export enum GeoTier {
  INDIA = 'india',
  STATE = 'state',
  DISTRICT = 'district',
  PARLIAMENTARY_CONSTITUENCY = 'parliamentary_constituency',
  ASSEMBLY_CONSTITUENCY = 'assembly_constituency',
  MANDAL = 'mandal',
  VILLAGE = 'village',
  MUNICIPAL_CORPORATION = 'municipal_corporation',
  MUNICIPALITY = 'municipality',
  WARD = 'ward',
}

export interface GeoEntity {
  id: string;
  name: string;
  telugu_name?: string | null;
  tier: GeoTier | string;
  code?: string | null;
  is_historical?: boolean;
  matched_alias?: string | null;
}

export interface NewspaperClippingItem {
  id: string;
  headline: string;
  newspaper_name: string;
  edition?: string | null;
  publication_date: string;
  page_number?: number | string | null;
  extracted_text?: string | null;
  geo_tags: GeoEntity[];
  preview_url: string;
  created_at: string;
}

export interface NewspaperListResponse {
  items: NewspaperClippingItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SearchResultItem {
  id: string;
  title: string;
  snippet: string;
  score: number;
  asset_type: AssetType | string;
  headline?: string | null;
  highlighted_snippet?: string | null;
  go_number?: string | null;
  publication_date?: string | null;
  source_name?: string | null;
  preview_url?: string | null;
  geo_tags: GeoEntity[];
}

export interface SearchPaginationResponse {
  items: SearchResultItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export enum RelationType {
  AMENDS = 'amends',
  SUPERSEDES = 'supersedes',
  CLARIFIES = 'clarifies',
  RELATED = 'related',
}

export enum CopyrightFlag {
  PUBLIC_DOMAIN = 'public_domain',
  INTERNAL_RESEARCH_ONLY = 'internal_research_only',
  RESTRICTED_COPYRIGHT = 'restricted_copyright',
}

export interface UploaderSummary {
  id: string;
  full_name?: string | null;
  email: string;
  role: UserRole;
}

export interface RelationshipSummary {
  id: string;
  relation_type: RelationType | string;
  direction: 'outgoing' | 'incoming' | string;
  source_asset_id: string;
  target_asset_id: string;
  related_asset_id: string;
  related_asset_title: string;
  related_asset_type: AssetType | string;
  created_at: string;
}

export interface AssetDetailResponse {
  id: string;
  title: string;
  asset_type: AssetType | string;
  primary_language: string;
  source_name?: string | null;
  source_url?: string | null;
  r2_object_key: string;
  file_sha256: string;
  mime_type: string;
  file_size_bytes: number;
  go_number?: string | null;
  copyright_flag: CopyrightFlag | string;
  is_public_record: boolean;
  extracted_text?: string | null;
  english_summary?: string | null;
  tenglish_keywords: string[];
  subject_tags: string[];
  dynamic_metadata: Record<string, any>;
  status: string;
  verification_status: VerificationStatus | string;
  uploaded_by?: string | null;
  uploader?: UploaderSummary | null;
  geo_entities: GeoEntity[];
  relationships: RelationshipSummary[];
  created_at: string;
  updated_at: string;
}

export interface DownloadUrlResponse {
  download_url: string;
  expires_in: number;
}

export * from './schemas/assetMetadata';
