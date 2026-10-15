import { useEffect, useState } from "react";
import { getTransactions } from "../api";
import { formatRs } from "../utils";

export default function TransactionsTable({ month, refreshKey, categories }) {
  const [category, setCategory] = useState("");
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    getTransactions({ month, category })
      .then((data) => !cancelled && setRows(data))
      .catch((err) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [month, category, refreshKey]);

  return (
    <section className="panel">
      <div className="panel-head">
        <h3>Transactions</h3>
        <select aria-label="Category filter" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {error && <div className="banner error">{error}</div>}
      {!rows && !error && <p className="muted">Loading…</p>}
      {rows && rows.length === 0 && <p className="muted">No transactions found.</p>}
      {rows && rows.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Description</th>
                <th>Category</th>
                <th className="num">Amount</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((t) => (
                <tr key={t.id}>
                  <td>{t.txn_date}</td>
                  <td>{t.description}</td>
                  <td><span className="badge">{t.category ?? "Uncategorized"}</span></td>
                  <td className="num">{formatRs(Number(t.amount))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}