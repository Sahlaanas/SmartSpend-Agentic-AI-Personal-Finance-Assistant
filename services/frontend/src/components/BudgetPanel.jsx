import { useState } from "react";
import { deleteBudget, setBudget } from "../api";
import { formatRs } from "../utils";

// Same list the backend accepts ("Total" = all spending together)
const CATEGORIES = [
  "Total", "Groceries", "Food", "Transport", "Shopping",
  "Bills", "Entertainment", "Health", "Rent", "Other",
];

function statusText(b) {
  if (b.status === "exceeded") return `Over budget by ${formatRs(-b.remaining)}`;
  return `${formatRs(b.remaining)} left (${b.percent_used}% used)`;
}

export default function BudgetPanel({ report, onChanged }) {
  const [category, setCategory] = useState("Food");
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function save(event) {
    event.preventDefault();
    const limit = Number(amount);
    if (!(limit > 0)) {
      setError("Enter an amount greater than 0.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await setBudget(category, limit);
      setAmount("");
      onChanged();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function remove(name) {
    setError(null);
    try {
      await deleteBudget(name);
      onChanged();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="panel">
      <h3>Budgets</h3>

      {report.budgets.length === 0 ? (
        <p className="muted">No budgets yet. Add one below.</p>
      ) : (
        <ul className="budgets">
          {report.budgets.map((b) => (
            <li key={b.category} className={`budget ${b.status}`}>
              <div className="budget-head">
                <strong>{b.category}</strong>
                <span className="budget-amounts">
                  {formatRs(b.spent)} of {formatRs(b.monthly_limit)}
                </span>
                <button
                  type="button"
                  className="icon"
                  aria-label={`Remove ${b.category} budget`}
                  onClick={() => remove(b.category)}
                >
                  ×
                </button>
              </div>
              <div className="bar">
                <div className="bar-fill" style={{ width: `${Math.min(b.percent_used, 100)}%` }} />
              </div>
              <div className="budget-foot">{statusText(b)}</div>
            </li>
          ))}
        </ul>
      )}

      <form className="budget-form" onSubmit={save}>
        <select aria-label="Budget category" value={category} onChange={(e) => setCategory(e.target.value)}>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <input
          type="number"
          aria-label="Monthly limit"
          placeholder="Monthly limit (₹)"
          min="1"
          step="0.01"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
        <button type="submit" className="primary" disabled={busy}>
          {busy ? "Saving…" : "Save budget"}
        </button>
      </form>
      {error && <div className="banner error small">{error}</div>}
    </section>
  );
}