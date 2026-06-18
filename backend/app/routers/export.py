"""
Exports a chat session's conversation history to PDF.

Satisfies the 'Save the Conversation History in PDF format locally' requirement.
"""

import io
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.routers.chat import SESSIONS

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/{session_id}/pdf")
def export_pdf(session_id: str):
    session = SESSIONS.get(session_id)
    if not session or not session.get("history"):
        raise HTTPException(status_code=404, detail="No conversation history found for this session")

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="PDF export requires the 'reportlab' package. Install with: pip install reportlab"
        ) from exc

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=16)
    meta_style = ParagraphStyle("meta", parent=styles["Normal"], textColor="#666666", fontSize=9)
    user_style = ParagraphStyle("user", parent=styles["Normal"], fontSize=11, spaceAfter=4,
                                 backColor="#EEF1FA", borderPadding=6)
    assistant_style = ParagraphStyle("assistant", parent=styles["Normal"], fontSize=11, spaceAfter=2,
                                      backColor="#CADCFC", borderPadding=6)
    evidence_style = ParagraphStyle("evidence", parent=styles["Normal"], fontSize=8.5,
                                     textColor="#555555", spaceAfter=10, leftIndent=10)

    elements = [
        Paragraph("Kavach - KSP Crime Intelligence Assistant", title_style),
        Paragraph(f"Session: {session_id} &nbsp;|&nbsp; Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}", meta_style),
        Spacer(1, 8),
        HRFlowable(width="100%", color="#1E2761"),
        Spacer(1, 8),
    ]

    for entry in session["history"]:
        if entry["role"] == "user":
            elements.append(Paragraph(f"<b>Investigator:</b> {entry['message']}", user_style))
        else:
            elements.append(Paragraph(f"<b>Kavach:</b> {entry['message']}", assistant_style))
            if entry.get("evidence"):
                elements.append(Paragraph(f"Evidence: {entry['evidence']}", evidence_style))

    doc.build(elements)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=kavach_conversation_{session_id}.pdf"},
    )
