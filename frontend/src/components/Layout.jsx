import { useEffect, useState } from "react";
import { NavLink, Link, Outlet, useLocation } from "react-router-dom";
import { api } from "../api.js";
import { useApp } from "../i18n.jsx";

const NAV = [
  ["/verify", "nav.verify"],
  ["/plot", "nav.plot"],
  ["/register", "nav.register"],
  ["/flagged", "nav.flagged"],
  ["/admin", "nav.admin"],
];

export default function Layout() {
  const { t, lang, theme, toggleLang, toggleTheme } = useApp();
  const [open, setOpen] = useState(false);
  const [sys, setSys] = useState(null);
  const location = useLocation();

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);
  useEffect(() => {
    api.stats().then(setSys).catch(() => setSys(null));
  }, []);

  return (
    <div className="app">
      <header className="topbar">
        <div className="container topbar-inner">
          <Link to="/" className="brand" aria-label={t("nav.home")}>
            <img src="/favicon.svg" alt="" width="34" height="34" />
            <span>
              <strong>{t("app.name")}</strong>
              <small>{lang === "bn" ? "JomiProman" : "জমি প্রমাণ"}</small>
            </span>
          </Link>
          <div className="tools">
            <button className="tool-btn" onClick={toggleLang} aria-label={t("lang.switch")} title={t("lang.switch")}>
              🌐 {t("lang.short")}
            </button>
            <button
              className="tool-btn"
              onClick={toggleTheme}
              aria-label={theme === "dark" ? t("theme.toLight") : t("theme.toDark")}
              title={theme === "dark" ? t("theme.toLight") : t("theme.toDark")}
            >
              {theme === "dark" ? "☀️ " + t("theme.light") : "🌙 " + t("theme.dark")}
            </button>
            <button className="menu-btn" onClick={() => setOpen(!open)} aria-label={t("nav.menu")} aria-expanded={open}>
              ☰
            </button>
          </div>
          <nav className={`nav ${open ? "open" : ""}`}>
            {NAV.map(([to, key]) => (
              <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "active" : "")}>
                {t(key)}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="container main">
        <Outlet />
      </main>

      <footer className="footer">
        <div className="container footer-inner">
          <p>
            <strong>{t("footer.dummy")}</strong> {t("footer.note")}
          </p>
          <p className="muted">
            {t("footer.db")} {sys ? t("footer.up") : "—"} · {t("footer.cache")}: {sys?.cache_backend ?? "—"} · {t("footer.ai")}:{" "}
            {sys ? (sys.ai_enabled ? t("footer.aiOn") : t("footer.aiOff")) : "—"}
          </p>
        </div>
      </footer>
    </div>
  );
}
