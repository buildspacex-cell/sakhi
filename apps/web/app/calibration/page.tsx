"use client";

import { useRouter } from 'next/navigation';
import { useState } from 'react';

type Depth = 'light' | 'medium' | 'deep';
type Verbosity = 'brief' | 'standard' | 'detailed';

const depthOptions: Depth[] = ['light', 'medium', 'deep'];
const verbosityOptions: Verbosity[] = ['brief', 'standard', 'detailed'];

export default function CalibrationPage() {
  const router = useRouter();
  const [depth, setDepth] = useState<Depth>('medium');
  const [verbosity, setVerbosity] = useState<Verbosity>('standard');

  const savePreferences = async () => {
    try {
      await fetch('/api/preferences', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reflection_depth: depth,
          response_verbosity: verbosity,
        }),
      });
    } catch (_) {
      // Silent by design; preferences are soft and optional.
    } finally {
      router.push('/journal');
    }
  };

  return (
    <main
      className="min-h-screen w-full flex items-center justify-center px-6 py-16"
      style={{ backgroundColor: '#F6F4F0', color: '#2F2F2F' }}
    >
      <section className="w-full max-w-xl space-y-10 text-left">
        <div className="space-y-6">
          <h1 className="text-3xl font-light tracking-tight">Set how you want to listen.</h1>

          <div className="space-y-3">
            <p className="text-sm" style={{ color: '#2F2F2F' }}>
              Depth
            </p>
            <div className="flex gap-2">
              {depthOptions.map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setDepth(option)}
                  className={`px-4 py-2 text-sm rounded-sm border ${
                    depth === option ? 'border-black/20' : 'border-black/10'
                  } hover:opacity-80 focus:outline-none focus:ring-0`}
                  aria-pressed={depth === option}
                >
                  {option}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <p className="text-sm" style={{ color: '#2F2F2F' }}>
              Verbosity
            </p>
            <div className="flex gap-2">
              {verbosityOptions.map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setVerbosity(option)}
                  className={`px-4 py-2 text-sm rounded-sm border ${
                    verbosity === option ? 'border-black/20' : 'border-black/10'
                  } hover:opacity-80 focus:outline-none focus:ring-0`}
                  aria-pressed={verbosity === option}
                >
                  {option}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center">
          <button
            type="button"
            onClick={savePreferences}
            className="border border-black/10 text-sm font-medium px-6 py-2 rounded-sm hover:opacity-80 focus:outline-none focus:ring-0"
            aria-label="Save preferences and continue"
          >
            Continue
          </button>
        </div>
      </section>
    </main>
  );
}
