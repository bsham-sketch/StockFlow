import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import api, { getErrorMessage } from "../api/client";
import ProductImage from "../components/ProductImage";
import { formatPrice, formatProductName } from "../utils/format";
import { EmptyState, InlineError, LoadingState, PageHeading, TableWrap } from "./DashboardPage";

export default function ProductsPage() {
  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      api.get("/products", { params: search.trim() ? { search: search.trim() } : {} })
        .then(({ data }) => active && setProducts(data))
        .catch((requestError) => active && setError(getErrorMessage(requestError)))
        .finally(() => active && setLoading(false));
    }, 250);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [search]);

  const removeProduct = async (product) => {
    if (!window.confirm(`Delete "${product.name}"? This action cannot be undone.`)) return;
    try {
      await api.delete(`/products/${product.id}`);
      setProducts((current) => current.filter((item) => item.id !== product.id));
      toast.success("Product deleted.");
    } catch (requestError) {
      const message = getErrorMessage(requestError);
      setError(message);
      toast.error(message);
    }
  };

  const adjustStock = async (product, delta) => {
    const note = window.prompt(`Add a note for this ${delta > 0 ? "stock increase" : "stock decrease"}:`);
    if (note === null) return;
    if (!note.trim()) {
      setError("A note is required for stock adjustments.");
      toast.error("A note is required for stock adjustments.");
      return;
    }
    try {
      const { data } = await api.post(`/products/${product.id}/adjust`, { delta, note: note.trim() });
      setProducts((items) => items.map((item) => item.id === data.id ? data : item));
      toast.success("Stock updated.");
    } catch (requestError) {
      const message = getErrorMessage(requestError);
      setError(message);
      toast.error(message);
    }
  };

  return (
    <div>
      <PageHeading
        title="Products"
        subtitle="Manage the products and quantities in your catalog."
        action={<Link className="primary-button" to="/products/new">Add product</Link>}
      />
      <div className="mt-7 max-w-md">
        <label className="sr-only" htmlFor="search">Search by name or SKU</label>
        <input id="search" className="field mt-0" type="search" placeholder="Search by name or SKU..." value={search} onChange={(event) => setSearch(event.target.value)} />
      </div>
      {error && <InlineError message={error} />}
      {loading ? <LoadingState label="Loading products..." /> : (
        <section className="mt-5 overflow-hidden rounded-2xl border border-border bg-surface">
          {products.length === 0 ? (
            <EmptyState title={search ? "No matching products" : "No products yet"} message={search ? "Try another name or SKU." : "Add your first product to start tracking stock."} />
          ) : (
            <TableWrap>
              <table className="min-w-full divide-y divide-border text-sm">
                <thead className="text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-5 py-3.5">Image</th>
                    <th className="px-5 py-3.5">Name</th><th className="px-5 py-3.5">SKU</th>
                    <th className="px-5 py-3.5">Quantity</th><th className="px-5 py-3.5">Threshold</th><th className="px-5 py-3.5">Status</th>
                    <th className="px-5 py-3.5">Selling price</th><th className="px-5 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/70">
                  {products.map((product) => {
                    const name = formatProductName(product.name);
                    return (
                      <tr key={product.id} className="hover:bg-white/[0.02]">
                        <td className="px-5 py-3"><ProductImage imageUrl={product.image_url} alt={name} className="h-11 w-11" /></td>
                        <td className="whitespace-nowrap px-5 py-4 font-medium text-slate-100">{name}</td>
                        <td className="whitespace-nowrap px-5 py-4 text-slate-400">{product.sku}</td>
                        <td className="whitespace-nowrap px-5 py-4 font-medium text-slate-200">{product.quantity_on_hand}</td>
                        <td className="whitespace-nowrap px-5 py-4 text-slate-400">{product.effective_threshold}</td>
                        <td className="whitespace-nowrap px-5 py-4">
                          <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${
                            product.status === "Out of stock"
                              ? "border-red-900/60 bg-red-950/40 text-red-300"
                              : product.status === "Low stock"
                                ? "border-amber-900/60 bg-amber-950/40 text-amber-300"
                                : "border-emerald-900/60 bg-emerald-950/40 text-emerald-300"
                          }`}>{product.status}</span>
                        </td>
                        <td className="whitespace-nowrap px-5 py-4 text-slate-400">{formatPrice(product.selling_price)}</td>
                        <td className="whitespace-nowrap px-5 py-4">
                          <div className="flex justify-end gap-2">
                            <button className="secondary-button h-8 w-8 px-0" title="Increase stock" aria-label={`Increase ${name} stock`} onClick={() => adjustStock(product, 1)}>+</button>
                            <button className="secondary-button h-8 w-8 px-0" title="Decrease stock" aria-label={`Decrease ${name} stock`} onClick={() => adjustStock(product, -1)}>-</button>
                            <Link className="secondary-button px-3 py-1.5" to={`/products/${product.id}/edit`}>Edit</Link>
                            <button className="secondary-button border-red-900/70 px-3 py-1.5 text-red-300 hover:bg-red-950/50" onClick={() => removeProduct({ ...product, name })}>Delete</button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </TableWrap>
          )}
        </section>
      )}
    </div>
  );
}
