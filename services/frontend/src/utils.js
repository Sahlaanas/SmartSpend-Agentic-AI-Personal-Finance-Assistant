const rupees = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export const formatRs = (amount) => rupees.format(amount);

const pad = (n) => String(n).padStart(2, "0");

export function currentMonth() {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`;
}

export function previousMonth(month) {
  const [year, mon] = month.split("-").map(Number);
  const d = new Date(year, mon - 2, 1); // JS months are 0-based, so mon - 2 is the month before
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`;
}

export function monthLabel(month) {
  const [year, mon] = month.split("-").map(Number);
  return new Date(year, mon - 1, 1).toLocaleString("en-IN", { month: "long", year: "numeric" });
}

// null when there is nothing to compare against (previous is 0)
export function percentChange(current, previous) {
  if (!previous) return null;
  return ((current - previous) / previous) * 100;
}