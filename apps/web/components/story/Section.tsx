import type { ReactNode } from "react";

type SectionProps = {
  children: ReactNode;
  id?: string;
  className?: string;
  contentClassName?: string;
};

export default function Section({
  children,
  id,
  className = "",
  contentClassName = "",
}: SectionProps) {
  return (
    <section
      id={id}
      data-story-section="true"
      className={`relative flex min-h-[120svh] items-center justify-center px-5 pb-16 pt-28 sm:px-8 sm:pb-20 sm:pt-32 lg:px-12 lg:pb-24 lg:pt-36 ${className}`}
    >
      <div className={`relative mx-auto w-full max-w-6xl ${contentClassName}`}>
        {children}
      </div>
    </section>
  );
}
