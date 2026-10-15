import { formatRs } from "../utils";

// A banner at the top of the page for budgets that are exceeded or close to the limit
export default function BudgetAlerts({ report }) {
  const exceeded = report.budgets.filter((b) => b.status === "exceeded");
  const warning = report.budgets.filter((b) => b.status === "warning");
  if (exceeded.length === 0 && warning.length === 0) return null;

  return (
    <div className="alerts" role="alert" aria-label="Budget alerts">
      {exceeded.map((b) => (
        <div className="alert exceeded" key={b.category}>
          {b.category} budget exceeded by {formatRs(-b.remaining)} ({formatRs(b.spent)} of{" "}
          {formatRs(b.monthly_limit)})
        </div>
      ))}
      {warning.map((b) => (
        <div className="alert warning" key={b.category}>
          {b.category} is at {b.percent_used}% of its budget ({formatRs(b.remaining)} left)
        </div>
      ))}
    </div>
  );
}