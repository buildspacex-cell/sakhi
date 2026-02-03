'use client'

import { useState, useEffect, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'

interface LinkResult {
  success: boolean
  agent_id?: string
  agent_name?: string
  platform?: string
  error?: string
}

function LinkDeviceContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const codeFromUrl = searchParams.get('code') || ''

  const [code, setCode] = useState(codeFromUrl)
  const [status, setStatus] = useState<'input' | 'loading' | 'success' | 'error'>('input')
  const [result, setResult] = useState<LinkResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleConfirm = async () => {
    const cleanCode = code.replace('-', '')
    if (cleanCode.length !== 8) {
      setError('Please enter a valid 8-character code')
      return
    }

    setStatus('loading')
    setError(null)

    try {
      const response = await fetch('/api/agent/link/confirm', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code: cleanCode }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Error: ${response.status}`)
      }

      const data = await response.json()
      setResult(data)
      setStatus('success')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to link device')
      setStatus('error')
    }
  }

  // Auto-submit if code is in URL
  useEffect(() => {
    if (codeFromUrl && codeFromUrl.length === 8) {
      handleConfirm()
    }
  }, [codeFromUrl])

  const formatCode = (input: string) => {
    const clean = input.replace(/[^a-zA-Z0-9]/g, '').toUpperCase()
    if (clean.length > 4) {
      return clean.slice(0, 4) + '-' + clean.slice(4, 8)
    }
    return clean
  }

  const handleCodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatCode(e.target.value)
    setCode(formatted)
  }

  const getPlatformName = (platform?: string) => {
    switch (platform) {
      case 'macos':
      case 'darwin':
        return 'Mac'
      case 'windows':
      case 'win32':
        return 'Windows'
      case 'linux':
        return 'Linux'
      default:
        return 'Desktop'
    }
  }

  return (
    <div className="w-full max-w-md">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-indigo-100 dark:bg-indigo-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-indigo-600 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Link Desktop Agent
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-2">
            Enter the code shown on your desktop to connect Sakhi Agent
          </p>
        </div>

        {/* Input State */}
        {status === 'input' && (
          <div className="space-y-6">
            <div>
              <label htmlFor="code" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Device Code
              </label>
              <input
                type="text"
                id="code"
                value={code}
                onChange={handleCodeChange}
                placeholder="XXXX-XXXX"
                maxLength={9}
                className="w-full px-4 py-4 text-center text-2xl font-mono font-bold tracking-widest border border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white uppercase"
                autoFocus
              />
            </div>

            {error && (
              <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
              </div>
            )}

            <button
              onClick={handleConfirm}
              disabled={code.replace('-', '').length !== 8}
              className="w-full py-4 px-6 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 text-white font-semibold rounded-xl transition-colors disabled:cursor-not-allowed"
            >
              Confirm &amp; Link Device
            </button>
          </div>
        )}

        {/* Loading State */}
        {status === 'loading' && (
          <div className="text-center py-8">
            <div className="w-12 h-12 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400">Linking your device...</p>
          </div>
        )}

        {/* Success State */}
        {status === 'success' && result && (
          <div className="text-center space-y-6">
            <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto">
              <svg className="w-8 h-8 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">Device Linked!</h2>
              <p className="text-gray-500 dark:text-gray-400 mt-2">
                Your {getPlatformName(result.platform)} device is now connected to Sakhi.
              </p>
            </div>

            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                <span className="font-medium">{result.agent_name || 'Desktop Agent'}</span>
              </p>
            </div>

            <div className="space-y-3">
              <button
                onClick={() => router.push('/experience/converse')}
                className="w-full py-3 px-6 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl transition-colors"
              >
                Go to Sakhi
              </button>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                You can now close this page. The agent on your desktop will start automatically.
              </p>
            </div>
          </div>
        )}

        {/* Error State */}
        {status === 'error' && (
          <div className="text-center space-y-6">
            <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto">
              <svg className="w-8 h-8 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">Link Failed</h2>
              <p className="text-gray-500 dark:text-gray-400 mt-2">
                {error || 'Something went wrong. Please try again.'}
              </p>
            </div>
            <button
              onClick={() => {
                setStatus('input')
                setError(null)
                setCode('')
              }}
              className="w-full py-3 px-6 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl transition-colors"
            >
              Try Again
            </button>
          </div>
        )}
      </div>

      {/* Help text */}
      <p className="text-center text-sm text-gray-500 dark:text-gray-400 mt-6">
        {"Don't have the Sakhi Agent? "}
        <a href="/download" className="text-indigo-600 dark:text-indigo-400 hover:underline">
          Download it here
        </a>
      </p>
    </div>
  )
}

function LoadingFallback() {
  return (
    <div className="w-full max-w-md">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8">
        <div className="text-center">
          <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4 animate-pulse" />
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mx-auto mb-4 animate-pulse" />
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full mx-auto animate-pulse" />
        </div>
      </div>
    </div>
  )
}

export default function LinkDevicePage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
      <Suspense fallback={<LoadingFallback />}>
        <LinkDeviceContent />
      </Suspense>
    </div>
  )
}
