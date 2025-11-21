import React from 'react';
import { Database, Home, ChevronRight, ArrowLeft } from 'lucide-react';
import { IconButton } from './ui/Button';

interface LayoutProps {
  children: React.ReactNode;
  activeTab: 'collections' | 'history';
  breadcrumbs: { label: string; href?: string }[];
  onNavigate: (path: string) => void;
  showBackButton?: boolean;
  onBack?: () => void;
}

export function Layout({ children, activeTab, breadcrumbs, onNavigate, showBackButton, onBack }: LayoutProps) {
  return (
    <div className="min-h-screen flex flex-col bg-[var(--color-background)]">
      {/* Top App Bar */}
      <header className="bg-[var(--color-surface)] border-b border-[var(--color-border)] px-8 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-[var(--color-primary)] to-blue-600 rounded-lg flex items-center justify-center">
              <Database className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-[var(--color-text-primary)]">EvidenceQA</h2>
          </div>
          <div className="w-10 h-10 bg-gradient-to-br from-slate-600 to-slate-700 rounded-full flex items-center justify-center text-white">
            <span>U</span>
          </div>
        </div>
      </header>
      
      {/* Tab Bar */}
      <div className="bg-[var(--color-surface)] border-b border-[var(--color-border)] px-8">
        <div className="flex gap-1">
          <button
            onClick={() => onNavigate('/')}
            className={`px-6 py-3 relative transition-colors ${
              activeTab === 'collections' 
                ? 'text-[var(--color-primary)]' 
                : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
            }`}
          >
            知识库主页
            {activeTab === 'collections' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--color-primary)]" />
            )}
          </button>
          <button
            onClick={() => onNavigate('/chat-history')}
            className={`px-6 py-3 relative transition-colors ${
              activeTab === 'history' 
                ? 'text-[var(--color-primary)]' 
                : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
            }`}
          >
            Chat 历史
            {activeTab === 'history' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--color-primary)]" />
            )}
          </button>
        </div>
      </div>
      
      {/* Breadcrumb */}
      <div className="bg-[var(--color-surface)] px-8 py-3 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-3">
          {showBackButton && onBack && (
            <IconButton onClick={onBack} size="sm">
              <ArrowLeft className="w-5 h-5" />
            </IconButton>
          )}
          <div className="flex items-center gap-2 text-sm">
            <Home className="w-4 h-4 text-[var(--color-text-tertiary)]" />
            {breadcrumbs.map((crumb, index) => (
              <React.Fragment key={index}>
                {index > 0 && <ChevronRight className="w-4 h-4 text-[var(--color-text-tertiary)]" />}
                {crumb.href ? (
                  <button 
                    onClick={() => onNavigate(crumb.href!)}
                    className="text-[var(--color-primary)] hover:underline"
                  >
                    {crumb.label}
                  </button>
                ) : (
                  <span className="text-[var(--color-text-secondary)]">{crumb.label}</span>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>
      
      {/* Main Content */}
      <main className="flex-1">
        {children}
      </main>
    </div>
  );
}
