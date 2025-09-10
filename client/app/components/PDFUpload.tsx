'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'

export default function PDFUpload() {
  const { token } = useAuth()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<string>('')
  const [jobId, setJobId] = useState<string | null>(null)
  const [processingStatus, setProcessingStatus] = useState<string>('')
  const [progressPercent, setProgressPercent] = useState<number>(0)
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null)

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
      formData.append('file', selectedFile)  // FastAPI expects 'file' parameter

      const response = await fetch('http://localhost:8000/api/upload/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      })

      if (response.ok) {
        const data = await response.json()
        setUploadStatus('PDF uploaded successfully!')
        setJobId(data.job_id)
        setSelectedFile(null)

        // Start polling for processing status
        pollProcessingStatus(data.job_id)
      } else {
        setUploadStatus('Upload failed. Please try again.')
      }
    } catch (error) {
      setUploadStatus('Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  const stopPolling = () => {
    if (pollingInterval) {
      clearInterval(pollingInterval)
      setPollingInterval(null)
    }
  }

  const pollProcessingStatus = async (jobId: string) => {
    // Clear any existing polling
    stopPolling()

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/jobs/${jobId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        })

        if (response.ok) {
          const jobData = await response.json()

          if (jobData.status === 'completed') {
            setProcessingStatus('✅ PDF processed successfully! Ready for questions.')
            setProgressPercent(100)
            stopPolling()
            return
          } else if (jobData.status === 'failed') {
            setProcessingStatus('❌ PDF processing failed. Please try uploading again.')
            setProgressPercent(0)
            stopPolling()
            return
          } else if (jobData.status === 'active' && jobData.progress) {
            // Extract the detailed status message from the worker
            const statusMessage = jobData.progress.message || `Processing... ${jobData.progress.percent || 0}%`
            const percent = jobData.progress.percent || 0

            setProcessingStatus(statusMessage)
            setProgressPercent(percent)
          } else {
            setProcessingStatus('⏳ PDF queued for processing...')
            setProgressPercent(0)
          }
        } else {
          // HTTP error - stop polling
          setProcessingStatus('❓ Unable to check processing status')
          stopPolling()
        }
      } catch (error) {
        console.error('Error polling job status:', error)
        setProcessingStatus('❓ Unable to check processing status')
        stopPolling()
      }
    }, 2000)

    setPollingInterval(pollInterval)

    // Stop polling after 2 minutes as fallback
    setTimeout(() => {
      if (pollingInterval) {
        stopPolling()
        if (processingStatus && !processingStatus.includes('✅') && !processingStatus.includes('❌')) {
          setProcessingStatus('⏰ Processing is taking longer than expected...')
        }
      }
    }, 120000)
  }

  // Cleanup polling on component unmount
  useEffect(() => {
    return () => {
      stopPolling()
    }
  }, [])

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
            <div className={`mt-4 p-4 rounded-lg ${
              processingStatus.includes('✅')
                ? 'bg-green-50 border border-green-200 text-green-800'
                : processingStatus.includes('❌')
                ? 'bg-red-50 border border-red-200 text-red-800'
                : 'bg-blue-50 border border-blue-200 text-blue-800'
            }`}>
              <div className="flex justify-between items-center mb-2">
                <p className="text-sm font-medium">{processingStatus}</p>
                {!processingStatus.includes('✅') && !processingStatus.includes('❌') && (
                  <span className="text-xs font-bold">{progressPercent}%</span>
                )}
              </div>

              {/* Progress bar for active processing */}
              {!processingStatus.includes('✅') && !processingStatus.includes('❌') && progressPercent > 0 && (
                <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${progressPercent}%` }}
                  ></div>
                </div>
              )}

              {jobId && (
                <p className="text-xs mt-2 opacity-75 font-mono">Job ID: {jobId}</p>
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
