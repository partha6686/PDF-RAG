'use client'

import { useState } from 'react'

export default function PDFUpload() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<string>('')
  const [jobId, setJobId] = useState<string | null>(null)
  const [processingStatus, setProcessingStatus] = useState<string>('')

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file)
      setUploadStatus('')
    } else {
      setUploadStatus('Please select a valid PDF file')
      setSelectedFile(null)
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) return

    setUploading(true)
    setUploadStatus('Uploading...')

    try {
      const formData = new FormData()
      formData.append('pdf', selectedFile)

      const response = await fetch('http://localhost:3002/api/upload', {
        method: 'POST',
        body: formData,
      })

      if (response.ok) {
        const data = await response.json()
        setUploadStatus('PDF uploaded successfully!')
        setJobId(data.jobId)
        setSelectedFile(null)
        
        // Start polling for processing status
        pollProcessingStatus(data.jobId)
      } else {
        setUploadStatus('Upload failed. Please try again.')
      }
    } catch (error) {
      setUploadStatus('Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  const pollProcessingStatus = async (jobId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:3002/api/job/${jobId}`)
        if (response.ok) {
          const jobData = await response.json()
          
          if (jobData.state === 'completed') {
            setProcessingStatus('✅ PDF processed successfully! Ready for questions.')
            clearInterval(pollInterval)
          } else if (jobData.state === 'failed') {
            setProcessingStatus('❌ PDF processing failed. Please try uploading again.')
            clearInterval(pollInterval)
          } else if (jobData.state === 'active') {
            setProcessingStatus(`🔄 Processing PDF... ${jobData.progress || 0}%`)
          } else {
            setProcessingStatus('⏳ PDF queued for processing...')
          }
        }
      } catch (error) {
        console.error('Error polling job status:', error)
        setProcessingStatus('❓ Unable to check processing status')
        clearInterval(pollInterval)
      }
    }, 2000)

    // Stop polling after 2 minutes
    setTimeout(() => {
      clearInterval(pollInterval)
      if (processingStatus && !processingStatus.includes('✅') && !processingStatus.includes('❌')) {
        setProcessingStatus('⏰ Processing is taking longer than expected...')
      }
    }, 120000)
  }

  return (
    <div className="flex flex-col h-full p-6 bg-gray-50 border-r border-gray-200">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">Upload PDF</h2>
      
      <div className="flex-1 flex flex-col items-center justify-center">
        <div className="w-full max-w-md">
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-gray-400 transition-colors">
            <svg
              className="mx-auto h-12 w-12 text-gray-400 mb-4"
              stroke="currentColor"
              fill="none"
              viewBox="0 0 48 48"
            >
              <path
                d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            
            <label htmlFor="pdf-upload" className="cursor-pointer">
              <span className="text-lg font-medium text-gray-900">
                Click to upload PDF
              </span>
              <input
                id="pdf-upload"
                type="file"
                className="hidden"
                accept=".pdf"
                onChange={handleFileSelect}
              />
            </label>
            <p className="text-sm text-gray-500 mt-2">or drag and drop</p>
          </div>

          {selectedFile && (
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
              <p className="text-sm font-medium text-blue-900">
                Selected: {selectedFile.name}
              </p>
              <p className="text-xs text-blue-700">
                Size: {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
          )}

          {uploadStatus && (
            <div className={`mt-4 p-3 rounded ${
              uploadStatus.includes('successfully') 
                ? 'bg-green-50 border border-green-200 text-green-800'
                : uploadStatus.includes('failed')
                ? 'bg-red-50 border border-red-200 text-red-800'
                : 'bg-yellow-50 border border-yellow-200 text-yellow-800'
            }`}>
              <p className="text-sm">{uploadStatus}</p>
            </div>
          )}

          {processingStatus && (
            <div className={`mt-4 p-3 rounded ${
              processingStatus.includes('✅') 
                ? 'bg-green-50 border border-green-200 text-green-800'
                : processingStatus.includes('❌')
                ? 'bg-red-50 border border-red-200 text-red-800'
                : 'bg-blue-50 border border-blue-200 text-blue-800'
            }`}>
              <p className="text-sm font-medium">{processingStatus}</p>
              {jobId && (
                <p className="text-xs mt-1 opacity-75">Job ID: {jobId}</p>
              )}
            </div>
          )}

          <button
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            className={`w-full mt-6 py-3 px-4 rounded-lg font-medium transition-colors ${
              selectedFile && !uploading
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            {uploading ? 'Uploading...' : 'Upload PDF'}
          </button>
        </div>
      </div>
    </div>
  )
}