import React from 'react';
import { Search, X } from 'lucide-react';
import { Button } from './Button';

interface SearchBarProps {
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  onSearch?: () => void;
  onReset?: () => void;
  searchType?: string;
  searchOptions?: { value: string; label: string }[];
  onSearchTypeChange?: (type: string) => void;
  showReset?: boolean;
}

export function SearchBar({ 
  placeholder = '搜索...', 
  value, 
  onChange,
  onSearch,
  onReset,
  searchType,
  searchOptions,
  onSearchTypeChange,
  showReset = false
}: SearchBarProps) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 flex items-center gap-2 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-4 py-2.5 focus-within:border-[var(--color-primary)] transition-colors">
        <Search className="w-5 h-5 text-[var(--color-text-tertiary)]" />
        <input
          type="text"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSearch?.()}
          className="flex-1 bg-transparent border-none outline-none text-[var(--color-text-primary)]"
        />
        {value && (
          <button
            onClick={() => onChange('')}
            className="text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
      
      {searchOptions && onSearchTypeChange && (
        <select
          value={searchType}
          onChange={(e) => onSearchTypeChange(e.target.value)}
          className="px-4 py-2.5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg outline-none focus:border-[var(--color-primary)] transition-colors"
        >
          {searchOptions.map(option => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      )}
      
      {onSearch && (
        <Button onClick={onSearch}>搜索</Button>
      )}
      
      {showReset && onReset && (
        <Button variant="secondary" onClick={onReset}>
          重置
        </Button>
      )}
    </div>
  );
}
