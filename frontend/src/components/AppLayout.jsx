import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const links = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/products", label: "Products" },
  { to: "/settings", label: "Settings" },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const exit = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="min-h-screen bg-canvas">
      <header className="border-b border-border bg-[#0e121b]">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-5">
            <NavLink to="/dashboard" className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue text-lg font-bold text-white">S</span>
              <span className="text-lg font-bold tracking-tight text-white">StockFlow</span>
            </NavLink>
            <nav className="flex items-center gap-1">
              {links.map(({ to, label }) => (
                <NavLink key={to} to={to} className={({ isActive }) =>
                  `rounded-lg px-3 py-2 text-sm font-medium transition ${isActive ? "bg-blue/15 text-blue-300" : "text-slate-400 hover:bg-white/5 hover:text-white"}`
                }>{label}</NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center justify-between gap-4 sm:justify-end">
            <div className="text-right">
              <p className="text-sm font-medium text-slate-100">{user?.username || user?.email}</p>
              <p className="text-xs text-muted">{user?.email}</p>
            </div>
            <button type="button" className="secondary-button" onClick={exit}>Log out</button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-5 py-8 lg:px-8"><Outlet /></main>
    </div>
  );
}
