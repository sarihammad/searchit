import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'SearchIt - Neural Search Engine',
  description: 'Hybrid search and RAG system with BM25 + Vector search',
  keywords: ['search', 'ai', 'rag', 'neural search', 'semantic search'],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="h-full">
      <body className={`${inter.className} h-full`}>
        <div className="min-h-full bg-gray-50 dark:bg-gray-900">
          {children}
        </div>
      </body>
    </html>
  )
}
