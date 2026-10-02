import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from config import TEMP_DIR

# 🎨 1. ULTRA-ADVANCED PROFESSIONAL HEADER & FOOTER
def add_header_footer(canvas, doc):
    canvas.saveState()
    
    # --- TOP HERO BANNER (Corporate Dark Navy Blue) ---
    canvas.setFillColor(colors.HexColor("#0F172A"))
    canvas.rect(0, 735, 612, 65, fill=1, stroke=0)
    
    # Vibrant Accent Blue Strip
    canvas.setFillColor(colors.HexColor("#3B82F6"))
    canvas.rect(0, 730, 612, 5, fill=1, stroke=0)
    
    # Header Main Title
    canvas.setFillColor(colors.white)
    canvas.setFont('Helvetica-Bold', 16)
    canvas.drawCentredString(306, 762, "ADITYA'S ELITE AI STUDY PORTAL")
    
    # Header Subtitle
    canvas.setFillColor(colors.HexColor("#94A3B8"))
    canvas.setFont('Helvetica-Oblique', 10)
    canvas.drawCentredString(306, 742, "Advanced Smart Vision Scanner & Ultra-Modern Notes Engine")
    
    # --- BOTTOM FOOTER DESIGN ---
    canvas.setStrokeColor(colors.HexColor("#CBD5E0"))
    canvas.setLineWidth(1)
    canvas.line(40, 40, 572, 40)
    
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.setFont('Helvetica-Bold', 9)
    canvas.drawString(40, 25, "Engineered by Aditya | @aadit_paswan.007")
    canvas.drawRightString(572, 25, f"Page {doc.page}")
    
    canvas.restoreState()


# 🚀 2. THE ULTIMATE RICH-UI SMART PDF GENERATOR (Fixes Markdown & Tables)
def generate_study_notes_pdf(user_id: int, topic: str, text_content: str) -> str:
    # 🧹 SMART CLEANUP: Converts Markdown **bold** to real PDF <b>bold</b>
    clean_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text_content)
    
    # Remove unsupported weird unicode but keep basic formatting and table pipes (|)
    clean_text = re.sub(r'[^\x00-\x7F\xa9\xae]+', ' ', clean_text)
    
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        
    file_path = os.path.join(TEMP_DIR, f"Elite_Notes_{user_id}_{int(os.getpid())}.pdf")
    
    # Document Setup with safe margins
    doc = SimpleDocTemplate(
        file_path,
        pagesize=letter,
        rightMargin=40, leftMargin=40, 
        topMargin=85, bottomMargin=55
    )

    styles = getSampleStyleSheet()
    
    # 💎 ELITE TYPOGRAPHY
    title_style = ParagraphStyle(
        name='EliteDocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold',
        fontSize=15, leading=22, textColor=colors.HexColor('#1E3A8A'), spaceAfter=12
    )

    body_style = ParagraphStyle(
        name='EliteBodyText', parent=styles['BodyText'], fontName='Helvetica',
        fontSize=10.5, leading=16, textColor=colors.HexColor('#1E293B')
    )
    
    subheading_style = ParagraphStyle(
        name='EliteSubhead', parent=styles['Heading2'], fontName='Helvetica-Bold',
        fontSize=13, leading=18, textColor=colors.HexColor('#2563EB'),
        spaceBefore=14, spaceAfter=6
    )
    
    summary_style = ParagraphStyle(
        name='EliteSummary', parent=styles['BodyText'], fontName='Helvetica-Bold',
        fontSize=10.5, leading=16, textColor=colors.HexColor('#065F46')
    )

    story = []

    # Main Document Banner
    safe_topic = topic[:65] + "..." if len(topic) > 65 else topic
    story.append(Paragraph(f"<b>MODULE TOPIC:</b> {safe_topic}", title_style))
    story.append(Spacer(1, 6))

    # 🧠 RICH UI PARSER: Intelligently handles Tables (|), Cards, and Summaries
    for line in clean_text.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # Ignore raw markdown table divider lines (e.g., |---|---|)
        if re.match(r'^[\s\|\-]+$', line) and len(line) > 3:
            continue
            
        # 1. Detect Headings
        if line.startswith('Page ') or line.startswith('#'):
            clean_heading = line.replace('#', '').strip()
            story.append(Spacer(1, 10))
            story.append(Paragraph(f"✨ <b>{clean_heading}</b>", subheading_style))
            story.append(Spacer(1, 4))
            
        # 2. Detect Smart Summary (Green Box)
        elif 'SUMMARY' in line.upper():
            summary_p = Paragraph(f"<b>💡 {line.replace('SUMMARY:', '').strip()}</b>", summary_style)
            summary_table = Table([[summary_p]], colWidths=[532])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#ECFDF5")),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#34D399")),
                ('LINEBEFORE', (0,0), (-1,-1), 5, colors.HexColor("#059669")),
                ('TOPPADDING', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10),
                ('LEFTPADDING', (0,0), (-1,-1), 12),
                ('RIGHTPADDING', (0,0), (-1,-1), 12),
            ]))
            story.append(Spacer(1, 6))
            story.append(summary_table)
            story.append(Spacer(1, 10))
            
        # 3. Detect Markdown Tables (Lines containing '|')
        elif '|' in line:
            # Extract cells by splitting via '|' and remove empty edge spaces
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if not cells:
                continue
                
            # Convert cells to Paragraphs for text-wrapping
            p_cells = [Paragraph(c, body_style) for c in cells]
            
            # Auto-calculate width so it fits perfectly on the 532px page
            col_width = 532 / len(cells)
            
            row_table = Table([p_cells], colWidths=[col_width] * len(cells))
            row_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")), # Grid lines inside table
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING', (0,0), (-1,-1), 8),
                ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(row_table)
            story.append(Spacer(1, 2))
            
        # 4. Standard Text -> Ultra-Modern Blue Accent Cards
        else:
            p = Paragraph(line, body_style)
            content_table = Table([[p]], colWidths=[532])
            content_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
                ('LINEBEFORE', (0,0), (-1,-1), 4, colors.HexColor("#2563EB")), 
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('LEFTPADDING', (0,0), (-1,-1), 12),
                ('RIGHTPADDING', (0,0), (-1,-1), 12),
            ]))
            story.append(content_table)
            story.append(Spacer(1, 4))

    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    return file_path


# 🛡️ 3. SAFE CLEANUP FUNCTION
def safe_cleanup(file_path: str):
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error cleaning file: {e}")
    
