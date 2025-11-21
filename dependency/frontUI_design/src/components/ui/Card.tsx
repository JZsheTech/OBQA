import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  hover?: boolean;
}

export function Card({ children, className = '', onClick, hover = false }: CardProps) {
  const hoverClass = hover ? 'hover:shadow-md hover:border-[var(--color-primary-light)] cursor-pointer' : '';
  
  return (
    <div 
      className={`bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-6 transition-all duration-200 ${hoverClass} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  );
}
