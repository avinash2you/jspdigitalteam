import type { Metadata } from 'next';
import React from 'react';
import { ClerkProvider } from '@clerk/nextjs';

export const metadata: Metadata = {
  title: 'JSP Digital Intelligence Platform',
  description: 'JSP Digital Intelligence Platform Web Portal',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider signInUrl="/sign-in">
      <html lang="en">
        <body style={{ margin: 0, padding: 0 }}>{children}</body>
      </html>
    </ClerkProvider>
  );
}
