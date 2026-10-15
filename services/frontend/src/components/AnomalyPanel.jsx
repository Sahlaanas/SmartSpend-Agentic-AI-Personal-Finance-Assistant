import { useEffect, useState } from "react";
import { getAnomalies } from "../api";
import { formatRs } from "../utils";

// Loads on its own, so if the anomaly service is slow or down the rest of the dashboard still works
export default function AnomalyPanel({ month, refreshKey }) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setResult(null);
    setError(null);
    getAnomalies(month)
      .then((data) => !cancelled && setResult(data))
      .catch((err) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [month, refreshKey]);

  return (
    <section className="panel">
      <h3>Unusual expenses</h3>

      {error && <div className="banner error small">{error}</div>}
      {!result && !error && <p className="muted">Analyzing…</p>}

      {result?.message && <p className="muted">{result.message}</p>}
      {result && !result.message && result.flagged.length === 0 && (
        <p className="muted">Nothing unusual this month.</p>
      )}

      {result?.flagged.map((f) => (
        <div className="anomaly" key={f.id}>
          <div className="anomaly-head">
            <strong>{f.description}</strong>
            <span className="num">{formatRs(f.amount)}</span>
          </div>
          <div className="anomaly-meta">
            {f.txn_date} · <span className="badge">{f.category ?? "Uncategorized"}</span>
          </div>
          <p className="anomaly-reason">{f.reason}</p>
        </div>
      ))}

      {result && !result.message && (
        <p className="muted tiny">Based on {result.trained_on} transactions of history.</p>
      )}
    </section>
  );
}