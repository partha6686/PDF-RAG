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
  const [chats, setChats] = useState<Chat[]>([])
  const [selectedChat, setSelectedChat] = useState<Chat | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showNewChatForm, setShowNewChatForm] = useState(false)
  const [newChatTitle, setNewChatTitle] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Fetch chats when document changes
  useEffect(() => {
    if (document) {
      fetchChats()
    } else {
      setChats([])
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

  const fetchChats = async () => {
    if (!document) return

    try {
      const response = await fetch(`http://localhost:8000/api/chat/document/${document.document_id}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setChats(data.chats || [])
        
        // Auto-select first chat if available
        if (data.chats && data.chats.length > 0) {
          setSelectedChat(data.chats[0])
        }
      }
    } catch (error) {
      console.error('Failed to fetch chats:', error)
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

  const createNewChat = async () => {
    if (!document || !newChatTitle.trim()) return

    try {
      const response = await fetch('http://localhost:8000/api/chat/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          title: newChatTitle.trim(),
          document_id: document.document_id,
        }),
      })

      if (response.ok) {
        const newChat = await response.json()
        setChats(prev => [newChat, ...prev])
        setSelectedChat(newChat)
        setNewChatTitle('')
        setShowNewChatForm(false)
      } else {
        const error = await response.json()
        alert(`Failed to create chat: ${error.detail}`)
      }
    } catch (error) {
      console.error('Failed to create chat:', error)
      alert('Failed to create chat. Please try again.')
    }
  }

  const sendMessage = async () => {
    if (!inputMessage.trim() || !selectedChat) return

    setIsLoading(true)
    const tempMessage: Message = {
      message_id: 'temp-' + Date.now(),
      chat_id: selectedChat.chat_id,
      role: 'user',
      content: inputMessage,
      created_at: new Date().toISOString(),
    }

    setMessages(prev => [...prev, tempMessage])
    const messageToSend = inputMessage
    setInputMessage('')

    try {
      const response = await fetch(`http://localhost:8000/api/chat/${selectedChat.chat_id}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ message: messageToSend }),
      })

      if (response.ok) {
        const data = await response.json()
        
        // Remove temp message and add real messages
        setMessages(prev => prev.filter(m => m.message_id !== tempMessage.message_id))
        
        // Fetch updated messages to get both user and assistant messages
        await fetchMessages()
        
        // Update chat list (in case chat was updated)
        await fetchChats()
      } else {
        throw new Error('Failed to send message')
      }
    } catch (error) {
      console.error('Send message error:', error)
      
      // Remove temp message and add error message
      setMessages(prev => [
        ...prev.filter(m => m.message_id !== tempMessage.message_id),
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

  const deleteChat = async (chatId: string) => {
    if (!confirm('Are you sure you want to delete this chat?')) return

    try {
      const response = await fetch(`http://localhost:8000/api/chat/${chatId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })

      if (response.ok) {
        setChats(prev => prev.filter(c => c.chat_id !== chatId))
        if (selectedChat?.chat_id === chatId) {
          setSelectedChat(null)
          setMessages([])
        }
      }
    } catch (error) {
      console.error('Failed to delete chat:', error)
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
    <div className="flex-1 flex">
      {/* Chat List */}
      <div className="w-64 bg-gray-50 border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-medium text-gray-900">Chats</h3>
            <button
              onClick={() => setShowNewChatForm(true)}
              className="p-1 text-gray-500 hover:text-blue-600 transition-colors"
              title="New chat"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            </button>
          </div>

          {showNewChatForm && (
            <div className="mb-3 p-2 bg-white rounded border">
              <input
                type="text"
                value={newChatTitle}
                onChange={(e) => setNewChatTitle(e.target.value)}
                placeholder="Chat title..."
                className="w-full p-2 text-sm border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    createNewChat()
                  } else if (e.key === 'Escape') {
                    setShowNewChatForm(false)
                    setNewChatTitle('')
                  }
                }}
                autoFocus
              />
              <div className="flex justify-end space-x-1 mt-2">
                <button
                  onClick={() => {
                    setShowNewChatForm(false)
                    setNewChatTitle('')
                  }}
                  className="px-2 py-1 text-xs text-gray-500 hover:text-gray-700"
                >
                  Cancel
                </button>
                <button
                  onClick={createNewChat}
                  disabled={!newChatTitle.trim()}
                  className="px-2 py-1 text-xs bg-blue-600 text-white rounded disabled:bg-gray-300"
                >
                  Create
                </button>
              </div>
            </div>
          )}

          <div className="text-xs text-gray-500 mb-2">
            Document: {document.original_name}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {chats.length === 0 ? (
            <div className="text-center text-gray-500 mt-8">
              <p className="text-sm">No chats yet</p>
              <p className="text-xs mt-1">Create your first chat</p>
            </div>
          ) : (
            <div className="space-y-1">
              {chats.map((chat) => (
                <div
                  key={chat.chat_id}
                  className={`p-2 rounded cursor-pointer group flex items-center justify-between ${
                    selectedChat?.chat_id === chat.chat_id
                      ? 'bg-blue-100 text-blue-900'
                      : 'hover:bg-white'
                  }`}
                  onClick={() => setSelectedChat(chat)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">
                      {chat.title}
                    </div>
                    <div className="text-xs text-gray-500">
                      {new Date(chat.updated_at).toLocaleDateString()}
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      deleteChat(chat.chat_id)
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition-all"
                  >
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Chat Messages */}
      {selectedChat ? (
        <div className="flex-1 flex flex-col bg-white">
          <div className="p-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-800">{selectedChat.title}</h2>
            <p className="text-sm text-gray-600">Chat with {document.original_name}</p>
          </div>

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

          <div className="p-4 border-t border-gray-200">
            <div className="flex space-x-2">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Ask a question about this document..."
                className="flex-1 p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
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
      ) : (
        <div className="flex-1 flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Chat Selected</h3>
            <p className="text-gray-500">Create a new chat to start asking questions about this document</p>
          </div>
        </div>
      )}
    </div>
  )
}