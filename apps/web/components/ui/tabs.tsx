"use client";

import {
  createContext,
  PropsWithChildren,
  useContext,
  useMemo,
  useState,
} from "react";

interface TabsContextValue {
  value: string;
  setValue: (value: string) => void;
}

const TabsContext = createContext<TabsContextValue | null>(null);

interface TabsProps {
  defaultValue: string;
  className?: string;
}

export function Tabs({ defaultValue, className = "", children }: PropsWithChildren<TabsProps>) {
  const [value, setValue] = useState(defaultValue);
  const ctx = useMemo(() => ({ value, setValue }), [value]);

  return (
    <TabsContext.Provider value={ctx}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  );
}

export function TabsList({ children }: PropsWithChildren) {
  return <div className="mb-2 inline-flex rounded border border-slate-200 bg-slate-50 text-xs">{children}</div>;
}

export function TabsTrigger({ value, children }: PropsWithChildren<{ value: string }>) {
  const ctx = useContext(TabsContext);
  if (!ctx) throw new Error("TabsTrigger must be used within Tabs");
  const active = ctx.value === value;
  return (
    <button
      type="button"
      onClick={() => ctx.setValue(value)}
      className={`px-3 py-1 ${active ? "bg-white shadow-sm" : "text-slate-500"}`}
    >
      {children}
    </button>
  );
}

export function TabsContent({ value, children }: PropsWithChildren<{ value: string }>) {
  const ctx = useContext(TabsContext);
  if (!ctx) throw new Error("TabsContent must be used within Tabs");
  if (ctx.value !== value) return null;
  return <div>{children}</div>;
}
