import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useApp } from "../i18n.jsx";
import { Spinner } from "./common.jsx";

/** Plain-Bangla explanation of a result. The AI never changes the verdict; it only explains it. */
export default function AiExplain({ status, findings }) {
  const { t } = useApp();
  const [state, setState] = useState({ loading: true });
  const key = JSON.stringify([status, (findings ?? []).map((f) => f.code)]);

  useEffect(() => {
    let alive = true;
    setState({ loading: true });
    api
      .explain(status, findings)
      .then((reply) => alive && setState({ reply }))
      .catch(() => alive && setState({ failed: true }));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  if (state.failed) return null;
  return (
    <section className="card ai-card">
      <div className="card-head">
        <h3>{t("ai.title")}</h3>
        {state.reply && (
          <span className={`badge ${state.reply.source === "ai" ? "badge-ai" : ""}`}>
            {state.reply.source === "ai" ? `AI · ${state.reply.model}` : t("ai.auto")}
          </span>
        )}
      </div>
      {state.loading ? <Spinner label={t("ai.loading")} /> : <p className="ai-text">{state.reply.text}</p>}
      <p className="muted small">{t("ai.note")}</p>
    </section>
  );
}
