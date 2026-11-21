import React from 'react';
import { UserRole } from '@jsp/shared';

export default function HomePage() {
  return (
    <main style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif' }}>
      <h1>JSP Digital Intelligence Platform</h1>
      <p>Default Role: {UserRole.VIEWER}</p>
    </main>
  );
}
