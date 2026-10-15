import { useEffect, useState } from "react";
import { getBudgetStatus, getLatestMonth, getMonthlySummary } from "./api";
import { currentMonth, monthLabel, previousMonth } from "./utils";
import AnomalyPanel from "./components/AnomalyPanel.jsx";
import BudgetAlerts from "./components/BudgetAlerts.jsx";
import BudgetPanel from "./components/BudgetPanel.jsx";
import CategoryChart from "./components/CategoryChart.jsx";
import ChatPanel from "./components/ChatPanel.jsx";
import SummaryCards from "./components/SummaryCards.jsx";
import TransactionsTable from "./components/TransactionsTable.jsx";
import UploadButton from "./components/UploadButton.jsx";

export default function App() {
  const [month, setMonth] = useState(null);          // "YYYY-MM"
  const [current, setCurrent] = useState(null);      // summary of the selected month
  const [previous, setPrevious] = useState(null);    // summary of the month before
  const [budgets, setBudgets] = useState(null);      // budget status for the selected month
  const [error, setError] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);   // bump it to reload everything

  const reload = () => setRefreshKey((k) => k + 1);

  // On first load, open the month of the newest transaction
  useEffect(() => {
    getLatestMonth()
      .then((latest) => setMonth(latest ?? currentMonth()))
      .catch((err) => {
        setError(err.message);
        setMonth(currentMonth());
      });
  }, []);

  // Whenever the month changes (or something was uploaded/changed), load everything
  useEffect(() => {
    if (!month) return;
    let cancelled = false; // ignore answers that arrive after the user already switched month
    setError(null);
    Promise.all([
      getMonthlySummary(month),
      getMonthlySummary(previousMonth(month)),
      getBudgetStatus(month),
    ])
      .then(([cur, prev, budgetStatus]) => {
        if (cancelled) return;
        setCurrent(cur);
        setPrevious(prev);
        setBudgets(budgetStatus);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [month, refreshKey]);

  // Keep showing the old month (dimmed) while the new one loads, instead of unmounting
  // everything. That also keeps the chat conversation alive when you change month.
  const hasData = current && previous && budgets;
  const loading = !hasData || current.month !== month;

  return (
    <div className="app">
      <header className="topbar">
        <h1>SmartSpend</h1>
        <div className="topbar-actions">
          {month && (
            <input
              type="month"
              aria-label="Month"
              value={month}
              onChange={(e) => e.target.value && setMonth(e.target.value)}
            />
          )}
          <UploadButton onUploaded={reload} />
        </div>
      </header>

      {error && <div className="banner error">{error}</div>}

      {!hasData ? (
        !error && <p className="muted">Loading…</p>
      ) : (
        <main className={loading ? "loading" : ""}>
          <h2 className="month-title">{monthLabel(current.month)}</h2>
          <BudgetAlerts report={budgets} />
          <SummaryCards current={current} previous={previous} />
          <CategoryChart current={current} previous={previous} />
          <div className="grid-2">
            <BudgetPanel report={budgets} onChanged={reload} />
            <AnomalyPanel month={month} refreshKey={refreshKey} />
          </div>
          <ChatPanel />
          <TransactionsTable
            key={month}
            month={month}
            refreshKey={refreshKey}
            categories={current.categories.map((c) => c.category)}
          />
        </main>
      )}
    </div>
  );
}