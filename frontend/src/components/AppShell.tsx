import { GitCompare, Library, Menu, Plus, ScanSearch, Server, X } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

export function AppShell() {
  const [navOpen, setNavOpen] = useState(false);

  return (
    <div className="app-shell">
      <div
        className={`nav-overlay ${navOpen ? "visible" : ""}`}
        onClick={() => setNavOpen(false)}
        aria-hidden={!navOpen}
      />
      <nav className={`nav-rail ${navOpen ? "open" : ""}`} aria-label="Main">
        <div className="brand">Ghost Users</div>
        <div className="nav-kicker">Inspect and replay</div>
        <NavLink to="/" end onClick={() => setNavOpen(false)}>
          <Plus size={16} /> New investigation
        </NavLink>
        <NavLink to="/runs" onClick={() => setNavOpen(false)}>
          <Library size={16} /> Run library
        </NavLink>
        <NavLink to="/review" onClick={() => setNavOpen(false)}>
          <ScanSearch size={16} /> Review
        </NavLink>
        <NavLink to="/compare" onClick={() => setNavOpen(false)}>
          <GitCompare size={16} /> Comparison
        </NavLink>
        <NavLink to="/provider" onClick={() => setNavOpen(false)}>
          <Server size={16} /> Provider
        </NavLink>
      </nav>
      <div className="main-column">
        <header className="top-strip">
          <button
            type="button"
            className="menu-btn"
            aria-label={navOpen ? "Close menu" : "Open menu"}
            onClick={() => setNavOpen((o) => !o)}
          >
            {navOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </header>
        <main className="page-body">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
