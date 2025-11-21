import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'error';
  className?: string;
}

export function Badge({ children, variant = 'default', className = '' }: BadgeProps) {
  const variants = {
    default: 'bg-[var(--color-background)] text-[var(--color-text-secondary)] border border-[var(--color-border)]',
    primary: 'bg-[var(--color-primary-light)] text-[var(--color-primary)]',
    success: 'bg-green-50 text-green-700',
    warning: 'bg-yellow-50 text-yellow-700',
    error: 'bg-red-50 text-red-700'
  };
  
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs ${variants[variant]} ${className}`}>
      {children}
    </span>
  );
}
