'use client'

import { useState } from 'react'
import { FileText, ThumbsUp, ThumbsDown, Shield, CheckCircle } from 'lucide-react'

interface Citation {
  chunk_id: string
  span: { start: number; end: number }
}

interface AskResult {
  answer: string
  citations: Citation[]
  evidence_coverage: number
  abstained: boolean
  reason?: string
}

interface CitationPaneProps {
  result: AskResult
  onFeedback: (docId: string, chunkId: string, label: string) => void
}

export default function CitationPane({ result, onFeedback }: CitationPaneProps) {
  const [feedbackGiven, setFeedbackGiven] = useState<Set<string>>(new Set())

  const handleFeedback = (label: string) => {
    const key = `answer-${label}`
    if (!feedbackGiven.has(key)) {
      onFeedback('', '', label)
      setFeedbackGiven(new Set([...feedbackGiven, key]))
    }
  }

  const renderAnswerWithCitations = (answer: string, citations: Citation[]) => {
    // Simple citation rendering - in a real implementation, you'd want more sophisticated parsing
    let processedAnswer = answer
    
    // Replace [chunk_id:start-end] patterns with clickable citations
    citations.forEach((citation, index) => {
      const citationPattern = `[${citation.chunk_id}:${citation.span.start}-${citation.span.end}]`
      const citationElement = `<sup class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 cursor-pointer hover:bg-blue-200 dark:hover:bg-blue-800" title="Citation ${index + 1}">${index + 1}</sup>`
      processedAnswer = processedAnswer.replace(citationPattern, citationElement)
    })

    return (
      <div
        className="prose dark:prose-invert max-w-none"
        dangerouslySetInnerHTML={{ __html: processedAnswer }}
      />
    )
  }

  if (result.abstained) {
    return (
      <div className="card p-8 text-center">
        <Shield className="h-16 w-16 text-gray-400 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
          Unable to Answer
        </h3>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          {result.reason === 'low_coverage' 
            ? 'Not enough relevant information found to answer this question.'
            : 'Unable to generate a reliable answer with proper citations.'
          }
        </p>
        <div className="flex justify-center space-x-4">
          <button
            onClick={() => handleFeedback('thumbs_down')}
            disabled={feedbackGiven.has('answer-thumbs_down')}
            className={`inline-flex items-center px-4 py-2 rounded-lg font-medium transition-colors ${
              feedbackGiven.has('answer-thumbs_down')
                ? 'text-red-600 cursor-not-allowed'
                : 'text-gray-600 dark:text-gray-400 hover:text-red-600'
            }`}
          >
            <ThumbsDown className="h-4 w-4 mr-2" />
            Not Helpful
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Answer */}
      <div className="card p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-2">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Answer
            </h2>
          </div>
          
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Coverage: {(result.evidence_coverage * 100).toFixed(1)}%
            </span>
            <div className="flex items-center space-x-1">
              <button
                onClick={() => handleFeedback('thumbs_up')}
                disabled={feedbackGiven.has('answer-thumbs_up')}
                className={`p-2 rounded-lg transition-colors ${
                  feedbackGiven.has('answer-thumbs_up')
                    ? 'text-green-600 cursor-not-allowed'
                    : 'text-gray-400 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-900'
                }`}
                title="This answer is helpful"
              >
                <ThumbsUp className="h-4 w-4" />
              </button>
              <button
                onClick={() => handleFeedback('thumbs_down')}
                disabled={feedbackGiven.has('answer-thumbs_down')}
                className={`p-2 rounded-lg transition-colors ${
                  feedbackGiven.has('answer-thumbs_down')
                    ? 'text-red-600 cursor-not-allowed'
                    : 'text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900'
                }`}
                title="This answer is not helpful"
              >
                <ThumbsDown className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

        <div className="prose dark:prose-invert max-w-none">
          {renderAnswerWithCitations(result.answer, result.citations)}
        </div>
      </div>

      {/* Citations */}
      {result.citations && result.citations.length > 0 && (
        <div className="card p-6">
          <div className="flex items-center space-x-2 mb-4">
            <FileText className="h-5 w-5 text-gray-600 dark:text-gray-400" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Sources & Citations
            </h3>
          </div>

          <div className="space-y-4">
            {result.citations.map((citation, index) => (
              <div key={citation.chunk_id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                      {index + 1}
                    </span>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {citation.chunk_id}
                    </span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <button
                      onClick={() => handleFeedback(`citation-${index}-thumbs_up`)}
                      disabled={feedbackGiven.has(`citation-${index}-thumbs_up`)}
                      className={`p-1 rounded transition-colors ${
                        feedbackGiven.has(`citation-${index}-thumbs_up`)
                          ? 'text-green-600 cursor-not-allowed'
                          : 'text-gray-400 hover:text-green-600'
                      }`}
                      title="This citation is helpful"
                    >
                      <ThumbsUp className="h-3 w-3" />
                    </button>
                    <button
                      onClick={() => handleFeedback(`citation-${index}-thumbs_down`)}
                      disabled={feedbackGiven.has(`citation-${index}-thumbs_down`)}
                      className={`p-1 rounded transition-colors ${
                        feedbackGiven.has(`citation-${index}-thumbs_down`)
                          ? 'text-red-600 cursor-not-allowed'
                          : 'text-gray-400 hover:text-red-600'
                      }`}
                      title="This citation is not helpful"
                    >
                      <ThumbsDown className="h-3 w-3" />
                    </button>
                  </div>
                </div>
                
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  <p>Span: {citation.span.start} - {citation.span.end}</p>
                  {/* In a real implementation, you'd fetch and display the actual text content here */}
                  <p className="mt-2 italic">
                    [Text content would be displayed here in a real implementation]
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
