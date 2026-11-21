import React from 'react';
import { UserRole } from '@jsp/shared';
import { AppShell } from '@/components/AppShell';

export default function HomePage() {
  return (
    <AppShell role={UserRole.VIEWER} userEmail="guest@jsp.internal">
      <h1>JSP Digital Intelligence Platform</h1>
      <p>Welcome to the private intelligence repository and analytical workspace.</p>
    </AppShell>
  );
}
