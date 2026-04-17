import { useState } from 'react';
import type { ReactNode } from 'react';
import { Sidebar } from './Sidebar';

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <main style={{
        flex: 1,
        marginLeft: '240px',
        padding: 'var(--spacing-2xl)',
        maxWidth: '1200px',
      }}>
        <div className="fade-in">
          {children}
        </div>
      </main>
    </div>
  );
}
