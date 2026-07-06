import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from config import TEMP_DIR

def generate_study_notes_pdf(user_id: int, topic_title: str, explanatory_text: str) -> str:
    """
    Generates a clean, professionally formatted PDF for the given study notes.
    """
    file_path = os.path.join(TEMP_DIR, f"Notes_{user_id}_{int(os.getpid())}.pdf")
    doc = SimpleDocTemplate(
        file_path,
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom elegant styles
    title_style = ParagraphStyle(
        name='PDFTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#1A365D'),
        spaceAfter=15
    )

    body_style = ParagraphStyle(
        name='PDFBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=11,
        leading=16,
        textColor=colors.HexColor('#2D3748'),
        spaceAfter=10
    )

    story = []

    # Title Section
    story.append(Paragraph(f"Study Notes: {topic_title}", title_style))
    story.append(Spacer(1, 10))

    # Normalize text format for ReportLab compatibility
    clean_text = explanatory_text.replace("\n", "<br/>")
    story.append(Paragraph(clean_text, body_style))

    # Build Document
    doc.build(story)
    return file_path

def safe_cleanup(file_path: str):
    """
    Safely removes transient system files to mitigate runtime disk consumption.
    """
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error executing storage sweep on {file_path}: {e}")