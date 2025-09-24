'use client'

import { useState } from 'react'
import { ChevronDown, X } from 'lucide-react'

interface Facets {
  lang: Record<string, number>
  tags: Record<string, number>
}

interface FiltersProps {
  facets: Facets
  selectedFilters: Record<string, string>
  onFilterChange: (filters: Record<string, string>) => void
}

export default function Filters({ facets, selectedFilters, onFilterChange }: FiltersProps) {
  const [expandedFacets, setExpandedFacets] = useState<Set<string>>(new Set())

  const toggleFacet = (facetName: string) => {
    const newExpanded = new Set(expandedFacets)
    if (newExpanded.has(facetName)) {
      newExpanded.delete(facetName)
    } else {
      newExpanded.add(facetName)
    }
    setExpandedFacets(newExpanded)
  }

  const handleFilterSelect = (facetName: string, value: string) => {
    const newFilters = { ...selectedFilters }
    
    if (selectedFilters[facetName] === value) {
      // Remove filter if already selected
      delete newFilters[facetName]
    } else {
      // Set new filter
      newFilters[facetName] = value
    }
    
    onFilterChange(newFilters)
  }

  const clearAllFilters = () => {
    onFilterChange({})
  }

  const hasActiveFilters = Object.keys(selectedFilters).length > 0

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-900 dark:text-white">
          Filters
        </h3>
        {hasActiveFilters && (
          <button
            onClick={clearAllFilters}
            className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
          >
            Clear all
          </button>
        )}
      </div>

      <div className="space-y-4">
        {/* Language Filter */}
        {facets.lang && Object.keys(facets.lang).length > 0 && (
          <div>
            <button
              onClick={() => toggleFacet('lang')}
              className="flex items-center justify-between w-full text-left text-sm font-medium text-gray-900 dark:text-white hover:text-gray-700 dark:hover:text-gray-300"
            >
              <span>Language ({Object.keys(facets.lang).length})</span>
              <ChevronDown
                className={`h-4 w-4 transition-transform ${
                  expandedFacets.has('lang') ? 'rotate-180' : ''
                }`}
              />
            </button>
            
            {expandedFacets.has('lang') && (
              <div className="mt-2 space-y-1">
                {Object.entries(facets.lang)
                  .sort(([, a], [, b]) => b - a)
                  .map(([lang, count]) => (
                    <label
                      key={lang}
                      className="flex items-center space-x-2 cursor-pointer"
                    >
                      <input
                        type="radio"
                        name="lang"
                        value={lang}
                        checked={selectedFilters.lang === lang}
                        onChange={() => handleFilterSelect('lang', lang)}
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 dark:border-gray-600 dark:bg-gray-700"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300">
                        {lang.toUpperCase()} ({count})
                      </span>
                    </label>
                  ))}
              </div>
            )}
          </div>
        )}

        {/* Tags Filter */}
        {facets.tags && Object.keys(facets.tags).length > 0 && (
          <div>
            <button
              onClick={() => toggleFacet('tags')}
              className="flex items-center justify-between w-full text-left text-sm font-medium text-gray-900 dark:text-white hover:text-gray-700 dark:hover:text-gray-300"
            >
              <span>Tags ({Object.keys(facets.tags).length})</span>
              <ChevronDown
                className={`h-4 w-4 transition-transform ${
                  expandedFacets.has('tags') ? 'rotate-180' : ''
                }`}
              />
            </button>
            
            {expandedFacets.has('tags') && (
              <div className="mt-2 space-y-1 max-h-40 overflow-y-auto">
                {Object.entries(facets.tags)
                  .sort(([, a], [, b]) => b - a)
                  .map(([tag, count]) => (
                    <label
                      key={tag}
                      className="flex items-center space-x-2 cursor-pointer"
                    >
                      <input
                        type="radio"
                        name="tags"
                        value={tag}
                        checked={selectedFilters.tags === tag}
                        onChange={() => handleFilterSelect('tags', tag)}
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 dark:border-gray-600 dark:bg-gray-700"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300">
                        {tag} ({count})
                      </span>
                    </label>
                  ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Active Filters */}
      {hasActiveFilters && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex flex-wrap gap-2">
            {Object.entries(selectedFilters).map(([key, value]) => (
              <span
                key={`${key}-${value}`}
                className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200"
              >
                {key}: {value}
                <button
                  onClick={() => handleFilterSelect(key, value)}
                  className="ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full hover:bg-primary-200 dark:hover:bg-primary-800"
                >
                  <X className="h-2.5 w-2.5" />
                </button>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
