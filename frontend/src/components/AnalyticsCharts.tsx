import type { RunStatus } from "../types";

const STATUS_COLORS: Record<RunStatus, string> = {
  queued: "#f59e0b",
  running: "#3b82f6",
  finished: "#22c55e",
  failed: "#ef4444",
  cancelled: "#64748b",
};

const STATUS_LABELS: Record<RunStatus, string> = {
  queued: "Queued",
  running: "Running",
  finished: "Successful",
  failed: "Failed",
  cancelled: "Cancelled",
};

interface DailyPoint {
  day: string;
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
}

/* ── Donut Chart (pure SVG) ──────────────────────────── */

interface StatusDonutProps {
  data: Record<RunStatus, number>;
  total: number;
}

export function StatusDonutChart({ data, total }: StatusDonutProps) {
  const entries = (Object.keys(data) as RunStatus[])
    .filter((s) => data[s] > 0)
    .map((status) => ({
      status,
      value: data[status],
      color: STATUS_COLORS[status],
      label: STATUS_LABELS[status],
    }));

  const size = 220;
  const cx = size / 2;
  const cy = size / 2;
  const outerR = 95;
  const innerR = 65;

  // Build arcs
  let currentAngle = -90;
  const arcs = entries.map((entry) => {
    const angle = total > 0 ? (entry.value / total) * 360 : 0;
    const startAngle = currentAngle;
    const endAngle = currentAngle + angle;
    currentAngle = endAngle;

    const startRad = (startAngle * Math.PI) / 180;
    const endRad = (endAngle * Math.PI) / 180;
    const largeArc = angle > 180 ? 1 : 0;

    const x1Outer = cx + outerR * Math.cos(startRad);
    const y1Outer = cy + outerR * Math.sin(startRad);
    const x2Outer = cx + outerR * Math.cos(endRad);
    const y2Outer = cy + outerR * Math.sin(endRad);
    const x1Inner = cx + innerR * Math.cos(endRad);
    const y1Inner = cy + innerR * Math.sin(endRad);
    const x2Inner = cx + innerR * Math.cos(startRad);
    const y2Inner = cy + innerR * Math.sin(startRad);

    const d = [
      `M ${x1Outer} ${y1Outer}`,
      `A ${outerR} ${outerR} 0 ${largeArc} 1 ${x2Outer} ${y2Outer}`,
      `L ${x1Inner} ${y1Inner}`,
      `A ${innerR} ${innerR} 0 ${largeArc} 0 ${x2Inner} ${y2Inner}`,
      "Z",
    ].join(" ");

    return { ...entry, d };
  });

  return (
    <div className="chart-donut-wrapper">
      <svg viewBox={`0 0 ${size} ${size}`} className="chart-donut-svg">
        {arcs.length === 0 ? (
          <circle cx={cx} cy={cy} r={outerR} fill="none" stroke="#334155" strokeWidth={outerR - innerR} />
        ) : (
          arcs.map((arc, i) => (
            <path key={i} d={arc.d} fill={arc.color} className="chart-donut-segment">
              <title>{arc.label}: {arc.value}</title>
            </path>
          ))
        )}
        <text x={cx} y={cy - 8} textAnchor="middle" dominantBaseline="middle" className="chart-donut-total">
          {total}
        </text>
        <text x={cx} y={cy + 14} textAnchor="middle" dominantBaseline="middle" className="chart-donut-label">
          runs
        </text>
      </svg>
      <div className="chart-donut-legend">
        {entries.map((entry) => (
          <div className="chart-legend-item" key={entry.status}>
            <span className="chart-legend-dot" style={{ background: entry.color }} />
            <span>{entry.label}</span>
            <strong>{entry.value}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Daily Trend (pure SVG area chart) ───────────────── */

interface DailyTrendProps {
  data: DailyPoint[];
}

export function DailyTrendChart({ data }: DailyTrendProps) {
  const width = 600;
  const height = 200;
  const padX = 40;
  const padY = 20;
  const chartW = width - padX * 2;
  const chartH = height - padY * 2;

  const maxVal = Math.max(...data.map((d) => d.total_runs), 1);

  function toX(i: number) {
    return padX + (i / Math.max(data.length - 1, 1)) * chartW;
  }
  function toY(v: number) {
    return padY + chartH - (v / maxVal) * chartH;
  }

  const totalLine = data.map((d, i) => `${i === 0 ? "M" : "L"} ${toX(i)} ${toY(d.total_runs)}`).join(" ");
  const successLine = data.map((d, i) => `${i === 0 ? "M" : "L"} ${toX(i)} ${toY(d.successful_runs)}`).join(" ");
  const failedLine = data.map((d, i) => `${i === 0 ? "M" : "L"} ${toX(i)} ${toY(d.failed_runs)}`).join(" ");

  const totalArea = `${totalLine} L ${toX(data.length - 1)} ${toY(0)} L ${toX(0)} ${toY(0)} Z`;

  return (
    <div className="chart-svg-wrapper">
      <svg viewBox={`0 0 ${width} ${height}`} className="chart-line-svg">
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((pct) => (
          <line
            key={pct}
            x1={padX} y1={padY + chartH * (1 - pct)}
            x2={padX + chartW} y2={padY + chartH * (1 - pct)}
            stroke="rgba(148,163,184,0.12)" strokeDasharray="4 4"
          />
        ))}
        {/* Area fill */}
        <path d={totalArea} fill="rgba(167,139,250,0.15)" />
        {/* Lines */}
        <path d={totalLine} fill="none" stroke="#a78bfa" strokeWidth="2.5" strokeLinejoin="round" />
        <path d={successLine} fill="none" stroke="#22c55e" strokeWidth="2" strokeLinejoin="round" strokeDasharray="6 3" />
        <path d={failedLine} fill="none" stroke="#ef4444" strokeWidth="2" strokeLinejoin="round" />
        {/* Dots */}
        {data.map((d, i) => (
          <g key={i}>
            <circle cx={toX(i)} cy={toY(d.total_runs)} r="3.5" fill="#a78bfa" />
            <title>{d.day}: {d.total_runs} total, {d.successful_runs} ok, {d.failed_runs} fail</title>
          </g>
        ))}
        {/* X labels */}
        {data.map((d, i) => (
          <text key={i} x={toX(i)} y={height - 2} textAnchor="middle" className="chart-axis-label">{d.day.slice(5)}</text>
        ))}
        {/* Y labels */}
        {[0, 0.5, 1].map((pct) => (
          <text key={pct} x={padX - 6} y={padY + chartH * (1 - pct) + 4} textAnchor="end" className="chart-axis-label">
            {Math.round(maxVal * pct)}
          </text>
        ))}
      </svg>
      <div className="chart-mini-legend">
        <span><span className="chart-legend-dot" style={{ background: "#a78bfa" }} /> Total</span>
        <span><span className="chart-legend-dot" style={{ background: "#22c55e" }} /> Successful</span>
        <span><span className="chart-legend-dot" style={{ background: "#ef4444" }} /> Failed</span>
      </div>
    </div>
  );
}

/* ── Hourly Bar Chart (pure CSS) ─────────────────────── */

interface HourlyBarProps {
  buckets: number[];
}

export function HourlyBarChart({ buckets }: HourlyBarProps) {
  const maxVal = Math.max(...buckets, 1);

  return (
    <div className="chart-bar-grid">
      {buckets.map((value, hour) => {
        const height = Math.max((value / maxVal) * 100, value ? 8 : 2);
        return (
          <div className="chart-bar-item" key={hour}>
            <span className="chart-bar-value">{value || ""}</span>
            <div className="chart-bar-column">
              <div
                className="chart-bar-fill"
                style={{
                  height: `${height}%`,
                  background: hour % 2 === 0
                    ? "linear-gradient(to top, #7c3aed, #a78bfa)"
                    : "linear-gradient(to top, #6366f1, #818cf8)",
                }}
              />
            </div>
            <span className="chart-bar-label">{hour}</span>
          </div>
        );
      })}
    </div>
  );
}

/* ── Success Rate Trend (pure SVG line) ──────────────── */

interface SuccessRateTrendProps {
  data: DailyPoint[];
}

export function SuccessRateTrendChart({ data }: SuccessRateTrendProps) {
  const width = 600;
  const height = 180;
  const padX = 50;
  const padY = 20;
  const chartW = width - padX * 2;
  const chartH = height - padY * 2;

  const chartData = data.map((d) => {
    const total = d.total_runs || 1;
    return { day: d.day, rate: Math.round((d.successful_runs / total) * 100) };
  });

  function toX(i: number) {
    return padX + (i / Math.max(chartData.length - 1, 1)) * chartW;
  }
  function toY(v: number) {
    return padY + chartH - (v / 100) * chartH;
  }

  const linePath = chartData.map((d, i) => `${i === 0 ? "M" : "L"} ${toX(i)} ${toY(d.rate)}`).join(" ");

  return (
    <div className="chart-svg-wrapper">
      <svg viewBox={`0 0 ${width} ${height}`} className="chart-line-svg">
        {[0, 25, 50, 75, 100].map((pct) => (
          <g key={pct}>
            <line x1={padX} y1={toY(pct)} x2={padX + chartW} y2={toY(pct)} stroke="rgba(148,163,184,0.12)" strokeDasharray="4 4" />
            <text x={padX - 6} y={toY(pct) + 4} textAnchor="end" className="chart-axis-label">{pct}%</text>
          </g>
        ))}
        <path d={linePath} fill="none" stroke="#22c55e" strokeWidth="2.5" strokeLinejoin="round" />
        {chartData.map((d, i) => (
          <g key={i}>
            <circle cx={toX(i)} cy={toY(d.rate)} r="4" fill="#22c55e" stroke="#0f0f23" strokeWidth="2" />
            <title>{d.day}: {d.rate}%</title>
          </g>
        ))}
        {chartData.map((d, i) => (
          <text key={i} x={toX(i)} y={height - 2} textAnchor="middle" className="chart-axis-label">{d.day.slice(5)}</text>
        ))}
      </svg>
    </div>
  );
}

/* ── Horizontal Latency Bar (pure CSS) ───────────────── */

interface LatencyBarProps {
  data: Array<{ label: string; value: number; status: RunStatus }>;
}

export function LatencyBarChart({ data }: LatencyBarProps) {
  const maxVal = Math.max(...data.map((d) => d.value), 0.1);

  return (
    <div className="chart-hbar-list">
      {data.map((item, i) => {
        const width = Math.max((item.value / maxVal) * 100, 4);
        return (
          <div className="chart-hbar-item" key={i}>
            <span className="chart-hbar-label">{item.label}</span>
            <div className="chart-hbar-track">
              <div
                className="chart-hbar-fill"
                style={{ width: `${width}%`, background: STATUS_COLORS[item.status] }}
              />
            </div>
            <span className="chart-hbar-value">{(Math.round(item.value * 10) / 10)}s</span>
          </div>
        );
      })}
    </div>
  );
}

/* ── Failure Categories (pure CSS horizontal bar) ────── */

interface FailureBarProps {
  data: Array<{ category: string; count: number }>;
}

export function FailureBarChart({ data }: FailureBarProps) {
  const maxVal = Math.max(...data.map((d) => d.count), 1);

  return (
    <div className="chart-hbar-list">
      {data.map((item, i) => {
        const width = Math.max((item.count / maxVal) * 100, 6);
        const label = item.category.length > 24 ? item.category.slice(0, 24) + "…" : item.category;
        return (
          <div className="chart-hbar-item" key={i}>
            <span className="chart-hbar-label chart-hbar-label-wide">{label}</span>
            <div className="chart-hbar-track">
              <div className="chart-hbar-fill" style={{ width: `${width}%`, background: "#ef4444" }} />
            </div>
            <span className="chart-hbar-value">{item.count}</span>
          </div>
        );
      })}
    </div>
  );
}
