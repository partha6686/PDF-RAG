import { type Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import './globals.css'
import { AuthProvider } from './contexts/AuthContext'
import AuthWrapper from './components/AuthWrapper'

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
})

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
})

export const metadata: Metadata = {
  title: 'PDF RAG - FastAPI',
  description: 'PDF Retrieval-Augmented Generation with FastAPI',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <AuthProvider>
          <AuthWrapper>
            {children}
          </AuthWrapper>
        </AuthProvider>
      </body>
    </html>
  )
}
