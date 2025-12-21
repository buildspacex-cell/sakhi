import { useMemo } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

type RhythmDatum = {
  day: string;
  energy: number;
  mood: number;
};

type Props = {
  data: RhythmDatum[];
};

export default function RhythmDashboard({ data }: Props) {
  const chartData = useMemo(() => data ?? [], [data]);

  return (
    <div className="rounded-2xl bg-gradient-to-br from-indigo-50 to-white p-4 shadow-md">
      <h2 className="mb-2 text-lg font-semibold">Your Rhythm</h2>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={chartData}>
          <XAxis dataKey="day" />
          <YAxis domain={[0, 1]} />
          <Tooltip />
          <Area
            type="monotone"
            dataKey="energy"
            stroke="#6366F1"
            fill="#A5B4FC"
            fillOpacity={0.4}
          />
          <Area
            type="monotone"
            dataKey="mood"
            stroke="#F59E0B"
            fill="#FDE68A"
            fillOpacity={0.4}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
