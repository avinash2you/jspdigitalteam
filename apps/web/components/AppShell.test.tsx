import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { UserRole } from '@jsp/shared';
import { AppShell } from './AppShell';

describe('AppShell Component Role-Based Visibility', () => {
  it('renders standard navigation for viewer without upload or audit links', () => {
    render(
      <AppShell role={UserRole.VIEWER} userEmail="viewer@jsp.internal">
        <div>Viewer Dashboard Content</div>
      </AppShell>
    );

    // Standard public navigation items are present
    expect(screen.getByTestId('nav-dashboard')).toBeDefined();
    expect(screen.getByTestId('nav-repository')).toBeDefined();
    expect(screen.getByTestId('nav-newspaper-archive')).toBeDefined();
    expect(screen.getByTestId('nav-geography')).toBeDefined();
    expect(screen.getByTestId('nav-search')).toBeDefined();

    // Privileged links are hidden
    expect(screen.queryByTestId('nav-upload')).toBeNull();
    expect(screen.queryByTestId('nav-audit-logs')).toBeNull();

    // Role badge
    expect(screen.getByTestId('role-badge').textContent).toBe('viewer');
    expect(screen.getByText('viewer@jsp.internal')).toBeDefined();
  });

  it('renders upload link for researcher but hides audit logs', () => {
    render(
      <AppShell role={UserRole.RESEARCHER} userEmail="researcher@jsp.internal">
        <div>Researcher Content</div>
      </AppShell>
    );

    // Upload link is visible for researcher
    expect(screen.getByTestId('nav-upload')).toBeDefined();

    // Audit logs are hidden for researcher
    expect(screen.queryByTestId('nav-audit-logs')).toBeNull();

    // Role badge
    expect(screen.getByTestId('role-badge').textContent).toBe('researcher');
  });

  it('renders both upload and audit logs links for super_admin', () => {
    render(
      <AppShell role={UserRole.SUPER_ADMIN} userEmail="admin@jsp.internal">
        <div>Admin Content</div>
      </AppShell>
    );

    // Both privileged links are visible
    expect(screen.getByTestId('nav-upload')).toBeDefined();
    expect(screen.getByTestId('nav-audit-logs')).toBeDefined();

    // Role badge
    expect(screen.getByTestId('role-badge').textContent).toBe('super_admin');
  });

  it('enforces invite-only architecture with no public registration link', () => {
    const { container } = render(
      <AppShell role={UserRole.VIEWER}>
        <div>Content</div>
      </AppShell>
    );

    // Ensure no sign-up or register links exist
    const links = container.querySelectorAll('a');
    links.forEach((link) => {
      expect(link.getAttribute('href')).not.toContain('sign-up');
      expect(link.getAttribute('href')).not.toContain('register');
      expect(link.textContent?.toLowerCase()).not.toContain('sign up');
      expect(link.textContent?.toLowerCase()).not.toContain('register');
    });
  });
});
