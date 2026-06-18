from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape as html_escape
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

from app.schemas.run import RunInsightsRead, RunLogRead, RunRead


@dataclass(frozen=True)
class RunReportData:
    run: RunRead
    insights: RunInsightsRead
    logs: list[RunLogRead]


def _enum_value(value: Any) -> str:
    if value is None:
        return ""
    return str(getattr(value, "value", value))


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "-"
    normalized = value
    if normalized.tzinfo is None:
        normalized = normalized.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _format_duration(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f} s"


def _format_number(value: int | float | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _format_text(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return _enum_value(value)


def _quality_gate_status(report: RunReportData) -> str:
    quality_gate = report.insights.quality_gate
    if quality_gate is None or not quality_gate.enabled:
        return "Disabled"
    if quality_gate.passed is None:
        return "Pending"
    return "Passed" if quality_gate.passed else "Failed"


def _metric_rows(report: RunReportData) -> list[tuple[str, str]]:
    metrics = report.insights.metrics
    return [
        ("Duration", _format_duration(metrics.duration_seconds)),
        ("Queue wait", _format_duration(metrics.queue_time_seconds)),
        ("Total logs", _format_number(metrics.total_logs)),
        ("Stdout lines", _format_number(metrics.stdout_lines)),
        ("Stderr lines", _format_number(metrics.stderr_lines)),
        ("System lines", _format_number(metrics.system_lines)),
        ("Info", _format_number(metrics.info_count)),
        ("Warnings", _format_number(metrics.warning_count)),
        ("Errors", _format_number(metrics.error_count)),
    ]


def _summary_rows(report: RunReportData) -> list[tuple[str, str]]:
    run = report.run
    return [
        ("Run ID", str(run.id)),
        ("Project", _format_text(run.project_name)),
        ("Test", _format_text(run.test_name)),
        ("Status", _format_text(run.status)),
        ("Created", _format_datetime(run.created_at)),
        ("Started", _format_datetime(run.started_at)),
        ("Finished", _format_datetime(run.finished_at)),
        ("Exit code", _format_number(run.exit_code)),
        ("Failure category", _format_text(report.insights.failure_category)),
        ("Quality gate", _quality_gate_status(report)),
    ]


def _html_value(value: Any) -> str:
    return html_escape(_format_text(value))


def _html_rows(rows: list[tuple[str, str]]) -> str:
    return "\n".join(
        f"<tr><th>{html_escape(label)}</th><td>{_html_value(value)}</td></tr>"
        for label, value in rows
    )


def _html_list(items: list[str], empty_text: str) -> str:
    if not items:
        return f'<p class="muted">{html_escape(empty_text)}</p>'
    return "<ul>" + "".join(f"<li>{_html_value(item)}</li>" for item in items) + "</ul>"


def build_run_report_html(report: RunReportData) -> str:
    run = report.run
    quality_gate = report.insights.quality_gate
    quality_gate_reasons = quality_gate.reasons if quality_gate else []
    signals = "\n".join(
        "<tr>"
        f'<td><span class="badge badge-{html_escape(_enum_value(signal.severity))}">{_html_value(signal.severity)}</span></td>'
        f"<td>{_html_value(signal.title)}</td>"
        f"<td>{_html_value(signal.detail)}</td>"
        "</tr>"
        for signal in report.insights.signals
    )
    if not signals:
        signals = '<tr><td colspan="3" class="muted">No diagnostic signals.</td></tr>'

    log_rows = "\n".join(
        "<tr>"
        f"<td>{_format_datetime(log.created_at)}</td>"
        f"<td>{_html_value(log.source)}</td>"
        f"<td>{_html_value(log.severity)}</td>"
        f"<td><pre>{html_escape(log.message)}</pre></td>"
        "</tr>"
        for log in report.logs
    )
    if not log_rows:
        log_rows = '<tr><td colspan="4" class="muted">No logs recorded.</td></tr>'

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>BlockTest Run #{run.id} Report</title>
  <style>
    :root {{
      color-scheme: light;
      --text: #1c1c1c;
      --muted: #666666;
      --border: #d9d9d9;
      --panel: #f7f7f7;
      --accent: #2563eb;
      --error: #b91c1c;
      --warning: #a16207;
      --info: #166534;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 32px;
      font-family: Inter, Arial, sans-serif;
      color: var(--text);
      background: #ffffff;
      line-height: 1.5;
    }}
    header {{
      border-bottom: 2px solid var(--text);
      margin-bottom: 28px;
      padding-bottom: 18px;
    }}
    h1, h2, h3 {{ margin: 0; }}
    h1 {{ font-size: 30px; }}
    h2 {{ font-size: 20px; margin: 28px 0 12px; }}
    h3 {{ font-size: 16px; margin: 20px 0 8px; }}
    .muted {{ color: var(--muted); }}
    .summary {{ font-size: 15px; max-width: 920px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 18px;
      align-items: start;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #ffffff;
      border: 1px solid var(--border);
    }}
    th, td {{
      border-bottom: 1px solid var(--border);
      padding: 9px 10px;
      text-align: left;
      vertical-align: top;
      font-size: 13px;
    }}
    th {{ width: 34%; background: var(--panel); font-weight: 700; }}
    thead th {{ width: auto; }}
    tr:last-child td, tr:last-child th {{ border-bottom: 0; }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: "JetBrains Mono", Consolas, monospace;
      font-size: 12px;
    }}
    ul {{ margin-top: 0; padding-left: 20px; }}
    .badge {{
      display: inline-block;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 12px;
      font-weight: 700;
      background: var(--panel);
    }}
    .badge-error {{ color: var(--error); }}
    .badge-warning {{ color: var(--warning); }}
    .badge-info {{ color: var(--info); }}
    @media print {{
      body {{ padding: 18mm; }}
      table {{ page-break-inside: auto; }}
      tr {{ page-break-inside: avoid; page-break-after: auto; }}
    }}
  </style>
</head>
<body>
  <header>
    <p class="muted">BlockTest execution report</p>
    <h1>Run #{run.id}: {_html_value(run.test_name)}</h1>
    <p class="summary">{_html_value(report.insights.summary or run.result_summary)}</p>
  </header>

  <section class="grid">
    <article>
      <h2>Summary</h2>
      <table>
        <tbody>
          {_html_rows(_summary_rows(report))}
        </tbody>
      </table>
    </article>
    <article>
      <h2>Metrics</h2>
      <table>
        <tbody>
          {_html_rows(_metric_rows(report))}
        </tbody>
      </table>
    </article>
  </section>

  <section>
    <h2>Diagnostics</h2>
    <table>
      <thead>
        <tr><th>Severity</th><th>Signal</th><th>Detail</th></tr>
      </thead>
      <tbody>{signals}</tbody>
    </table>

    <h3>Recommendations</h3>
    {_html_list(report.insights.recommendations, "No recommendations.")}

    <h3>Quality gate reasons</h3>
    {_html_list(quality_gate_reasons, "No quality gate reasons.")}
  </section>

  <section>
    <h2>Logs</h2>
    <table>
      <thead>
        <tr><th>Time</th><th>Source</th><th>Severity</th><th>Message</th></tr>
      </thead>
      <tbody>{log_rows}</tbody>
    </table>
  </section>
</body>
</html>
"""


def _font_candidates() -> list[tuple[Path, Path | None]]:
    return [
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
        (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
        (Path("/Library/Fonts/Arial Unicode.ttf"), None),
        (Path("/System/Library/Fonts/Supplemental/Arial.ttf"), None),
    ]


def _register_pdf_fonts() -> tuple[str, str]:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    regular_name = "BlockTestSans"
    bold_name = "BlockTestSansBold"
    try:
        pdfmetrics.getFont(regular_name)
        pdfmetrics.getFont(bold_name)
        return regular_name, bold_name
    except KeyError:
        pass

    for regular_path, bold_path in _font_candidates():
        if regular_path.exists():
            pdfmetrics.registerFont(TTFont(regular_name, str(regular_path)))
            if bold_path and bold_path.exists():
                pdfmetrics.registerFont(TTFont(bold_name, str(bold_path)))
            else:
                pdfmetrics.registerFont(TTFont(bold_name, str(regular_path)))
            return regular_name, bold_name

    return "Helvetica", "Helvetica-Bold"


def _pdf_text(value: Any) -> str:
    return xml_escape(_format_text(value)).replace("\n", "<br/>")


def _truncate_pdf_text(value: str, limit: int = 1800) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}... [truncated]"


def build_run_report_pdf(report: RunReportData) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    regular_font, bold_font = _register_pdf_fonts()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "BlockTestTitle",
        parent=styles["Title"],
        fontName=bold_font,
        fontSize=18,
        leading=23,
        alignment=TA_LEFT,
        spaceAfter=8,
    )
    subtitle_style = ParagraphStyle(
        "BlockTestSubtitle",
        parent=styles["BodyText"],
        fontName=regular_font,
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#555555"),
        spaceAfter=10,
        wordWrap="CJK",
    )
    heading_style = ParagraphStyle(
        "BlockTestHeading",
        parent=styles["Heading2"],
        fontName=bold_font,
        fontSize=13,
        leading=16,
        spaceBefore=12,
        spaceAfter=8,
    )
    normal_style = ParagraphStyle(
        "BlockTestNormal",
        parent=styles["BodyText"],
        fontName=regular_font,
        fontSize=9,
        leading=12,
        wordWrap="CJK",
    )
    small_style = ParagraphStyle(
        "BlockTestSmall",
        parent=normal_style,
        fontSize=8,
        leading=10,
    )
    header_style = ParagraphStyle(
        "BlockTestTableHeader",
        parent=normal_style,
        fontName=bold_font,
        alignment=TA_CENTER,
        textColor=colors.white,
    )

    table_style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), regular_font),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
    )

    def paragraph(value: Any, style: ParagraphStyle = normal_style) -> Paragraph:
        return Paragraph(_pdf_text(value), style)

    def key_value_table(rows: list[tuple[str, str]]) -> Table:
        data = [[paragraph("Field", header_style), paragraph("Value", header_style)]]
        data.extend([[paragraph(label), paragraph(value)] for label, value in rows])
        table = Table(data, colWidths=[48 * mm, 120 * mm], hAlign="LEFT", repeatRows=1)
        table.setStyle(table_style)
        return table

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"BlockTest Run #{report.run.id} Report",
        author="BlockTest",
    )

    story: list[Any] = [
        Paragraph(f"BlockTest Run #{report.run.id} Report", title_style),
        Paragraph(_pdf_text(report.insights.summary or report.run.result_summary), subtitle_style),
        Paragraph("Summary", heading_style),
        key_value_table(_summary_rows(report)),
        Spacer(1, 8),
        Paragraph("Metrics", heading_style),
        key_value_table(_metric_rows(report)),
    ]

    signal_rows = [[paragraph("Severity", header_style), paragraph("Signal", header_style), paragraph("Detail", header_style)]]
    if report.insights.signals:
        signal_rows.extend(
            [
                paragraph(signal.severity, small_style),
                paragraph(signal.title, small_style),
                paragraph(signal.detail, small_style),
            ]
            for signal in report.insights.signals
        )
    else:
        signal_rows.append([paragraph("-"), paragraph("No diagnostic signals."), paragraph("-")])
    signals_table = LongTable(signal_rows, colWidths=[26 * mm, 48 * mm, 94 * mm], hAlign="LEFT", repeatRows=1)
    signals_table.setStyle(table_style)
    story.extend([Paragraph("Diagnostics", heading_style), signals_table])

    if report.insights.recommendations:
        story.append(Paragraph("Recommendations", heading_style))
        for index, item in enumerate(report.insights.recommendations, start=1):
            story.append(Paragraph(f"{index}. {_pdf_text(item)}", normal_style))

    quality_gate = report.insights.quality_gate
    if quality_gate and quality_gate.reasons:
        story.append(Paragraph("Quality Gate Reasons", heading_style))
        for index, item in enumerate(quality_gate.reasons, start=1):
            story.append(Paragraph(f"{index}. {_pdf_text(item)}", normal_style))

    log_rows = [
        [
            paragraph("Time", header_style),
            paragraph("Source", header_style),
            paragraph("Severity", header_style),
            paragraph("Message", header_style),
        ]
    ]
    if report.logs:
        log_rows.extend(
            [
                paragraph(_format_datetime(log.created_at), small_style),
                paragraph(log.source, small_style),
                paragraph(log.severity, small_style),
                paragraph(_truncate_pdf_text(log.message), small_style),
            ]
            for log in report.logs
        )
    else:
        log_rows.append([paragraph("-"), paragraph("-"), paragraph("-"), paragraph("No logs recorded.")])
    logs_table = LongTable(log_rows, colWidths=[36 * mm, 24 * mm, 24 * mm, 84 * mm], hAlign="LEFT", repeatRows=1)
    logs_table.setStyle(table_style)
    story.extend([Paragraph("Logs", heading_style), logs_table])

    document.build(story)
    return buffer.getvalue()
