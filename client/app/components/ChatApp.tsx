'use client'

import { useState } from 'react'
import DocumentList from './DocumentList'
import DocumentChat from './DocumentChat'

interface Document {
  document_id: string
  filename: string
  original_name: string
  file_size: number
  processing_status: string
  chunk_count: number
  created_at: string
  processed_at?: string
}

export default function ChatApp() {
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null)

  return (
    <div className="flex h-full bg-white">
      <DocumentList 
        onSelectDocument={setSelectedDocument}
        selectedDocumentId={selectedDocument?.document_id || null}
      />
      <DocumentChat document={selectedDocument} />
    </div>
  )
}