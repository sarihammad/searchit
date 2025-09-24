'use client'

import { useState } from 'react'
import { Search, Brain, Zap, Shield } from 'lucide-react'
import SearchBox from './components/SearchBox'
import Results from './components/Results'
import Filters from './components/Filters'
import CitationPane from './components/CitationPane'

interface SearchResult {
  doc_id: string
  chunk_id: string
  score: number
  title: string
  url: string
  highlights: string[]
  section: string
  lang: string
  tags: string[]
}

interface Facets {
  lang: Record<string, number>
  tags: Record<string, number>
}

interface AskResult {
  answer: string
  citations: Array<{
    chunk_id: string
    span: { start: number; end: number }
  }>
  evidence_coverage: number
  abstained: boolean
  reason?: string
}

export default function HomePage() {
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [facets, setFacets] = useState<Facets>({})
  const [askResult, setAskResult] = useState<AskResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'search' | 'ask'>('search')
  const [selectedFilters, setSelectedFilters] = useState<Record<string, string>>({})

  const handleSearch = async (query: string, filters: Record<string, string> = {}) => {
    if (!query.trim()) return

    setLoading(true)
    try {
      const params = new URLSearchParams({
        q: query,
        top_k: '10',
        with_highlights: 'true',
        ...filters
      })

      const response = await fetch(`/search?${params}`)
      if (!response.ok) throw new Error('Search failed')

      const data = await response.json()
      setSearchResults(data.results || [])
      setFacets(data.facets || {})
    } catch (error) {
      console.error('Search error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAsk = async (question: string) => {
    if (!question.trim()) return

    setLoading(true)
    try {
      const response = await fetch('/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question,
          top_k: 8,
          ground: true
        })
      })

      if (!response.ok) throw new Error('Ask failed')

      const data = await response.json()
      setAskResult(data)
    } catch (error) {
      console.error('Ask error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleFeedback = async (docId: string, chunkId: string, label: string) => {
    try {
      await fetch('/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchResults[0]?.title || '',
          doc_id: docId,
          chunk_id: chunkId,
          label,
          user_id: 'anonymous'
        })
      })
    } catch (error) {
      console.error('Feedback error:', error)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <Brain className="h-8 w-8 text-primary-600" />
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                SearchIt
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              <button className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700">
                <Zap className="h-5 w-5 text-gray-600 dark:text-gray-400" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Hero Section */}
        <div className="text-center mb-8">
          <h2 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
            Neural Search Engine
          </h2>
          <p className="text-xl text-gray-600 dark:text-gray-400 max-w-3xl mx-auto">
            Hybrid BM25 + Vector search with grounded question answering. 
            Find relevant information with citations and evidence.
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="flex justify-center mb-8">
          <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
            <button
              onClick={() => setActiveTab('search')}
              className={`px-6 py-2 rounded-md font-medium transition-colors ${
                activeTab === 'search'
                  ? 'bg-white dark:bg-gray-700 text-primary-600 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
            >
              Search
            </button>
            <button
              onClick={() => setActiveTab('ask')}
              className={`px-6 py-2 rounded-md font-medium transition-colors ${
                activeTab === 'ask'
                  ? 'bg-white dark:bg-gray-700 text-primary-600 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
            >
              Ask
            </button>
          </div>
        </div>

        {/* Search Interface */}
        <div className="max-w-4xl mx-auto">
          <SearchBox
            onSearch={activeTab === 'search' ? handleSearch : handleAsk}
            loading={loading}
            placeholder={
              activeTab === 'search' 
                ? 'Search for documents...' 
                : 'Ask a question...'
            }
          />

          {/* Filters */}
          {activeTab === 'search' && Object.keys(facets).length > 0 && (
            <Filters
              facets={facets}
              selectedFilters={selectedFilters}
              onFilterChange={(filters) => {
                setSelectedFilters(filters)
                // Re-run search with new filters
                const currentQuery = (document.querySelector('input') as HTMLInputElement)?.value
                if (currentQuery) {
                  handleSearch(currentQuery, filters)
                }
              }}
            />
          )}

          {/* Results */}
          {loading && (
            <div className="flex justify-center items-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
              <span className="ml-3 text-gray-600 dark:text-gray-400">
                {activeTab === 'search' ? 'Searching...' : 'Thinking...'}
              </span>
            </div>
          )}

          {!loading && activeTab === 'search' && searchResults.length > 0 && (
            <Results
              results={searchResults}
              onFeedback={handleFeedback}
            />
          )}

          {!loading && activeTab === 'ask' && askResult && (
            <CitationPane
              result={askResult}
              onFeedback={handleFeedback}
            />
          )}

          {!loading && activeTab === 'search' && searchResults.length === 0 && (
            <div className="text-center py-12">
              <Search className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                No results found
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Try different keywords or check your spelling.
              </p>
            </div>
          )}

          {!loading && activeTab === 'ask' && askResult?.abstained && (
            <div className="text-center py-12">
              <Shield className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                Unable to answer
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                {askResult.reason === 'low_coverage' 
                  ? 'Not enough relevant information found to answer this question.'
                  : 'Unable to generate a reliable answer with proper citations.'
                }
              </p>
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-gray-600 dark:text-gray-400">
            <p>SearchIt - Hybrid Neural Search Engine with RAG</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
