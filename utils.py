import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from config import TEMP_DIR

# 🎨 1. ULTRA-ADVANCED PROFESSIONAL HEADER & FOOTER CANVAS
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


# 🚀 2. THE ULTIMATE RICH-UI SMART PDF GENERATOR
def generate_study_notes_pdf(user_id: int, topic: str, text_content: str) -> str:
    # 🧹 Clean emojis & markdown asterisks to prevent ReportLab crashes
    clean_text = re.sub(r'[^\x00-\x7F]+', ' ', text_content)
    clean_text = clean_text.replace('**', '')
    
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
    
    # 💎 ELITE TYPOGRAPHY & RICH TEXT STYLES
    title_style = ParagraphStyle(
        name='EliteDocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=22,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=12
    )

    body_style = ParagraphStyle(
        name='EliteBodyText',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=16,
        textColor=colors.HexColor('#1E293B') # Deep rich slate for ultra-clear reading
    )
    
    subheading_style = ParagraphStyle(
        name='EliteSubhead',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=18,
        textColor=colors.HexColor('#2563EB'), # Vibrant Royal Blue
        spaceBefore=14,
        spaceAfter=6
    )
    
    summary_style = ParagraphStyle(
        name='EliteSummary',
        parent=styles['BodyText'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=15,
        textColor=colors.HexColor('#065F46')
    )

    story = []

    # Main Document Subject Title Banner
    safe_topic = topic[:65] + "..." if len(topic) > 65 else topic
    story.append(Paragraph(f"<b>MODULE TOPIC:</b> {safe_topic}", title_style))
    story.append(Spacer(1, 6))

    # 🧠 RICH UI PARSER: Converts lines into Color-Accented Cards, Tables, and Highlights
    for line in clean_text.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # 1. Detect Page Headings (Page 1, Page 2, etc.)
        if line.startswith(('Page 1', 'Page 2', 'Page 3', 'Page 4', 'Page 5', 'Page 6')):
            story.append(Spacer(1, 10))
            story.append(Paragraph(f"✨ <b>{line}</b>", subheading_style))
            story.append(Spacer(1, 4))
            
        # 2. Detect Quick Summary -> Wrap in a Mint-Green Highlight Box
        elif line.startswith('Quick Summary'):
            summary_p = Paragraph(f"<b>💡 SMART SUMMARY:</b> {line.replace('Quick Summary:', '').strip()}", summary_style)
            summary_table = Table([[summary_p]], colWidths=[532])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#ECFDF5")), # Soft Mint Green
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#34D399")),     # Emerald Border
                ('TOPPADDING', (0,0), (-1,-1), 9),
                ('BOTTOMPADDING', (0,0), (-1,-1), 9),
                ('LEFTPADDING', (0,0), (-1,-1), 12),
                ('RIGHTPADDING', (0,0), (-1,-1), 12),
            ]))
            story.append(Spacer(1, 6))
            story.append(summary_table)
            story.append(Spacer(1, 10))
            
        # 3. Detect Tabular Data (Lines with colons like "Vitamin A: Milk, carrots") -> Creates 2-Column Grid Table
        elif ':' in line and not line.startswith('http') and len(line.split(':', 1)[0]) < 35:
            parts = line.split(':', 1)
            col1 = Paragraph(f"<b>{parts[0].strip()}</b>", body_style)
            col2 = Paragraph(parts[1].strip(), body_style)
            
            row_table = Table([[col1, col2]], colWidths=[150, 382])
            row_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING', (0,0), (-1,-1), 10),
                ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ]))
            story.append(row_table)
            story.append(Spacer(1, 4))
            
        # 4. Standard Text Points -> Packaged into Ultra-Modern Cards with Left Accent Bar
        else:
            p = Paragraph(line, body_style)
            # Creating a 2-column micro-table to add a beautiful blue left border line (Accent Bar)
            accent_bar = Table([['']], colWidths=[4], rowHeights=[None])
            accent_bar.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#2563EB")) # Royal Blue Left Bar
            ]))
            
            content_table = Table([[accent_bar, p]], colWidths=[6, 520])
            content_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")), # Light Slate Background
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),  # Subtle outer border
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ]))
            story.append(content_table)
            story.append(Spacer(1, 5))

    # Build the final PDF document
    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    return file_path


# 🛡️ 3. SAFE CLEANUP FUNCTION (CRITICAL SERVER SAFETY)
def safe_cleanup(file_path: str):
    """
    Safely removes transient system files to mitigate runtime disk consumption.
    """
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error cleaning file: {e}")
    
