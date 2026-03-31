"use client";

import type { ReactNode } from "react";

type SectionProps = {
  children: ReactNode;
  id?: string;
  label?: string;
  className?: string;
  contentClassName?: string;
};

export default function Section({
  children,
  id,
  label,
  className = "",
  contentClassName = "",
}: SectionProps) {
  return (
    <section
      id={id}
      data-story-section="true"
      data-story-label={label}
      className={`relative flex min-h-[100svh] snap-start items-center justify-center px-5 py-8 sm:px-8 lg:px-12 ${className}`}
    >
      <div className={`relative mx-auto w-full max-w-6xl ${contentClassName}`}>
        {children}
      </div>
    </section>
  );
}
