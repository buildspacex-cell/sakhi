"use client";

import { useRouter } from "next/navigation";

const timelineEntries = [
  { meta: "Day 1 · Evening", text: "Long day. Back-to-back calls. Felt drained but didn’t really stop." },
  { meta: "Day 2 · Morning", text: "Didn’t sleep great. Woke up already thinking about work." },
  { meta: "Day 3 · Afternoon", text: "Why do I always take on more than I should?" },
  { meta: "Day 4 · Night", text: "Cancelled dinner plans. Too tired. Feel a bit guilty about it." },
  { meta: "Day 6 · Morning", text: "Energy better today. Had some quiet time before calls." },
  { meta: "Day 7 · Evening", text: "Exhausted again. Might be a pattern." },
];

export default function JournalPage() {
  const router = useRouter();

  return (
    <main
      className="min-h-screen w-full flex justify-center px-6 py-16"
      style={{ backgroundColor: "#0e0f12", color: "#f4f4f5" }}
    >
      <section className="w-full max-w-3xl space-y-10">
        <div className="space-y-4">
          <div className="text-xs uppercase tracking-[0.14em] text-[#a1a1aa]">Sakhi</div>
          <div className="text-lg font-medium tracking-tight text-[#f4f4f5]">Recent reflections</div>
          <div className="divide-y divide-[#27272a] border border-[#27272a] rounded-lg">
            {timelineEntries.map((entry) => (
              <div key={entry.meta} className="px-5 py-4 space-y-1">
                <div className="text-[13px] uppercase tracking-wide text-[#a1a1aa]">{entry.meta}</div>
              <div className="text-[17px] leading-relaxed text-[#f4f4f5]">{entry.text}</div>
            </div>
          ))}
          </div>
        </div>

        <div className="pt-2">
          <button
            type="button"
            onClick={() => router.push("/journal/reflection")}
            className="border border-[#3f3f46] text-sm font-medium px-6 py-2 rounded-sm text-[#e5e7eb] hover:opacity-80 focus:outline-none focus:ring-0"
          >
            Continue
          </button>
        </div>
      </section>
    </main>
  );
}
