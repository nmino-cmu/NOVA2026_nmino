import { Menu, X } from "lucide-react";
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
        <NavLink to="/" end onClick={() => setNavOpen(false)}>
          New investigation
        </NavLink>
        <NavLink to="/runs" onClick={() => setNavOpen(false)}>
          Run library
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
