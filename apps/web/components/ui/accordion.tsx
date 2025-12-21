"use client";

import {
  createContext,
  PropsWithChildren,
  useContext,
  useMemo,
  useState,
} from "react";

interface AccordionContextValue {
  type: "single";
  value: string | null;
  setValue: (value: string) => void;
  collapsible: boolean;
}

const AccordionContext = createContext<AccordionContextValue | null>(null);

interface AccordionProps {
  defaultValue?: string | null;
  type?: "single";
  collapsible?: boolean;
  className?: string;
}

export function Accordion({
  defaultValue = null,
  type = "single",
  collapsible = false,
  className = "",
  children,
}: PropsWithChildren<AccordionProps>) {
  const [active, setActive] = useState<string | null>(defaultValue);

  const context = useMemo(
    () => ({
      type,
      value: active,
      setValue: (value: string) => {
        setActive((prev) => (collapsible && prev === value ? null : value));
      },
      collapsible,
    }),
    [active, collapsible, type],
  );

  return (
    <AccordionContext.Provider value={context}>
      <div className={className}>{children}</div>
    </AccordionContext.Provider>
  );
}

const ItemContext = createContext<string | null>(null);

interface ItemProps {
  value: string;
}

export function AccordionItem({ value, children }: PropsWithChildren<ItemProps>) {
  return (
    <ItemContext.Provider value={value}>
      <div>{children}</div>
    </ItemContext.Provider>
  );
}

export function AccordionTrigger({ children }: PropsWithChildren) {
  const accordion = useContext(AccordionContext);
  const itemValue = useContext(ItemContext);
  if (!accordion || !itemValue) {
    throw new Error("AccordionTrigger must be used within AccordionItem inside Accordion");
  }

  return (
    <button
      type="button"
      className="flex w-full items-center justify-between gap-2 py-2"
      onClick={() => accordion.setValue(itemValue)}
    >
      {children}
    </button>
  );
}

export function AccordionContent({ children }: PropsWithChildren) {
  const accordion = useContext(AccordionContext);
  const itemValue = useContext(ItemContext);
  if (!accordion || !itemValue) {
    throw new Error("AccordionContent must be used within AccordionItem inside Accordion");
  }

  const open = accordion.value === itemValue;

  return (
    <div className="pb-3 text-sm text-slate-600" hidden={!open}>
      {children}
    </div>
  );
}
