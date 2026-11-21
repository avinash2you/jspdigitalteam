import React from 'react';
import { SignIn } from '@clerk/nextjs';

export default function SignInPage() {
  return (
    <div
      style={{
        display: 'flex',
        minHeight: '100vh',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#0f172a',
        padding: '2rem',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <div style={{ marginBottom: '1.5rem', textAlign: 'center', maxWidth: '420px' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#f87171', margin: 0 }}>
          JSP Digital Intelligence Platform
        </h1>
        <p style={{ fontSize: '0.875rem', color: '#94a3b8', marginTop: '0.5rem' }}>
          This portal is invite-only. Public self-registration is strictly disabled. Contact an administrator to receive an invitation.
        </p>
      </div>

      <SignIn
        routing="path"
        path="/sign-in"
        signUpUrl=""
      />
    </div>
  );
}
