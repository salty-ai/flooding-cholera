import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLgas } from '../../hooks/useApi';
import type { LGA, RiskLevel } from '../../types';

// Simple fuzzy matching function
function fuzzyMatch(text: string, query: string): { match: boolean; score: number } {
  const textLower = text.toLowerCase();
  const queryLower = query.toLowerCase();
  
  // Exact match gets highest score
  if (textLower === queryLower) return { match: true, score: 100 };
  
  // Starts with gets high score
  if (textLower.startsWith(queryLower)) return { match: true, score: 90 };
  
  // Contains gets medium score
  if (textLower.includes(queryLower)) return { match: true, score: 70 };
  
  // Fuzzy character matching
  let queryIdx = 0;
  let matchedChars = 0;
  let lastMatchIdx = -1;
  let consecutiveBonus = 0;
  
  for (let i = 0; i < textLower.length && queryIdx < queryLower.length; i++) {
    if (textLower[i] === queryLower[queryIdx]) {
      matchedChars++;
      if (lastMatchIdx === i - 1) {
        consecutiveBonus += 5;
      }
      lastMatchIdx = i;
      queryIdx++;
    }
  }
  
  if (queryIdx === queryLower.length) {
    const baseScore = (matchedChars / queryLower.length) * 50;
    return { match: true, score: baseScore + consecutiveBonus };
  }
  
  return { match: false, score: 0 };
}

interface LGAWithRisk extends LGA {
  risk_level?: RiskLevel;
  recent_cases?: number;
}

const RISK_STYLES: Record<RiskLevel, { bg: string; text: string; dot: string }> = {
  red: { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500' },
  yellow: { bg: 'bg-yellow-50', text: 'text-yellow-700', dot: 'bg-yellow-500' },
  green: { bg: 'bg-green-50', text: 'text-green-700', dot: 'bg-green-500' },
  unknown: { bg: 'bg-gray-50', text: 'text-gray-600', dot: 'bg-gray-400' },
};

interface Props {
  placeholder?: string;
  className?: string;
  onSelect?: (lga: LGA) => void;
  navigateOnSelect?: boolean;
}

export default function LGASearchBar({ 
  placeholder = "Search LGA...", 
  className = "",
  onSelect,
  navigateOnSelect = true 
}: Props) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  
  const { data: lgasData } = useLgas();

  // Filter and sort LGAs based on fuzzy matching
  const suggestions = useMemo(() => {
    const lgas = lgasData?.lgas || [];
    return query.length > 0
      ? lgas
          .map((lga) => ({
            ...lga,
            ...fuzzyMatch(lga.name, query),
          }))
          .filter((lga) => lga.match)
          .sort((a, b) => b.score - a.score)
          .slice(0, 8)
      : [];
  }, [lgasData, query]);

  // Reset highlighted index when suggestions change
  useEffect(() => {
    setHighlightedIndex(0);
  }, [suggestions.length]);

  const handleSelect = useCallback((lga: LGAWithRisk) => {
    setQuery('');
    setIsOpen(false);
    
    if (onSelect) {
      onSelect(lga);
    }
    
    if (navigateOnSelect) {
      navigate(`/lga/${lga.id}`);
    }
  }, [onSelect, navigateOnSelect, navigate]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') {
        setIsOpen(true);
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex((prev) => 
          prev < suggestions.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (suggestions[highlightedIndex]) {
          handleSelect(suggestions[highlightedIndex]);
        }
        break;
      case 'Escape':
        setIsOpen(false);
        inputRef.current?.blur();
        break;
    }
  }, [isOpen, suggestions, highlightedIndex, handleSelect]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        dropdownRef.current && 
        !dropdownRef.current.contains(e.target as Node) &&
        !inputRef.current?.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className={`relative ${className}`}>
      {/* Search Input */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-[#637588]">
          <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>search</span>
        </div>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => query.length > 0 && setIsOpen(true)}
          onKeyDown={handleKeyDown}
          className="block w-full rounded-lg border-none bg-[#f0f2f5] py-2.5 pl-10 pr-4 text-sm text-[#111518] placeholder-[#637588] focus:ring-2 focus:ring-primary focus:bg-white transition-all"
          placeholder={placeholder}
          autoComplete="off"
        />
        {query && (
          <button
            onClick={() => {
              setQuery('');
              setIsOpen(false);
              inputRef.current?.focus();
            }}
            className="absolute inset-y-0 right-0 flex items-center pr-3 text-[#637588] hover:text-[#111518]"
          >
            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>close</span>
          </button>
        )}
      </div>

      {/* Suggestions Dropdown */}
      {isOpen && suggestions.length > 0 && (
        <div
          ref={dropdownRef}
          className="absolute z-50 w-full mt-1 bg-white rounded-xl shadow-lg border border-[#e6e8eb] overflow-hidden"
        >
          <div className="py-1 max-h-80 overflow-y-auto">
            {suggestions.map((lga, index) => {
              const riskLevel = (lga as LGAWithRisk).risk_level || 'unknown';
              const style = RISK_STYLES[riskLevel];
              
              return (
                <button
                  key={lga.id}
                  onClick={() => handleSelect(lga)}
                  onMouseEnter={() => setHighlightedIndex(index)}
                  className={`w-full px-4 py-3 flex items-center gap-3 text-left transition-colors ${
                    index === highlightedIndex 
                      ? 'bg-primary/5' 
                      : 'hover:bg-gray-50'
                  }`}
                >
                  {/* Risk indicator dot */}
                  <span className={`size-2.5 rounded-full ${style.dot} flex-shrink-0`} />
                  
                  {/* LGA Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-[#111518] truncate">
                        {highlightQuery(lga.name, query)}
                      </span>
                      {lga.code && (
                        <span className="text-xs text-[#637588] bg-[#f0f2f5] px-1.5 py-0.5 rounded">
                          {lga.code}
                        </span>
                      )}
                    </div>
                    {lga.population && (
                      <span className="text-xs text-[#637588]">
                        Pop: {lga.population.toLocaleString()}
                      </span>
                    )}
                  </div>

                  {/* Arrow indicator */}
                  <span className="material-symbols-outlined text-[#637588]" style={{ fontSize: '18px' }}>
                    arrow_forward
                  </span>
                </button>
              );
            })}
          </div>
          
          {/* Footer hint */}
          <div className="px-4 py-2 bg-[#f6f7f8] border-t border-[#e6e8eb] flex items-center gap-2 text-xs text-[#637588]">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-white border border-[#e6e8eb] rounded text-[10px]">↑↓</kbd>
              navigate
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-white border border-[#e6e8eb] rounded text-[10px]">↵</kbd>
              select
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-white border border-[#e6e8eb] rounded text-[10px]">esc</kbd>
              close
            </span>
          </div>
        </div>
      )}

      {/* No results message */}
      {isOpen && query.length > 0 && suggestions.length === 0 && (
        <div
          ref={dropdownRef}
          className="absolute z-50 w-full mt-1 bg-white rounded-xl shadow-lg border border-[#e6e8eb] overflow-hidden"
        >
          <div className="px-4 py-6 text-center">
            <span className="material-symbols-outlined text-[#637588] mb-2" style={{ fontSize: '32px' }}>
              search_off
            </span>
            <p className="text-sm text-[#637588]">
              No LGA found matching "<span className="font-medium text-[#111518]">{query}</span>"
            </p>
            <p className="text-xs text-[#637588] mt-1">
              Try a different spelling or check the LGA name
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// Helper to highlight matching parts of text
function highlightQuery(text: string, query: string): React.ReactNode {
  if (!query) return text;
  
  const lowerText = text.toLowerCase();
  const lowerQuery = query.toLowerCase();
  const index = lowerText.indexOf(lowerQuery);
  
  if (index === -1) return text;
  
  return (
    <>
      {text.slice(0, index)}
      <span className="bg-yellow-200 text-yellow-900 rounded px-0.5">
        {text.slice(index, index + query.length)}
      </span>
      {text.slice(index + query.length)}
    </>
  );
}
