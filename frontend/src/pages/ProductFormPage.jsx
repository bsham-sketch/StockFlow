import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import api, { getErrorMessage } from "../api/client";
import ProductImage from "../components/ProductImage";
import { InlineError, LoadingState, PageHeading } from "./DashboardPage";

const initialForm = {
  name: "",
  sku: "",
  description: "",
  quantity_on_hand: "0",
  cost_price: "",
  selling_price: "",
  low_stock_threshold: "",
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
  const location = useLocation();
  const navigate = useNavigate();
  const [form, setForm] = useState(initialForm);
  const [error, setError] = useState(location.state?.imageError || "");
  const [loading, setLoading] = useState(editing);
  const [saving, setSaving] = useState(false);
  const [imageFile, setImageFile] = useState(location.state?.pendingImage || null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [hasImage, setHasImage] = useState(false);
  const [removeImage, setRemoveImage] = useState(false);

  useEffect(() => {
    if (!imageFile) {
      setPreviewUrl("");
      return undefined;
    }
    const objectUrl = URL.createObjectURL(imageFile);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [imageFile]);

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
          });
          setHasImage(Boolean(data.image_url));
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

  const selectImage = (event) => {
    const file = event.target.files?.[0] || null;
    if (!file) return;
    const allowedTypes = ["image/jpeg", "image/png", "image/gif", "image/webp"];
    if (!allowedTypes.includes(file.type)) {
      setImageFile(null);
      setError("Choose a JPEG, PNG, GIF, or WebP image.");
      event.target.value = "";
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setImageFile(null);
      setError("Product images must be 5 MB or smaller.");
      event.target.value = "";
      return;
    }
    setImageFile(file);
    setRemoveImage(false);
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
    };
    setSaving(true);
    setError("");
    let createdProductId = null;
    try {
      if (editing) {
        createdProductId = productId;
        await api.put(`/products/${productId}`, payload);
      } else {
        const { data } = await api.post("/products", payload);
        createdProductId = data.id;
      }

      if (imageFile) {
        const imagePayload = new FormData();
        imagePayload.append("image", imageFile);
        await api.put(`/products/${createdProductId}/image`, imagePayload, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      } else if (editing && removeImage) {
        await api.delete(`/products/${productId}/image`);
      }
      navigate("/products", { replace: true });
    } catch (requestError) {
      if (!editing && createdProductId !== null && imageFile) {
        navigate(`/products/${createdProductId}/edit`, {
          replace: true,
          state: {
            pendingImage: imageFile,
            imageError: `Product created, but its image could not be uploaded: ${getErrorMessage(requestError)}`,
          },
        });
        return;
      }
      setError(getErrorMessage(requestError));
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
          <label className="label" htmlFor="product-image">Product image</label>
          <p className="mt-1 text-sm text-muted">JPEG, PNG, GIF, or WebP, up to 5 MB.</p>
          <div className="mt-3 flex flex-wrap items-center gap-4">
            {imageFile ? (
              <img src={previewUrl} alt="Selected product preview" className="h-24 w-24 rounded-xl border border-border object-cover" />
            ) : hasImage && !removeImage ? (
              <ProductImage imageUrl={`/api/products/${productId}/image`} alt="Current product" className="h-24 w-24" />
            ) : (
              <div className="flex h-24 w-24 items-center justify-center rounded-xl border border-dashed border-border bg-[#171c28] text-xs text-slate-500">No image</div>
            )}
            <div className="space-y-2">
              <input
                className="block max-w-full text-sm text-slate-400 file:mr-3 file:rounded-lg file:border-0 file:bg-[#202738] file:px-3 file:py-2 file:text-sm file:font-medium file:text-slate-200 hover:file:bg-[#2a3448]"
                id="product-image"
                type="file"
                accept="image/jpeg,image/png,image/gif,image/webp"
                onChange={selectImage}
              />
              {editing && hasImage && !removeImage && !imageFile && (
                <button type="button" className="text-sm font-medium text-red-300 hover:text-red-200" onClick={() => setRemoveImage(true)}>Remove current image</button>
              )}
              {removeImage && (
                <button type="button" className="text-sm font-medium text-slate-300 hover:text-white" onClick={() => setRemoveImage(false)}>Keep current image</button>
              )}
            </div>
          </div>
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
