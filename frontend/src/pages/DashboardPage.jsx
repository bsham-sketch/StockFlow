import { useEffect, useState } from "react";
import api, { getErrorMessage } from "../api/client";
import { formatProductName } from "../utils/format";

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api.get("/dashboard")
      .then((response) => active && setData(response.data))
      .catch((requestError) => active && setError(getErrorMessage(requestError)))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, []);

  return (
    <div>
      <PageHeading title="Dashboard" subtitle="Here's what's happening with your inventory today." />
      {error && <InlineError message={error} />}
      {loading ? <LoadingState /> : data && (
        <>
          <div className="mt-7 grid gap-4 sm:grid-cols-2">
            <StatCard label="Total products" value={data.total_products.toLocaleString()} hint="Products in your catalog" icon="▦" />
            <StatCard label="Total units" value={data.total_quantity.toLocaleString()} hint="Units currently on hand" icon="◫" />
          </div>
          <section className="mt-7 overflow-hidden rounded-2xl border border-border bg-surface">
            <div className="flex items-center justify-between border-b border-border px-5 py-4 sm:px-6">
              <div>
                <h2 className="font-semibold text-white">Low stock items</h2>
                <p className="mt-1 text-sm text-muted">Products at or below their reorder threshold.</p>
              </div>
              <span className="rounded-full border border-amber-900/60 bg-amber-950/40 px-2.5 py-1 text-xs font-medium text-amber-300">{data.low_stock_items.length} {data.low_stock_items.length === 1 ? "item" : "items"}</span>
            </div>
            {data.low_stock_items.length ? (
              <TableWrap>
                <table className="min-w-full divide-y divide-border text-sm">
                  <thead className="text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                    <tr><th className="px-6 py-3">Name</th><th className="px-6 py-3">SKU</th><th className="px-6 py-3">Quantity</th><th className="px-6 py-3">Threshold</th></tr>
                  </thead>
                  <tbody className="divide-y divide-border/70">
                    {data.low_stock_items.map((item) => (
                      <tr key={item.sku} className="hover:bg-white/[0.02]">
                        <td className="whitespace-nowrap px-6 py-4 font-medium text-slate-100">{formatProductName(item.name)}</td>
                        <td className="whitespace-nowrap px-6 py-4 text-slate-400">{item.sku}</td>
                        <td className="whitespace-nowrap px-6 py-4 font-semibold text-amber-300">{item.quantity_on_hand}</td>
                        <td className="whitespace-nowrap px-6 py-4 text-slate-400">{item.threshold}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableWrap>
            ) : <EmptyState title="All stocked up" message="No products are currently at or below their low-stock threshold." />}
          </section>
        </>
      )}
    </div>
  );
}

export function PageHeading({ title, subtitle, action }) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div><h1 className="text-2xl font-bold tracking-tight text-white">{title}</h1><p className="mt-1.5 text-sm text-muted">{subtitle}</p></div>
      {action}
    </div>
  );
}

export function InlineError({ message }) {
  return <p role="alert" className="mt-5 rounded-xl border border-red-900/70 bg-red-950/40 px-4 py-3 text-sm text-red-300">{message}</p>;
}

export function LoadingState({ label = "Loading..." }) {
  return <div className="mt-7 rounded-2xl border border-border bg-surface px-6 py-12 text-center text-sm text-muted">{label}</div>;
}

export function EmptyState({ title, message }) {
  return <div className="px-6 py-12 text-center"><h3 className="font-semibold text-slate-100">{title}</h3><p className="mt-1.5 text-sm text-muted">{message}</p></div>;
}

export function TableWrap({ children }) {
  return <div className="overflow-x-auto">{children}</div>;
}

function StatCard({ label, value, hint, icon }) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-5 sm:p-6">
      <div className="flex items-start justify-between">
        <div><p className="text-sm font-medium text-muted">{label}</p><p className="mt-3 text-3xl font-bold tracking-tight text-white">{value}</p></div>
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue/15 text-xl text-blue-300">{icon}</span>
      </div>
      <p className="mt-2 text-sm text-slate-500">{hint}</p>
    </div>
  );
}
