import { describe, it, expect } from 'vitest';
import { UserRole, AssetType, VerificationStatus } from '@jsp/shared';

describe('Web App Skeletons & Enums', () => {
  it('loads shared enums correctly in web context', () => {
    expect(UserRole.SUPER_ADMIN).toBe('super_admin');
    expect(AssetType.DOCUMENT).toBe('document');
    expect(VerificationStatus.VERIFIED).toBe('verified');
  });
});
