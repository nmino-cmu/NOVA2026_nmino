import { NavLink, Outlet } from "react-router-dom";

function GhostMark() {
  return (
    <span className="ghost-mark" aria-hidden="true">
      <svg viewBox="0 0 32 32">
        <path d="M7 25.5V14.2C7 8.7 10.7 5 16 5s9 3.7 9 9.2v11.3l-4-2.7-5 3.2-5-3.2-4 2.7Z" fill="currentColor" />
        <circle cx="12.5" cy="14" r="1.5" fill="#0d0d10" />
        <circle cx="19.5" cy="14" r="1.5" fill="#0d0d10" />
      </svg>
    </span>
  );
}

export function AppShell() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/" end className="brand">
          <GhostMark />
          <span>Ghost Users</span>
          <em>α</em>
        </NavLink>
        <nav aria-label="Main">
          <NavLink to="/" end>Investigate</NavLink>
          <NavLink to="/board">Workspace</NavLink>
          <NavLink to="/runs">Runs</NavLink>
          <NavLink to="/review">Review</NavLink>
        </nav>
        <div className="header-actions">
          {import.meta.env.VITE_LIVE_DEMO === "1" ? null : (
          <NavLink to="/compare" className="icon-button" aria-label="Compare">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M3 12h4l2.2-6 4.4 12 2.2-6H21" /></svg>
          </NavLink>
          )}
          <NavLink to="/provider" className="avatar" aria-label="Provider">PR</NavLink>
        </div>
      </header>
      <main className="page-body">
        <Outlet />
      </main>
    </div>
  );
}
