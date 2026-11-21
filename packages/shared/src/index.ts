export enum UserRole {
  SUPER_ADMIN = 'super_admin',
  ADMIN = 'admin',
  RESEARCHER = 'researcher',
  REVIEWER = 'reviewer',
  CONTRIBUTOR = 'contributor',
  VIEWER = 'viewer',
}

export enum AssetType {
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
