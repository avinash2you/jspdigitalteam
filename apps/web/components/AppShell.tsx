import React from 'react';
import Link from 'next/link';
import { UserRole } from '@jsp/shared';

export interface AppShellProps {
  role: UserRole;
  userEmail?: string;
  children: React.ReactNode;
}

export function AppShell({ role, userEmail, children }: AppShellProps) {
  const canUpload = [
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.RESEARCHER,
    UserRole.CONTRIBUTOR,
  ].includes(role);

  const canViewAudit = [UserRole.SUPER_ADMIN, UserRole.ADMIN].includes(role);

  return (
    <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'system-ui, sans-serif' }}>
      {/* Sidebar Navigation */}
      <aside
        style={{
          width: '260px',
          backgroundColor: '#111827',
          color: '#f9fafb',
          display: 'flex',
          flexDirection: 'column',
          padding: '1.5rem 1rem',
          borderRight: '1px solid #374151',
        }}
        data-testid="platform-sidebar"
      >
        <div style={{ marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '1.125rem', fontWeight: 'bold', margin: 0, color: '#f87171' }}>
            JSP Digital Intelligence
          </h2>
          <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>Stage 0 Pilot Platform</span>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1 }}>
          <Link
            href="/"
            data-testid="nav-dashboard"
            style={{ color: '#e5e7eb', textDecoration: 'none', padding: '0.5rem', borderRadius: '4px' }}
          >
            Dashboard
          </Link>
          <Link
            href="/repository"
            data-testid="nav-repository"
            style={{ color: '#e5e7eb', textDecoration: 'none', padding: '0.5rem', borderRadius: '4px' }}
          >
            Digital Repository
          </Link>
          <Link
            href="/newspaper-archive"
            data-testid="nav-newspaper-archive"
            style={{ color: '#e5e7eb', textDecoration: 'none', padding: '0.5rem', borderRadius: '4px' }}
          >
            Newspaper Archive
          </Link>
          <Link
            href="/geography"
            data-testid="nav-geography"
            style={{ color: '#e5e7eb', textDecoration: 'none', padding: '0.5rem', borderRadius: '4px' }}
          >
            Geographic Intelligence
          </Link>
          <Link
            href="/search"
            data-testid="nav-search"
            style={{ color: '#e5e7eb', textDecoration: 'none', padding: '0.5rem', borderRadius: '4px' }}
          >
            Advanced Search
          </Link>

          {/* Role-gated upload link */}
          {canUpload && (
            <Link
              href="/upload"
              data-testid="nav-upload"
              style={{ color: '#6ee7b7', textDecoration: 'none', padding: '0.5rem', borderRadius: '4px' }}
            >
              + Upload Asset
            </Link>
          )}

          {/* Role-gated audit logs link */}
          {canViewAudit && (
            <Link
              href="/audit-logs"
              data-testid="nav-audit-logs"
              style={{ color: '#fcd34d', textDecoration: 'none', padding: '0.5rem', borderRadius: '4px' }}
            >
              Audit Logs
            </Link>
          )}
        </nav>

        {/* User profile & role badge */}
        <div
          style={{
            borderTop: '1px solid #374151',
            paddingTop: '1rem',
            marginTop: 'auto',
          }}
          data-testid="user-info-section"
        >
          {userEmail && (
            <div style={{ fontSize: '0.875rem', fontWeight: 500, color: '#f3f4f6' }}>
              {userEmail}
            </div>
          )}
          <div
            data-testid="role-badge"
            style={{
              display: 'inline-block',
              marginTop: '0.25rem',
              padding: '0.125rem 0.5rem',
              fontSize: '0.75rem',
              borderRadius: '9999px',
              backgroundColor: '#374151',
              color: '#d1d5db',
              textTransform: 'uppercase',
            }}
          >
            {role}
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main style={{ flex: 1, backgroundColor: '#f9fafb', padding: '2rem' }}>
        {children}
      </main>
    </div>
  );
}
