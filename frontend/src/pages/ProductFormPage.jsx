import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import api, { getErrorMessage } from "../api/client";
import { InlineError, LoadingState, PageHeading } from "./DashboardPage";

const initialForm = {
  name: "",
  sku: "",
  description: "",
  quantity_on_hand: "0",
  cost_price: "",
  selling_price: "",
  low_stock_threshold: "",
  image_url: "",
};

function NumberField({ id, label, value, onChange, ...props }) {
  return (
    <div>
      <label className="label" htmlFor={id}>{label}</label>
      <input className="field" id={id} name={id} type="number" value={value} onChange={onChange} {...props} />
    </div>
  );
}

export default function ProductFormPage() {
  const { productId } = useParams();
  const editing = Boolean(productId);
  const navigate = useNavigate();
  const [form, setForm] = useState(initialForm);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(editing);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!editing) return;
    let active = true;
    api.get(`/products/${productId}`)
      .then(({ data }) => {
        if (active) {
          setForm({
            name: data.name,
            sku: data.sku,
            description: data.description || "",
            quantity_on_hand: String(data.quantity_on_hand),
            cost_price: data.cost_price ?? "",
            selling_price: data.selling_price ?? "",
            low_stock_threshold: data.low_stock_threshold ?? "",
            image_url: data.image_url ?? "",
          });
        }
      })
      .catch((requestError) => active && setError(getErrorMessage(requestError)))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [editing, productId]);

  const change = (event) => {
    setForm({ ...form, [event.target.name]: event.target.value });
    setError("");
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!form.name.trim() || !form.sku.trim()) return setError("Name and SKU are required.");
    const numericFields = [
      ["Quantity on hand", form.quantity_on_hand],
      ["Cost price", form.cost_price],
      ["Selling price", form.selling_price],
      ["Low stock threshold", form.low_stock_threshold],
    ];
    for (const [label, raw] of numericFields) {
      if (raw !== "" && (!Number.isFinite(Number(raw)) || Number(raw) < 0)) {
        return setError(`${label} must be a non-negative number.`);
      }
    }
    if (!Number.isInteger(Number(form.quantity_on_hand))) return setError("Quantity on hand must be a whole number.");
    if (form.low_stock_threshold !== "" && !Number.isInteger(Number(form.low_stock_threshold))) {
      return setError("Low stock threshold must be a whole number.");
    }

    const payload = {
      name: form.name.trim(),
      sku: form.sku.trim(),
      description: form.description.trim() || null,
      quantity_on_hand: Number(form.quantity_on_hand),
      cost_price: form.cost_price === "" ? null : Number(form.cost_price),
      selling_price: form.selling_price === "" ? null : Number(form.selling_price),
      low_stock_threshold: form.low_stock_threshold === "" ? null : Number(form.low_stock_threshold),
      image_url: form.image_url.trim() || null,
    };
    setSaving(true);
    setError("");
    try {
      if (editing) {
        await api.put(`/products/${productId}`, payload);
      } else {
        await api.post("/products", payload);
      }
      toast.success(editing ? "Product updated." : "Product added.");
      navigate("/products", { replace: true });
    } catch (requestError) {
      const message = getErrorMessage(requestError);
      setError(message);
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingState label="Loading product..." />;

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeading title={editing ? "Edit product" : "Add product"} subtitle={editing ? "Update product details and stock levels." : "Add a product to your inventory."} />
      {error && <InlineError message={error} />}
      <form onSubmit={submit} className="mt-7 space-y-6 rounded-2xl border border-border bg-surface p-6 sm:p-8">
        <div className="grid gap-5 sm:grid-cols-2">
          <div><label className="label" htmlFor="name">Product name <span className="text-red-400">*</span></label><input className="field" id="name" name="name" value={form.name} onChange={change} maxLength={160} required /></div>
          <div><label className="label" htmlFor="sku">SKU <span className="text-red-400">*</span></label><input className="field" id="sku" name="sku" value={form.sku} onChange={change} maxLength={80} required /></div>
        </div>
        <div><label className="label" htmlFor="description">Description</label><textarea className="field min-h-24 resize-y" id="description" name="description" value={form.description} onChange={change} maxLength={2000} /></div>
        <div>
          <label className="label" htmlFor="image_url">Image URL</label>
          <input className="field mt-1.5" id="image_url" name="image_url" type="url" maxLength={2048} placeholder="https://example.com/product.jpg" value={form.image_url} onChange={change} />
        </div>
        <div className="grid gap-5 sm:grid-cols-2">
          <NumberField id="quantity_on_hand" label="Quantity on hand" value={form.quantity_on_hand} onChange={change} min="0" step="1" required />
          <NumberField id="low_stock_threshold" label="Low stock threshold" value={form.low_stock_threshold} onChange={change} min="0" step="1" placeholder="Use organization default" />
          <NumberField id="cost_price" label="Cost price" value={form.cost_price} onChange={change} min="0" step="0.01" />
          <NumberField id="selling_price" label="Selling price" value={form.selling_price} onChange={change} min="0" step="0.01" />
        </div>
        <div className="flex flex-col-reverse gap-3 border-t border-border pt-5 sm:flex-row sm:justify-end">
          <Link className="secondary-button" to="/products">Cancel</Link>
          <button className="primary-button" type="submit" disabled={saving}>{saving ? "Saving..." : editing ? "Save changes" : "Create product"}</button>
        </div>
      </form>
    </div>
  );
}
