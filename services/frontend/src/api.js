// All backend calls live here. The browser only talks to /api/*, and nginx (or the Vite
// dev server) forwards each prefix to the right service.
const TX = "/api/tx";
const ANOMALY = "/api/anomaly";
const AGENT = "/api/agent";

async function request(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      // the response had no JSON body; keep the status text
    }
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

const jsonBody = (method, body) => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

// ---- transactions ----
export const getMonthlySummary = (month) => request(`${TX}/summary/monthly?month=${month}`);

export function getTransactions({ month, category, limit = 200 }) {
  const params = new URLSearchParams({ limit });
  if (month) params.set("month", month);
  if (category) params.set("category", category);
  return request(`${TX}/transactions?${params}`);
}

// The month of the newest transaction, so the dashboard opens on a month that has data.
export async function getLatestMonth() {
  const [latest] = await getTransactions({ limit: 1 });
  return latest ? latest.txn_date.slice(0, 7) : null;
}

export function uploadStatement(file) {
  const form = new FormData();
  form.append("file", file);
  return request(`${TX}/transactions/upload`, { method: "POST", body: form });
}

// ---- budgets ----
export const getBudgetStatus = (month) => request(`${TX}/budgets/status?month=${month}`);

export const setBudget = (category, monthlyLimit) =>
  request(`${TX}/budgets/${encodeURIComponent(category)}`, jsonBody("PUT", { monthly_limit: monthlyLimit }));

export const deleteBudget = (category) =>
  request(`${TX}/budgets/${encodeURIComponent(category)}`, { method: "DELETE" });

// ---- unusual expenses (anomaly service) ----
export const getAnomalies = (month) => request(`${ANOMALY}/anomalies?month=${month}`);

// ---- chat (agent service) ----
export const sendChatMessage = (message, threadId) =>
  request(`${AGENT}/chat`, jsonBody("POST", { message, thread_id: threadId }));