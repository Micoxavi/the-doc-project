"""Genera en PDF el Vulnerability Intake and Triage Report (ELA-VH-001) o su plantilla de cabecera y pie.

Uso:
    python generar_informe.py informe [--datos datos.json] [-o salida.pdf]
    python generar_informe.py cabecera [--datos datos.json] [-o salida.pdf]
    python generar_informe.py datos > datos.json      # vuelca los campos con sus valores por defecto

Requiere Microsoft Edge o Google Chrome (se usa en modo headless para imprimir a PDF)
y logo.png en la misma carpeta que este script.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

DEFAULTS: dict = {
    "title": "Vulnerability Intake and Triage Report",
    "code": "ELA-VH-001",
    "rev": "xx",
    "date": "aaaammdd",
    "confidentiality": "Confidential",
    "vulnerability_id": "[Unique internal identifier assigned in the Vulnerability Register]",
    "detection_date": "[DD/MM/YYYY and time, when relevant]",
    "product": "[Product or product family]",
    "versions": "[Version, revision or configuration]",
    "component": "[Component, library, module, firmware, hardware element or dependency]",
    "summary": "[Concise description of the reported issue and known affected condition.]",
    "triage_result": "[CONTINUE / INSUFFICIENT INFORMATION / DISMISSED / DUPLICATE]",
    "released_by": [["", "", "", ""], ["", "", "", ""]],
    "history": [["1", "", "", ""], ["", "", "", ""]],
    "intake_source": "[Source and CVE, advisory ID, supplier notice, report ID, URL or internal reference]",
    "intake_reporter": "[Name, organization, function and available contact details; "
                       "state anonymous or unavailable where applicable]",
    "intake_product": "[Product or family]",
    "intake_versions": "[Product, firmware, software, hardware revision or configuration]",
    "intake_component": "[Component, library, module, firmware, hardware element or dependency]",
    "description": "[Summarize the reported issue, available technical details, observed behavior, "
                   "known exploitation conditions and relevant context.]",
    "evidence_references": "[Reports, advisories, correspondence, screenshots, logs, database records "
                           "or other supporting material.]",
    "info_sufficient": "[YES / NO]",
    "review_date": "[DD/MM/YYYY]",
    "missing_information": "[Identify missing or unclear information and describe the request, "
                           "search activity or reason it is unavailable.]",
    "followup_status": "[Pending / Received / Documented unavailable - DD/MM/YYYY]",
    "evidence_reference": "[Email, ticket, report or database record]",
    "credibility": "[Assess source reliability and the available technical support. State whether the "
                   "information is credible, unsupported, incorrect or uncertain, and identify the "
                   "supporting evidence.]",
    "duplicate_assessment": "[No duplicate identified / Potential duplicate / Duplicate. Reference the main "
                            "or related Vulnerability ID where applicable.]",
    "triage_justification": "[Document the reasoning and evidence supporting the triage conclusion.]",
    "triage_decision": "",  # "", "continue", "insufficient", "dismissed" o "duplicate" (marca la casilla)
    "selected_status": "[Registered / Insufficient information / Dismissed / Duplicate]",
    "decision_date": "[DD/MM/YYYY]",
    "next_action": "[Required follow-up and linked Vulnerability Register entry, VH-DEL-002 or other record]",
    "assigned_owner": "[Person or function]",
    "target_date": "[DD/MM/YYYY or not defined]",
}

DECISIONS = {
    "continue": ("Continuing to applicability assessment",
                 "Information is credible or cannot be confidently discarded. "
                 "Link the subsequent assessment record when created."),
    "insufficient": ("Insufficient information",
                     "The record remains open. Identify the missing information and follow-up action above."),
    "dismissed": ("Dismissed",
                  "The information is incorrect, misleading, unsupported or not technically valid. "
                  "Justification is mandatory."),
    "duplicate": ("Duplicate", "Reference the main Vulnerability ID. The duplicate record is retained."),
}

# ponytail: páginas A4 de alto fijo; un texto muy largo se recorta en vez de saltar de página. Si hace falta, paginación dinámica.
CSS = """
@page{size:A4;margin:0}
*{box-sizing:border-box}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{margin:0;font:10pt/1.35 'Inter',Arial,sans-serif;color:#2E2C33}
.page{width:210mm;height:297mm;display:flex;flex-direction:column;padding:11mm 15mm 9mm;overflow:hidden;break-after:page}
.page:last-child{break-after:auto}
.content{flex:1;padding:9mm 0 5mm}
.hdr{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;column-gap:6mm;row-gap:3mm}
.hdr::after{content:"";grid-column:1/-1;height:2px;background:linear-gradient(90deg,#FF9933 0 32mm,#E3E3E8 32mm)}
.hdr img{height:7.5mm}
.hdr-title{text-align:center;font-weight:600;font-size:10.5pt;color:#403E48}
.hdr-meta{justify-self:end;margin:0;display:grid;grid-template-columns:auto auto;column-gap:4mm;row-gap:.6mm;font-size:8.5pt}
.hdr-meta div{display:contents}
.hdr-meta dt{color:#7A7882}
.hdr-meta dd{margin:0;font-weight:600}
.ftr{display:flex;align-items:center;gap:5mm}
.ftr-conf{color:#D9730D;font-size:7pt;font-weight:700;letter-spacing:.2em;text-transform:uppercase}
.ftr-bar{flex:1;height:3px;border-radius:3px;background:linear-gradient(90deg,#FF9933 var(--p),#E6E6EA 0)}
.ftr-page{font-size:9pt;font-weight:700;color:#403E48;white-space:nowrap}
.ftr-page i{font-style:normal;margin:0 .35em;opacity:.6}
.doc-h1{margin:0 0 4mm;font:700 19pt/1.2 'Inter',Arial,sans-serif;color:#403E48}
.intro{margin:0 0 8mm;text-align:center;font-style:italic;color:#B35A12}
table{border-collapse:collapse;width:100%}
.tbl{margin-bottom:7mm;font-size:9.5pt}
.tbl th,.tbl td{padding:2.3mm 2.6mm;text-align:left;vertical-align:middle;border:1px solid #D9D9DF}
.tbl th{font-weight:700}
.tbl tbody th{background:#F4F4F6;color:#403E48}
.tbl .tbl-title{text-align:center;letter-spacing:.06em;background:#403E48;color:#fff;font-size:9pt;border-color:#403E48;box-shadow:inset 0 -2px 0 #FF9933}
.tbl .tbl-title.left{text-align:left}
.tbl .cols th{text-align:center;background:#ECECF0}
.tbl td.blank{height:9mm}
.tbl td.center{text-align:center}
.ph{color:#7A7882}
.triage{width:80%;margin:0 auto 7mm;font-size:9.5pt}
.triage th,.triage td{padding:3mm;border:1.5px solid #FF9933;color:#403E48}
.triage th{width:27%;background:#FF9933}
.triage td{text-align:center;font-weight:700}
.box{display:inline-block;width:3.6mm;height:3.6mm;border:1.3px solid #403E48;border-radius:.7mm;vertical-align:middle}
.box.on{background:#FF9933;border-color:#D9730D;box-shadow:inset 0 0 0 .7mm #fff}
"""

INTRO = ("This document constitutes the complete Vulnerability Intake and Triage Report. Complete all fields "
         "as far as the information is available. Unknown or unavailable information must be explicitly "
         "identified, and the record must remain traceable to the Vulnerability Register.")


def td(d: dict, key: str, colspan: int = 1, height: int | None = None) -> str:
    """Celda con el valor del campo; en gris si sigue siendo el texto de ejemplo. height en mm."""
    cls = ' class="ph"' if d[key] == DEFAULTS[key] else ""
    span = f' colspan="{colspan}"' if colspan > 1 else ""
    style = f' style="height:{height}mm"' if height else ""
    return f"<td{cls}{span}{style}>{html.escape(d[key])}</td>"


def grid_table(title: str, cols: list[str], rows: list[list[str]], center_first: bool) -> str:
    body = ""
    for row in rows:
        cells = [html.escape(str(c)) for c in row]
        first = "blank center" if center_first else "blank"
        body += f'<tr><td class="{first}">{cells[0]}</td>' + "".join(f"<td>{c}</td>" for c in cells[1:]) + "</tr>"
    return f"""<table class="tbl">
<colgroup><col style="width:14.7%"><col style="width:33.8%"><col style="width:33.8%"><col></colgroup>
<thead><tr><th class="tbl-title" colspan="4">{title}</th></tr>
<tr class="cols">{"".join(f"<th>{c}</th>" for c in cols)}</tr></thead>
<tbody>{body}</tbody></table>"""


def page1(d: dict) -> str:
    return f"""<h1 class="doc-h1">{html.escape(d["title"])}</h1>
<p class="intro">{INTRO}</p>
<table class="tbl">
<colgroup><col style="width:23%"><col><col style="width:13%"><col style="width:23.5%"></colgroup>
<thead><tr><th class="tbl-title" colspan="4">REPORT SUMMARY</th></tr></thead>
<tbody>
<tr><th>Vulnerability ID</th>{td(d, "vulnerability_id", 3)}</tr>
<tr><th>Detection / reception date</th>{td(d, "detection_date", 3)}</tr>
<tr><th>Affected product / family</th>{td(d, "product")}<th>Affected version(s)</th>{td(d, "versions")}</tr>
<tr><th>Affected component / dependency</th>{td(d, "component", 3)}</tr>
<tr><th>Vulnerability summary</th>{td(d, "summary", 3)}</tr>
</tbody></table>
<table class="triage"><tr><th>TRIAGE RESULT</th><td>{html.escape(d["triage_result"])}</td></tr></table>
{grid_table("RELEASED BY", ["Name", "Function", "Date", "Version"], d["released_by"], center_first=False)}
{grid_table("DOCUMENT HISTORY", ["Version", "Decision", "Reason", "Assessed by"], d["history"], center_first=True)}"""


def page2(d: dict) -> str:
    return f"""<table class="tbl">
<colgroup><col style="width:23.7%"><col><col style="width:17.3%"><col style="width:24.4%"></colgroup>
<thead><tr><th class="tbl-title left" colspan="4">VULNERABILITY INTAKE</th></tr></thead>
<tbody>
<tr><th>Source / Reference ID</th>{td(d, "intake_source", 3)}</tr>
<tr><th>Reporter / contact details</th>{td(d, "intake_reporter", 3)}</tr>
<tr><th>Affected product / family</th>{td(d, "intake_product")}<th>Affected version(s)</th>{td(d, "intake_versions")}</tr>
<tr><th>Affected component / dependency</th>{td(d, "intake_component", 3)}</tr>
</tbody></table>
<table class="tbl">
<colgroup><col style="width:24.2%"><col></colgroup>
<thead><tr><th class="tbl-title" colspan="2">VULNERABILITY DESCRIPTION</th></tr></thead>
<tbody>
<tr><th>Description</th>{td(d, "description", height=22)}</tr>
<tr><th>Evidence and references</th>{td(d, "evidence_references")}</tr>
</tbody></table>
<table class="tbl">
<colgroup><col style="width:25.4%"><col style="width:26.8%"><col style="width:14.3%"><col></colgroup>
<thead><tr><th class="tbl-title" colspan="4">INITIAL INFORMATION REVIEW</th></tr></thead>
<tbody>
<tr><th>Information sufficient for preliminary assessment?</th>{td(d, "info_sufficient")}<th>Review date</th>{td(d, "review_date")}</tr>
<tr><th>Missing information and follow-up action</th>{td(d, "missing_information", 3, height=30)}</tr>
<tr><th>Follow-up status / date</th>{td(d, "followup_status")}<th>Evidence reference</th>{td(d, "evidence_reference")}</tr>
</tbody></table>"""


def page3(d: dict) -> str:
    options = "".join(
        f'<tr><td colspan="2">{name}</td>'
        f'<td class="center"><span class="box{" on" if d["triage_decision"] == key else ""}"></span></td>'
        f'<td colspan="2">{meaning}</td></tr>'
        for key, (name, meaning) in DECISIONS.items()
    )
    return f"""<table class="tbl">
<colgroup><col style="width:28.8%"><col></colgroup>
<thead><tr><th class="tbl-title" colspan="2">TRIAGE ASSESSMENT</th></tr></thead>
<tbody>
<tr><th>Credibility assessment and supporting basis</th>{td(d, "credibility")}</tr>
<tr><th>Duplicate assessment / related record</th>{td(d, "duplicate_assessment")}</tr>
<tr><th>Triage justification</th>{td(d, "triage_justification", height=18)}</tr>
</tbody></table>
<table class="tbl">
<colgroup><col style="width:16%"><col style="width:12.8%"><col style="width:14.9%"><col style="width:16.4%"><col></colgroup>
<thead><tr><th class="tbl-title" colspan="5">TRIAGE DECISION</th></tr>
<tr class="cols"><th colspan="2">Decision</th><th>Select</th><th colspan="2">Meaning / required reference</th></tr></thead>
<tbody>
{options}
<tr><th>Selected status</th>{td(d, "selected_status", 2)}<th>Decision date</th>{td(d, "decision_date")}</tr>
<tr><th>Next action / linked record</th>{td(d, "next_action", 4)}</tr>
<tr><th>Assigned owner</th>{td(d, "assigned_owner", 2)}<th>Target date</th>{td(d, "target_date")}</tr>
</tbody></table>"""


def build_html(kind: str, d: dict) -> str:
    """Devuelve el HTML autocontenido del informe ('informe') o de la plantilla ('cabecera')."""
    logo = base64.b64encode((HERE / "logo.png").read_bytes()).decode()
    e = {k: html.escape(d[k]) for k in ("title", "code", "rev", "date", "confidentiality")}
    header = f"""<header class="hdr">
<img src="data:image/png;base64,{logo}" alt="elausa electronics">
<div class="hdr-title">{e["title"]}</div>
<dl class="hdr-meta"><div><dt>Code</dt><dd>{e["code"]}</dd></div><div><dt>Rev.</dt><dd>{e["rev"]}</dd></div>
<div><dt>Date</dt><dd>{e["date"]}</dd></div></dl>
</header>"""
    contents = [page1(d), page2(d), page3(d)] if kind == "informe" else [""]
    total = len(contents)
    pages = "".join(
        f"""<section class="page">{header}<main class="content">{content}</main>
<footer class="ftr" style="--p:{n / total:.2%}"><div class="ftr-conf">{e["confidentiality"]}</div>
<div class="ftr-bar"></div><div class="ftr-page">{n}<i>/</i>{total}</div></footer></section>"""
        for n, content in enumerate(contents, 1)
    )
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>{e["title"]}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap">
<style>{CSS}</style></head><body>{pages}</body></html>"""


def find_browser() -> str:
    for name in ("msedge", "chrome", "google-chrome", "chromium"):
        if found := shutil.which(name):
            return found
    for path in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                 r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                 r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
        if Path(path).exists():
            return path
    sys.exit("No se encontró Edge ni Chrome; indica la ruta con --navegador.")


def html_to_pdf(page_html: str, out: Path, browser: str) -> None:
    """Imprime el HTML a PDF con el navegador en modo headless."""
    out = out.resolve()
    out.unlink(missing_ok=True)
    # El perfil temporal evita chocar con un Edge/Chrome ya abierto; Windows puede tardar en liberarlo.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        src = Path(tmp) / "doc.html"
        src.write_text(page_html, encoding="utf-8")
        result = subprocess.run(
            [browser, "--headless=new", "--disable-gpu", f"--user-data-dir={Path(tmp) / 'profile'}",
             "--no-pdf-header-footer", "--virtual-time-budget=5000", f"--print-to-pdf={out}", src.as_uri()],
            capture_output=True, text=True, timeout=120,
        )
    if not out.exists():
        sys.exit(f"No se pudo generar el PDF.\n{result.stderr[-2000:]}")


def load_data(path: str | None) -> dict:
    """Combina los valores por defecto con los del JSON; rechaza claves desconocidas (erratas)."""
    if not path:
        return dict(DEFAULTS)
    user = json.loads(Path(path).read_text(encoding="utf-8-sig"))  # acepta BOM (Bloc de notas, PowerShell)
    if unknown := set(user) - set(DEFAULTS):
        sys.exit(f"Claves desconocidas en {path}: {', '.join(sorted(unknown))}")
    d = {**DEFAULTS, **user}
    if d["triage_decision"] not in ("", *DECISIONS):
        sys.exit(f"triage_decision debe ser vacío o uno de: {', '.join(DECISIONS)}")
    return d


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tipo", choices=["informe", "cabecera", "datos"])
    parser.add_argument("--datos", help="JSON con los campos a rellenar (ver 'datos')")
    parser.add_argument("-o", "--salida", help="PDF de salida (por defecto <code>-<tipo>.pdf)")
    parser.add_argument("--navegador", help="Ruta a msedge.exe o chrome.exe")
    args = parser.parse_args()

    if args.tipo == "datos":
        print(json.dumps(DEFAULTS, indent=2, ensure_ascii=False))
        return
    d = load_data(args.datos)
    out = Path(args.salida or f"{d['code']}-{args.tipo}.pdf")
    html_to_pdf(build_html(args.tipo, d), out, args.navegador or find_browser())
    print(f"Generado: {out}")


if __name__ == "__main__":
    main()

