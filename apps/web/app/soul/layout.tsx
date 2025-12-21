"use client";

import React from "react";
import { SWRConfig } from "swr";

const fetcher = async (url: string) => {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
};

export default function SoulLayout({ children }: { children: React.ReactNode }) {
  return (
    <SWRConfig
      value={{
        fetcher,
        dedupingInterval: 60_000,
        revalidateOnFocus: false,
        errorRetryInterval: 5_000,
        suspense: false,
      }}
    >
      <div className="min-h-screen bg-gradient-to-b from-stone-50 via-white to-stone-100 text-stone-900">
        {children}
      </div>
    </SWRConfig>
  );
}
