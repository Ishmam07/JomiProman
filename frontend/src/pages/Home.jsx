import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useApp } from "../i18n.jsx";
import PlotSketch from "../components/PlotSketch.jsx";
import { num } from "../utils.js";

export default function Home() {
  const { t } = useApp();
  const [stats, setStats] = useState(null);
  useEffect(() => {
    api.stats().then(setStats).catch(() => {});
  }, []);

  const steps = [
    ["1", "home.s1.t", "home.s1.d"],
    ["2", "home.s2.t", "home.s2.d"],
    ["3", "home.s3.t", "home.s3.d"],
  ];

  return (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">{t("home.eyebrow")}</p>
          <h1>{t("home.title")}</h1>
          <p className="lead">{t("home.lead")}</p>
          <div className="row">
            <Link to="/verify" className="btn btn-primary btn-lg">
              {t("home.cta1")}
            </Link>
            <Link to="/plot" className="btn btn-ghost btn-lg">
              {t("home.cta2")}
            </Link>
          </div>
        </div>
        <PlotSketch />
      </section>

      <section className="stats">
        <div>
          <b>{stats ? num(stats.plots) : "–"}</b>
          <span>{t("home.stat.plots")}</span>
        </div>
        <div>
          <b>{stats ? num(stats.deeds_registered) : "–"}</b>
          <span>{t("home.stat.deeds")}</span>
        </div>
        <div>
          <b className="danger">{stats ? num(stats.deeds_blocked) : "–"}</b>
          <span>{t("home.stat.blocked")}</span>
        </div>
      </section>

      <section>
        <h2 className="section-title">{t("home.how")}</h2>
        <div className="grid3">
          {steps.map(([n, title, text]) => (
            <article key={n} className="card step">
              <span className="step-no">{num(n)}</span>
              <h3>{t(title)}</h3>
              <p>{t(text)}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="card demo">
        <h2 className="section-title">{t("home.demo")}</h2>
        <ol>
          <li>
            <Link to="/register">{t("home.demo1a")}</Link>
            {t("home.demo1b")}
          </li>
          <li>{t("home.demo2")}</li>
          <li>
            <Link to="/verify">{t("home.demo3a")}</Link>
            {t("home.demo3b")}
          </li>
          <li>
            <Link to="/plot">{t("home.demo4a")}</Link>
            {t("home.demo4b")}
          </li>
        </ol>
      </section>
    </>
  );
}
