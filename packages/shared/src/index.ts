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

export * from './schemas/assetMetadata';
