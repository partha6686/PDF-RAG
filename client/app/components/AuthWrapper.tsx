'use client'

import { useAuth } from '../contexts/AuthContext'
import Auth from './Auth'

export default function AuthWrapper({ children }: { children: React.ReactNode }) {
  const { user, isLoading, logout } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!user) {
    return <Auth />
  }

  return (
    <div className="w-full min-h-screen">
      <nav className="absolute top-0 right-0 p-4 z-10">
        <div className="flex items-center space-x-4">
          <span className="text-sm text-gray-600">Welcome, {user.name}</span>
          <button
            onClick={logout}
            className="bg-red-600 text-white px-3 py-1 rounded-md text-sm hover:bg-red-700 transition-colors"
          >
            Logout
          </button>
        </div>
      </nav>
      <div className="container">
        {children}
      </div>
    </div>
  )
}