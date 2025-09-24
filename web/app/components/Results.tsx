'use client'

import { useState } from 'react'
import { ExternalLink, ThumbsUp, ThumbsDown, FileText } from 'lucide-react'

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

interface ResultsProps {
  results: SearchResult[]
  onFeedback: (docId: string, chunkId: string, label: string) => void
}

export default function Results({ results, onFeedback }: ResultsProps) {
  const [feedbackGiven, setFeedbackGiven] = useState<Set<string>>(new Set())

  const handleFeedback = (docId: string, chunkId: string, label: string) => {
    const key = `${docId}-${chunkId}-${label}`
    if (!feedbackGiven.has(key)) {
      onFeedback(docId, chunkId, label)
      setFeedbackGiven(new Set([...feedbackGiven, key]))
    }
  }

  const renderHighlights = (highlights: string[]) => {
    if (!highlights || highlights.length === 0) return null

    return (
      <div className="space-y-1">
        {highlights.slice(0, 3).map((highlight, index) => (
          <p
            key={index}
            className="text-sm text-gray-600 dark:text-gray-400"
            dangerouslySetInnerHTML={{
              __html: highlight.replace(
                /<em>(.*?)<\/em>/g,
                '<span class="highlight">$1</span>'
              )
            }}
          />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Search Results
        </h2>
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {results.length} result{results.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="space-y-4">
        {results.map((result, index) => (
          <div key={result.chunk_id} className="card p-6">
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-2">
                  <FileText className="h-4 w-4 text-gray-400" />
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                    {result.title}
                  </h3>
                </div>
                
                {result.url && (
                  <a
                    href={result.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
                  >
                    <ExternalLink className="h-3 w-3 mr-1" />
                    {result.url}
                  </a>
                )}
              </div>

              <div className="flex items-center space-x-2 ml-4">
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  Score: {result.score.toFixed(2)}
                </span>
                <div className="flex items-center space-x-1">
                  <button
                    onClick={() => handleFeedback(result.doc_id, result.chunk_id, 'thumbs_up')}
                    disabled={feedbackGiven.has(`${result.doc_id}-${result.chunk_id}-thumbs_up`)}
                    className={`p-1 rounded transition-colors ${
                      feedbackGiven.has(`${result.doc_id}-${result.chunk_id}-thumbs_up`)
                        ? 'text-green-600 cursor-not-allowed'
                        : 'text-gray-400 hover:text-green-600'
                    }`}
                    title="This result is helpful"
                  >
                    <ThumbsUp className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleFeedback(result.doc_id, result.chunk_id, 'thumbs_down')}
                    disabled={feedbackGiven.has(`${result.doc_id}-${result.chunk_id}-thumbs_down`)}
                    className={`p-1 rounded transition-colors ${
                      feedbackGiven.has(`${result.doc_id}-${result.chunk_id}-thumbs_down`)
                        ? 'text-red-600 cursor-not-allowed'
                        : 'text-gray-400 hover:text-red-600'
                    }`}
                    title="This result is not helpful"
                  >
                    <ThumbsDown className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>

            {/* Highlights */}
            {renderHighlights(result.highlights)}

            {/* Metadata */}
            <div className="flex items-center space-x-4 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              {result.section && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                  {result.section}
                </span>
              )}
              {result.lang && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
                  {result.lang}
                </span>
              )}
              {result.tags && result.tags.length > 0 && (
                <div className="flex items-center space-x-1">
                  {result.tags.slice(0, 3).map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                    >
                      {tag}
                    </span>
                  ))}
                  {result.tags.length > 3 && (
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      +{result.tags.length - 3} more
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
