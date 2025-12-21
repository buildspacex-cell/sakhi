"use client";

import useSWR from "swr";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function AlignmentPage() {
  const { data } = useSWR("/v1/alignment/today?person_id=me", fetcher, {
    revalidateOnFocus: false,
  });
  const map = data?.data?.alignment_map || {};
  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Daily Alignment View</h1>
      <div className="border rounded-lg p-4 bg-white/50 shadow-sm">
        <p className="text-sm text-gray-600">Energy profile: {map.energy_profile || "n/a"}</p>
        <p className="text-sm text-gray-600">Focus profile: {map.focus_profile || "n/a"}</p>
        <div>
          <h3 className="font-semibold mt-3">Recommended</h3>
          <ul className="list-disc ml-5 text-sm">
            {(map.recommended_actions || []).map((item: any) => (
              <li key={item.id || item.title}>{item.title} ({item.score})</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="font-semibold mt-3">Self-care</h3>
          <ul className="list-disc ml-5 text-sm">
            {(map.self_care_suggestions || []).map((s: string) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
