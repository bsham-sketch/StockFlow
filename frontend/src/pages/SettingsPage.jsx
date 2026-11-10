import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import api, { getErrorMessage } from "../api/client";
import { InlineError, LoadingState, PageHeading } from "./DashboardPage";

export default function SettingsPage() {
  const [threshold, setThreshold] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    api.get("/settings")
      .then(({ data }) => active && setThreshold(String(data.default_low_stock_threshold)))
      .catch((requestError) => active && setError(getErrorMessage(requestError)))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, []);

  const submit = async (event) => {
    event.preventDefault();
    const value = Number(threshold);
    if (!Number.isInteger(value) || value < 0) {
      setError("Enter a non-negative whole number.");
      toast.error("Enter a non-negative whole number.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const { data } = await api.put("/settings", { default_low_stock_threshold: value });
      setThreshold(String(data.default_low_stock_threshold));
      toast.success("Settings saved.");
    } catch (requestError) {
      const message = getErrorMessage(requestError);
      setError(message);
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeading title="Settings" subtitle="Set inventory defaults for your organization." />
      {error && <InlineError message={error} />}
      {loading ? <LoadingState label="Loading settings..." /> : (
        <form onSubmit={submit} className="mt-7 w-full rounded-2xl border border-border bg-surface p-6 sm:p-8">
          <div className="max-w-lg">
            <label className="label" htmlFor="threshold">Default low-stock threshold</label>
            <p className="mt-1 text-sm text-muted">Products without a custom threshold are marked low stock at or below this quantity.</p>
            <input className="field mt-4 max-w-xs" id="threshold" type="number" min="0" step="1" required value={threshold} onChange={(event) => { setThreshold(event.target.value); setError(""); }} />
          </div>
          <div className="mt-7 border-t border-border pt-5">
            <button className="primary-button" type="submit" disabled={saving}>{saving ? "Saving..." : "Save settings"}</button>
          </div>
        </form>
      )}
    </div>
  );
}
