/** Survey-style sketch of the headline scenario: 10 shatangsha plot, 6 sold, then 7 offered again. */
import { useApp } from "../i18n.jsx";
import { num } from "../utils.js";

export default function PlotSketch() {
  const { t } = useApp();
  return (
    <svg
      className="sketch"
      viewBox="0 0 480 330"
      role="img"
      aria-label={t("sketch.aria")}
    >
      <defs>
        <pattern id="hatch" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <line className="sk-hatch" x1="0" y1="0" x2="0" y2="9" />
        </pattern>
      </defs>

      {[70, 110, 150, 190, 230, 270].map((y) => (
        <line key={`h${y}`} className="sk-grid" x1="0" x2="480" y1={y} y2={y} />
      ))}
      {[60, 120, 180, 240, 300, 360, 420].map((x) => (
        <line key={`v${x}`} className="sk-grid" y1="0" y2="330" x1={x} x2={x} />
      ))}

      <text className="sk-text" x="24" y="32">
        {t("sketch.title")}
      </text>
      <text className="sk-sub" x="24" y="52">
        {t("sketch.total")}
      </text>

      <rect className="sk-a" x="40" y="80" width="180" height="150" />
      <text className="sk-text" x="130" y="152" textAnchor="middle">
        {t("sketch.rafiq")}
      </text>
      <text className="sk-sub" x="130" y="173" textAnchor="middle">
        {t("sketch.rafiqSub")}
      </text>

      <rect className="sk-b" x="220" y="80" width="120" height="150" />
      <text className="sk-text" x="280" y="152" textAnchor="middle">
        {t("sketch.karim")}
      </text>
      <text className="sk-sub" x="280" y="173" textAnchor="middle">
        {t("sketch.karimSub")}
      </text>

      <rect className="sk-boundary" x="40" y="80" width="300" height="150" />

      <rect className="sk-over" x="220" y="252" width="210" height="30" />
      <text className="sk-red" x="40" y="310">
        {t("sketch.over")}
      </text>

      <g transform="rotate(-10 405 130)">
        <circle className="sk-stamp" cx="405" cy="130" r="38" />
        <circle className="sk-stamp" cx="405" cy="130" r="32" style={{ strokeWidth: 1 }} />
        <text className="sk-stamp-text" x="405" y="126">
          {t("sketch.stamp")}
        </text>
        <text className="sk-stamp-text" x="405" y="144">
          {num(7)} &gt; {num(4)}
        </text>
      </g>
    </svg>
  );
}
