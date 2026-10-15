import { formatRs, monthLabel, percentChange } from "../utils";

export default function SummaryCards({ current, previous }) {
  const difference = current.total - previous.total;
  const percent = percentChange(current.total, previous.total);
  const top = current.categories[0];

  let changeText = "No data for last month";
  let changeClass = "";
  if (previous.total > 0) {
    const sign = difference > 0 ? "+" : "";
    changeText = `${sign}${formatRs(difference)}`;
    if (percent !== null) changeText += ` (${sign}${percent.toFixed(1)}%)`;
    changeClass = difference > 0 ? "up" : difference < 0 ? "down" : "";
  }

  return (
    <section className="cards">
      <div className="card">
        <span className="card-label">Total spent</span>
        <span className="card-value">{formatRs(current.total)}</span>
      </div>
      <div className="card">
        <span className="card-label">Transactions</span>
        <span className="card-value">{current.count}</span>
      </div>
      <div className="card">
        <span className="card-label">Change vs {monthLabel(previous.month)}</span>
        <span className={`card-value small ${changeClass}`}>{changeText}</span>
      </div>
      <div className="card">
        <span className="card-label">Top category</span>
        <span className="card-value small">
          {top ? `${top.category} · ${formatRs(top.total)}` : "—"}
        </span>
      </div>
    </section>
  );
}