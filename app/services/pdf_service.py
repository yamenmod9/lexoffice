from __future__ import annotations

from io import BytesIO


def build_simple_pdf(title: str, lines: list[str]) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise RuntimeError("reportlab is required for PDF generation") from exc

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 60

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, title)
    y -= 30

    pdf.setFont("Helvetica", 11)
    for line in lines:
        if y < 60:
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = height - 60
        pdf.drawString(50, y, str(line)[:130])
        y -= 18

    pdf.save()
    buffer.seek(0)
    return buffer.read()


def render_template_content(template_content: str, data: dict):
    rendered = template_content
    for key, value in data.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    return rendered
