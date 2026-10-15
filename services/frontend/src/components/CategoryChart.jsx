import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatRs, monthLabel } from "../utils";

const compact = new Intl.NumberFormat("en-IN", { notation: "compact" });

// One row per category with this month's and last month's spending side by side
export function buildChartData(current, previous) {
  const totals = (summary) => Object.fromEntries(summary.categories.map((c) => [c.category, c.total]));
  const now = totals(current);
  const before = totals(previous);
  const names = [...new Set([...Object.keys(now), ...Object.keys(before)])];

  return names
    .map((category) => ({
      category,
      thisMonth: now[category] ?? 0,
      lastMonth: before[category] ?? 0,
    }))
    .sort((a, b) => Math.max(b.thisMonth, b.lastMonth) - Math.max(a.thisMonth, a.lastMonth));
}

export default function CategoryChart({ current, previous }) {
  const data = buildChartData(current, previous);

  if (data.length === 0) {
    return (
      <section className="panel">
        <h3>Spending by category</h3>
        <p className="muted">No transactions in this period.</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <h3>Spending by category</h3>
      <div className="chart">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="category" />
            <YAxis tickFormatter={(v) => compact.format(v)} width={56} />
            <Tooltip formatter={(value) => formatRs(value)} />
            <Legend />
            <Bar dataKey="thisMonth" name={monthLabel(current.month)} fill="#2563eb" radius={[4, 4, 0, 0]} />
            <Bar dataKey="lastMonth" name={monthLabel(previous.month)} fill="#94a3b8" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}