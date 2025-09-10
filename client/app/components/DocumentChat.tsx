'use client'

import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { useAuth } from '../contexts/AuthContext'

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

interface Chat {
  chat_id: string
  user_id: string
  document_id: string
  title: string
  created_at: string
  updated_at: string
}

interface Message {
  message_id: string
  chat_id: string
  role: 'user' | 'assistant'
  content: string
  sources?: string
  created_at: string
}

interface DocumentChatProps {
  document: Document | null
}

export default function DocumentChat({ document }: DocumentChatProps) {
  const { token } = useAuth()
  const [selectedChat, setSelectedChat] = useState<Chat | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Get or create chat when document changes
  useEffect(() => {
    if (document) {
      getOrCreateChat()
    } else {
      setSelectedChat(null)
      setMessages([])
    }
  }, [document])

  // Fetch messages when chat changes
  useEffect(() => {
    if (selectedChat) {
      fetchMessages()
    } else {
      setMessages([])
    }
  }, [selectedChat])

  const getOrCreateChat = async () => {
    if (!document) return

    try {
      const response = await fetch(`http://localhost:8000/api/chat/document/${document.document_id}/get-or-create`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const chat = await response.json()
        setSelectedChat(chat)
      }
    } catch (error) {
      console.error('Failed to get or create chat:', error)
    }
  }

  const fetchMessages = async () => {
    if (!selectedChat) return

    try {
      const response = await fetch(`http://localhost:8000/api/chat/${selectedChat.chat_id}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setMessages(data.messages || [])
      }
    } catch (error) {
      console.error('Failed to fetch messages:', error)
    }
  }


  const sendMessage = async () => {
    if (!inputMessage.trim() || !selectedChat) return

    setIsLoading(true)
    const messageToSend = inputMessage
    setInputMessage('')

    // Add user message immediately and permanently
    const userMessage: Message = {
      message_id: 'user-' + Date.now(),
      chat_id: selectedChat.chat_id,
      role: 'user',
      content: messageToSend,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMessage])

    try {
      const response = await fetch(`http://localhost:8000/api/chat/${selectedChat.chat_id}/messages/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ message: messageToSend }),
      })

      if (response.ok) {
        // Stop loading indicator when streaming starts
        setIsLoading(false)

        // Create streaming assistant message
        const streamingMessage: Message = {
          message_id: 'streaming-' + Date.now(),
          chat_id: selectedChat.chat_id,
          role: 'assistant',
          content: '',
          created_at: new Date().toISOString(),
        }
        setMessages(prev => [...prev, streamingMessage])

        // Handle streaming response
        const reader = response.body?.getReader()
        const decoder = new TextDecoder()

        if (reader) {
          let buffer = ''

          while (true) {
            const { done, value } = await reader.read()

            if (done) break

            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop() || '' // Keep incomplete line in buffer

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6))

                  if (data.type === 'content') {
                    // Update streaming message with new content
                    setMessages(prev =>
                      prev.map(msg =>
                        msg.message_id === streamingMessage.message_id
                          ? { ...msg, content: msg.content + data.content }
                          : msg
                      )
                    )
                  } else if (data.type === 'done') {
                    // Replace streaming message with final message
                    setMessages(prev =>
                      prev.map(msg =>
                        msg.message_id === streamingMessage.message_id
                          ? { ...msg, message_id: 'final-' + Date.now() }
                          : msg
                      )
                    )
                    // Refresh messages to get the final stored message
                    await fetchMessages()
                  } else if (data.type === 'error') {
                    // Stop loading indicator on error
                    setIsLoading(false)
                    // Replace streaming message with error message
                    setMessages(prev =>
                      prev.map(msg =>
                        msg.message_id === streamingMessage.message_id
                          ? { ...msg, content: data.content, message_id: 'error-' + Date.now() }
                          : msg
                      )
                    )
                  }
                } catch (e) {
                  console.error('Error parsing streaming data:', e)
                }
              }
            }
          }
        }
      } else {
        throw new Error('Failed to send message')
      }
    } catch (error) {
      console.error('Send message error:', error)

      // Add error message
      setMessages(prev => [
        ...prev,
        {
          message_id: 'error-' + Date.now(),
          chat_id: selectedChat.chat_id,
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          created_at: new Date().toISOString(),
        }
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }


  if (!document) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-2">Select a Document</h3>
          <p className="text-gray-500">Choose a document from the sidebar to start chatting</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col bg-white">
      {/* Chat Header */}
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-800">
          {selectedChat ? selectedChat.title : document.original_name}
        </h2>
        <p className="text-sm text-gray-600">Chat with {document.original_name}</p>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.message_id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] p-3 rounded-lg ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white rounded-br-none'
                  : 'bg-gray-100 text-gray-800 rounded-bl-none'
              }`}
            >
              {message.role === 'assistant' ? (
                <div className="text-sm prose prose-sm max-w-none">
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                </div>
              ) : (
                <p className="text-sm">{message.content}</p>
              )}
              <p className={`text-xs mt-1 ${
                message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
              }`}>
                {new Date(message.created_at).toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-800 p-3 rounded-lg rounded-bl-none">
              <div className="flex items-center space-x-1">
                <div className="animate-bounce w-2 h-2 bg-gray-500 rounded-full"></div>
                <div className="animate-bounce w-2 h-2 bg-gray-500 rounded-full" style={{ animationDelay: '0.1s' }}></div>
                <div className="animate-bounce w-2 h-2 bg-gray-500 rounded-full" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Chat Input */}
      <div className="p-4 border-t border-gray-200">
        <div className="flex space-x-2">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Ask a question about this document..."
            className="flex-1 p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900 placeholder-gray-500"
            disabled={isLoading}
          />
          <button
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isLoading}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              inputMessage.trim() && !isLoading
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
