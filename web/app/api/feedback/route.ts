import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    // Validate required fields
    const { query, doc_id, chunk_id, label, user_id } = body
    
    if (!label) {
      return NextResponse.json(
        { error: 'Label is required' },
        { status: 400 }
      )
    }
    
    // Forward to gateway
    const gatewayUrl = process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8000'
    
    const response = await fetch(`${gatewayUrl}/feedback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: query || '',
        doc_id: doc_id || null,
        chunk_id: chunk_id || null,
        label,
        user_id: user_id || 'anonymous'
      })
    })
    
    if (!response.ok) {
      throw new Error(`Gateway responded with ${response.status}`)
    }
    
    const result = await response.json()
    
    return NextResponse.json(result)
    
  } catch (error) {
    console.error('Feedback API error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
