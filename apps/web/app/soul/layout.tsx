"use client";

import React from "react";
import { SWRConfig, type SWRConfiguration } from "swr";

const fetcher = async (url: string) => {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
};

export default function SoulLayout({ children }: { children: React.ReactNode }): React.ReactElement {
  const swrValue: SWRConfiguration = {
    fetcher,
    dedupingInterval: 60_000,
    revalidateOnFocus: false,
    errorRetryInterval: 5_000,
    suspense: false,
  };
  const SwrProvider = SWRConfig as unknown as React.ComponentType<{
    value: SWRConfiguration;
    children: React.ReactNode;
  }>;

  return (
    <SwrProvider value={swrValue}>
      <div className="min-h-screen bg-gradient-to-b from-stone-50 via-white to-stone-100 text-stone-900">
        {children}
      </div>
    </SwrProvider>
  );
}
