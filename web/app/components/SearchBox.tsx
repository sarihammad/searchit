'use client'

import { useState, KeyboardEvent } from 'react'
import { Search } from 'lucide-react'

interface SearchBoxProps {
  onSearch: (query: string) => void
  loading: boolean
  placeholder: string
}

export default function SearchBox({ onSearch, loading, placeholder }: SearchBoxProps) {
  const [query, setQuery] = useState('')

  const handleSubmit = () => {
    if (query.trim() && !loading) {
      onSearch(query.trim())
    }
  }

  const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSubmit()
    }
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-gray-400" />
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={placeholder}
          disabled={loading}
          className="input-field pl-10 pr-12 py-4 text-lg"
        />
        <button
          onClick={handleSubmit}
          disabled={loading || !query.trim()}
          className="absolute inset-y-0 right-0 pr-3 flex items-center"
        >
          <div className={`p-2 rounded-lg transition-colors ${
            loading || !query.trim()
              ? 'text-gray-400 cursor-not-allowed'
              : 'text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900 cursor-pointer'
          }`}>
            <Search className="h-5 w-5" />
          </div>
        </button>
      </div>
      
      {/* Search suggestions */}
      {query && (
        <div className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          <p>Press Enter to search</p>
        </div>
      )}
    </div>
  )
}
