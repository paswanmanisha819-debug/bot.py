import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from config import TEMP_DIR

# 🎨 1. CLEAN & PROFESSIONAL HEADER/FOOTER
def add_header_footer(canvas, doc):
    canvas.saveState()
    
    # --- TOP HERO BANNER (Sleek Navy Blue) ---
    canvas.setFillColor(colors.HexColor("#0F172A"))
    canvas.rect(0, 735, 612, 65, fill=1, stroke=0)
    
    canvas.setFillColor(colors.HexColor("#3B82F6"))
    canvas.rect(0, 730, 612, 5, fill=1, stroke=0)
    
    # Header Title
    canvas.setFillColor(colors.white)
    canvas.setFont('Helvetica-Bold', 16)
    canvas.drawCentredString(306, 762, "ADITYA'S ELITE AI STUDY PORTAL")
    
    canvas.setFillColor(colors.HexColor("#94A3B8"))
    canvas.setFont('Helvetica-Oblique', 10)
    canvas.drawCentredString(306, 742, "Premium Study Notes & Analysis")
    
    # --- FOOTER ---
    canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
    canvas.setLineWidth(1)
    canvas.line(40, 40, 572, 40)
    
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.setFont('Helvetica', 9)
    canvas.drawString(40, 25, "Engineered by Aditya | @aadit_paswan.007")
    canvas.drawRightString(572, 25, f"Page {doc.page}")
    
    canvas.restoreState()


# 🚀 2. THE NEW "CLEAN-READ" PDF GENERATOR
def generate_study_notes_pdf(user_id: int, topic: str, text_content: str) -> str:
    # 🧹 Convert Markdown **bold** to real PDF <b>bold</b>
    clean_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text_content)
    # Remove unsupported weird unicode but keep basic formatting and table pipes (|)
    clean_text = re.sub(r'[^\x00-\x7F\xa9\xae]+', ' ', clean_text)
    
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        
    file_path = os.path.join(TEMP_DIR, f"Elite_Notes_{user_id}_{int(os.getpid())}.pdf")
    
    doc = SimpleDocTemplate(
        file_path, pagesize=letter,
        rightMargin=45, leftMargin=45, 
        topMargin=85, bottomMargin=55
    )

    styles = getSampleStyleSheet()
    
    # 💎 CLEAN TYPOGRAPHY (Focus on Readability)
    title_style = ParagraphStyle(
        name='EliteDocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold',
        fontSize=18, leading=24, textColor=colors.HexColor('#0F172A'), spaceAfter=15
    )

    body_style = ParagraphStyle(
        name='EliteBodyText', parent=styles['BodyText'], fontName='Helvetica',
        fontSize=11, leading=18, textColor=colors.HexColor('#1E293B'), spaceAfter=8
    )
    
    subheading_style = ParagraphStyle(
        name='EliteSubhead', parent=styles['Heading2'], fontName='Helvetica-Bold',
        fontSize=14, leading=20, textColor=colors.HexColor('#2563EB'),
        spaceBefore=15, spaceAfter=8
    )
    
    bullet_style = ParagraphStyle(
        name='EliteBullet', parent=styles['BodyText'], fontName='Helvetica',
        fontSize=11, leading=18, textColor=colors.HexColor('#1E293B'), 
        leftIndent=15, spaceAfter=6
    )

    story = []

    # Document Banner
    safe_topic = topic[:65] + "..." if len(topic) > 65 else topic
    story.append(Paragraph(f"<b>Subject:</b> {safe_topic}", title_style))
    story.append(Spacer(1, 10))

    lines = clean_text.split('\n')
    table_buffer = []

    # Function to render collected table rows into a real Grid Table
    def flush_table():
        if table_buffer:
            # Remove empty markdown divider rows (e.g., |---|---|)
            valid_rows = []
            for r in table_buffer:
                if all(re.match(r'^[\s\-]+$', cell.text) for cell in r): 
                    continue
                valid_rows.append(r)

            if valid_rows:
                # Balance columns so the table doesn't crash
                max_cols = max(len(r) for r in valid_rows)
                for r in valid_rows:
                    while len(r) < max_cols:
                        r.append(Paragraph("", body_style))
                
                # Auto-calculate width for 510px usable space
                col_widths = [510 / max_cols] * max_cols
                t = Table(valid_rows, colWidths=col_widths)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F1F5F9")), # Light Grey Header
                    ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#0F172A")),
                    ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")), # Real table lines
                    ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#94A3B8")),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('TOPPADDING', (0,0), (-1,-1), 8),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                    ('LEFTPADDING', (0,0), (-1,-1), 8),
                    ('RIGHTPADDING', (0,0), (-1,-1), 8),
                ]))
                story.append(t)
                story.append(Spacer(1, 10))
            table_buffer.clear()

    # 🧠 SMART PARSER (Reads line by line)
    for line in lines:
        line = line.strip()
        
        # Empty lines
        if not line:
            flush_table()
            continue

        # 1. TABLE DETECTION (Collects consecutive lines with '|')
        if '|' in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells:
                row = [Paragraph(f"{c}", body_style) for c in cells]
                table_buffer.append(row)
            continue
        else:
            flush_table() # If a non-table line comes, print the collected table

        # 2. HEADINGS (Page 1, # Topic)
        if line.startswith('Page ') or line.startswith('#'):
            clean_h = line.replace('#', '').strip()
            story.append(Spacer(1, 10))
            story.append(Paragraph(f"<b>{clean_h}</b>", subheading_style))
        
        # 3. HIGHLIGHT BOX (For Summaries)
        elif 'SUMMARY' in line.upper() or line.startswith('💡'):
            story.append(Spacer(1, 8))
            summary_p = Paragraph(f"<b>{line}</b>", ParagraphStyle(
                'SumTxt', fontName='Helvetica-Bold', fontSize=11, leading=16, textColor=colors.HexColor('#064E3B')
            ))
            t = Table([[summary_p]], colWidths=[510])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#ECFDF5")),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#10B981")),
                ('PADDING', (0,0), (-1,-1), 12),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))
            
        # 4. BULLET POINTS (*, -, •)
        elif line.startswith(('-', '*', '•')):
            # Replace markdown bullet with a clean PDF bullet
            clean_bullet = line[1:].strip()
            story.append(Paragraph(f"• &nbsp; {clean_bullet}", bullet_style))
            
        # 5. NORMAL PARAGRAPHS
        else:
            story.append(Paragraph(line, body_style))

    # Ensure any trailing table is printed
    flush_table()

    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    return file_path


# 🛡️ 3. SAFE CLEANUP FUNCTION
def safe_cleanup(file_path: str):
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error cleaning file: {e}")
