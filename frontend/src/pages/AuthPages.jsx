import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { getErrorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";

function AuthLayout({ eyebrow, title, subtitle, footer, children }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas px-5 py-12">
      <section className="w-full max-w-[560px]">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">{eyebrow}</p>
        <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">{title}</h1>
        <p className="mt-3 text-base text-slate-400">{subtitle}</p>
        {children}
        <p className="mt-7 text-sm text-slate-400">{footer}</p>
      </section>
    </main>
  );
}

function FormField({ id, label, ...props }) {
  return (
    <div>
      <label className="label" htmlFor={id}>{label}</label>
      <input className="field mt-1.5" id={id} name={id} {...props} />
    </div>
  );
}

export function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  const change = (event) => {
    setForm({ ...form, [event.target.name]: event.target.value });
    setError("");
  };
  const submit = async (event) => {
    event.preventDefault();
    if (!form.email.trim() || !form.password) return setError("Enter your email and password.");
    setBusy(true);
    try {
      await login({ email: form.email.trim(), password: form.password });
      toast.success("Logged in.");
      navigate("/dashboard", { replace: true });
    } catch (requestError) {
      const message = getErrorMessage(requestError);
      setError(message);
      toast.error(message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout
      eyebrow="Welcome back"
      title="Log in to StockFlow"
      subtitle="Access your organization's inventory dashboard."
      footer={<>New to StockFlow? <Link to="/signup" className="font-semibold text-blue-500 hover:text-blue-400">Create an organization</Link></>}
    >
      <form className="mt-9 space-y-5" onSubmit={submit}>
        <FormField id="email" label="Email" type="email" placeholder="you@company.com" autoComplete="email" value={form.email} onChange={change} required />
        <FormField id="password" label="Password" type="password" placeholder="••••••••" autoComplete="current-password" value={form.password} onChange={change} required />
        {error && <p role="alert" className="rounded-lg border border-red-900/70 bg-red-950/40 px-3.5 py-3 text-sm text-red-300">{error}</p>}
        <button className="primary-button w-full" type="submit" disabled={busy}>{busy ? "Logging in..." : "Log in"}</button>
      </form>
    </AuthLayout>
  );
}

export function SignupPage() {
  const { signup, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: "", organization_name: "", email: "", password: "", confirm_password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  const change = (event) => {
    setForm({ ...form, [event.target.name]: event.target.value });
    setError("");
  };
  const submit = async (event) => {
    event.preventDefault();
    if (!form.username.trim() || !form.organization_name.trim() || !form.email.trim()) return setError("Complete all required fields.");
    if (form.password.length < 8) return setError("Password must be at least 8 characters.");
    if (form.password !== form.confirm_password) return setError("Passwords do not match.");
    setBusy(true);
    try {
      await signup({
        username: form.username.trim(),
        organization_name: form.organization_name.trim(),
        email: form.email.trim(),
        password: form.password,
      });
      toast.success("Your organization is ready.");
      navigate("/dashboard", { replace: true });
    } catch (requestError) {
      const message = getErrorMessage(requestError);
      setError(message);
      toast.error(message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout
      eyebrow="Get started"
      title="Create your organization"
      subtitle="You'll be its first (and only) user."
      footer={<>Already have an account? <Link to="/login" className="font-semibold text-blue-500 hover:text-blue-400">Log in</Link></>}
    >
      <form className="mt-9 space-y-4" onSubmit={submit}>
        <FormField id="username" label="Username" placeholder="How should we address you?" autoComplete="nickname" value={form.username} onChange={change} maxLength={80} required />
        <FormField id="organization_name" label="Organization name" placeholder="Acme Trading Co." autoComplete="organization" value={form.organization_name} onChange={change} maxLength={160} required />
        <FormField id="email" label="Email" type="email" placeholder="you@company.com" autoComplete="email" value={form.email} onChange={change} required />
        <FormField id="password" label="Password" type="password" placeholder="At least 8 characters" autoComplete="new-password" value={form.password} onChange={change} minLength={8} required />
        <FormField id="confirm_password" label="Confirm password" type="password" placeholder="Repeat your password" autoComplete="new-password" value={form.confirm_password} onChange={change} required />
        {error && <p role="alert" className="rounded-lg border border-red-900/70 bg-red-950/40 px-3.5 py-3 text-sm text-red-300">{error}</p>}
        <button className="primary-button w-full" type="submit" disabled={busy}>{busy ? "Creating organization..." : "Create organization"}</button>
      </form>
    </AuthLayout>
  );
}
