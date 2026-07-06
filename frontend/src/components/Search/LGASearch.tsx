import { useState, useEffect, useRef, useMemo } from 'react';
import { useLgas } from '../../hooks/useApi';
import { useAppStore } from '../../store/appStore';
import type { LGA } from '../../types';

export default function LGASearch() {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [filteredLgas, setFilteredLgas] = useState<LGA[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const { data, isLoading } = useLgas();
  const lgas = useMemo(() => data?.lgas || [], [data]);
  const { setSelectedLGA, setSelectedLGAId, selectedLGA } = useAppStore();

  useEffect(() => {
    if (query.length > 0) {
      const filtered = lgas.filter((lga) =>
        lga.name.toLowerCase().includes(query.toLowerCase())
      );
      setFilteredLgas(filtered);
      setIsOpen(true);
    } else {
      setFilteredLgas(lgas);
      setIsOpen(false);
    }
  }, [query, lgas]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (lga: LGA) => {
    setSelectedLGA(lga);
    setSelectedLGAId(lga.id);
    setQuery('');
    setIsOpen(false);
  };

  const handleClear = () => {
    setSelectedLGA(null);
    setSelectedLGAId(null);
    setQuery('');
  };

  return (
    <div className="relative">
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          placeholder="Search LGA..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => query.length > 0 && setIsOpen(true)}
          className="w-full px-4 py-2 pl-10 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
          aria-label="Search for LGA"
          aria-expanded={isOpen}
          aria-autocomplete="list"
          aria-controls="lga-search-results"
          role="combobox"
        />
        {/* Search icon */}
        <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" aria-hidden="true">
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
        {/* Loading indicator */}
        {isLoading && (
          <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
            <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin"></div>
          </div>
        )}
        {/* Clear button */}
        {!isLoading && (query || selectedLGA) && (
          <button
            onClick={handleClear}
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
            aria-label="Clear search"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
      </div>

      {/* Selected LGA badge */}
      {selectedLGA && !query && (
        <div className="mt-2 flex items-center gap-2">
          <span className="text-xs text-gray-600">Selected:</span>
          <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
            {selectedLGA.name}
          </span>
        </div>
      )}

      {/* Dropdown */}
      {isOpen && filteredLgas.length > 0 && (
        <div
          ref={dropdownRef}
          id="lga-search-results"
          className="absolute z-50 mt-1 w-full bg-white rounded-lg shadow-lg border border-gray-200 max-h-60 overflow-y-auto"
          role="listbox"
          aria-label="LGA search results"
        >
          {filteredLgas.map((lga) => (
            <button
              key={lga.id}
              onClick={() => handleSelect(lga)}
              className="w-full px-4 py-2 text-left hover:bg-gray-50 flex items-center justify-between text-sm"
              role="option"
              aria-selected={selectedLGA?.id === lga.id}
            >
              <span className="text-gray-900">{lga.name}</span>
              {lga.population && (
                <span className="text-xs text-gray-500">
                  Pop: {lga.population.toLocaleString()}
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* No results */}
      {isOpen && query && filteredLgas.length === 0 && (
        <div
          ref={dropdownRef}
          className="absolute z-50 mt-1 w-full bg-white rounded-lg shadow-lg border border-gray-200 p-4 text-center text-gray-500 text-sm"
        >
          No LGAs found matching "{query}"
        </div>
      )}
    </div>
  );
}
