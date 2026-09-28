"""Comprobación rápida: python test_generar_informe.py"""
import re
import tempfile
from pathlib import Path

import generar_informe as g


def pdf_pages(pdf: Path) -> int:
    return len(re.findall(rb"/Type\s*/Page\b", pdf.read_bytes()))


def test_html_escapa_y_numera() -> None:
    page = g.build_html("informe", {**g.DEFAULTS, "summary": "<b>x</b> & y"})
    assert "&lt;b&gt;x&lt;/b&gt; &amp; y" in page
    assert page.count('<section class="page">') == 3
    assert "3<i>/</i>3" in page and "--p:100.00%" in page
    assert page.count('class="box"') == 4
    marked = g.build_html("informe", {**g.DEFAULTS, "triage_decision": "dismissed"})
    assert marked.count('class="box on"') == 1 and marked.count('class="box"') == 3


def test_pdfs() -> None:
    browser = g.find_browser()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        for kind, expected in (("informe", 3), ("cabecera", 1)):
            out = Path(tmp) / f"{kind}.pdf"
            g.html_to_pdf(g.build_html(kind, dict(g.DEFAULTS)), out, browser)
            assert pdf_pages(out) == expected, (kind, pdf_pages(out))


if __name__ == "__main__":
    test_html_escapa_y_numera()
    test_pdfs()
    print("OK")

