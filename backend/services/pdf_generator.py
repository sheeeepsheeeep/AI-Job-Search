"""
Cover letter PDF generator using fpdf2.
Produces a professional, well-formatted single-page (or multi-page) PDF.
"""

import logging
import os
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

logger = logging.getLogger(__name__)


class CoverLetterPDF(FPDF):
    """Custom PDF class with header and footer for cover letters."""

    def __init__(self, candidate_name: str, company_name: str):
        super().__init__()
        self.candidate_name = candidate_name
        self.company_name = company_name

    def header(self):
        # Candidate name in header
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(26, 35, 126)  # Dark indigo
        self.cell(0, 12, self.candidate_name, align="C", new_x="LMARGIN", new_y="NEXT")

        # Horizontal rule
        self.set_draw_color(26, 35, 126)
        self.set_line_width(0.5)
        self.line(25, self.get_y() + 2, 185, self.get_y() + 2)
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def generate_cover_letter_pdf(
    content: str,
    candidate_name: str,
    company_name: str,
    output_path: str,
) -> str:
    """Generate a professional cover letter PDF.

    Args:
        content: The full text of the cover letter (plain text or simple
                 paragraphs separated by newlines).
        candidate_name: Name to display in the header / signature.
        company_name: Target company name for the header.
        output_path: Absolute or relative path where the PDF will be saved.

    Returns:
        The absolute path of the generated PDF file.
    """
    # Ensure output directory exists
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = CoverLetterPDF(candidate_name, company_name)
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()

    # Date — right-aligned
    date_str = datetime.now().strftime("%B %d, %Y")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(51, 51, 51)
    pdf.cell(0, 8, date_str, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Recipient
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(34, 34, 34)
    pdf.cell(0, 7, "Hiring Manager", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, company_name, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # Body paragraphs
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(34, 34, 34)

    paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
    for para_text in paragraphs:
        # Skip if it looks like "Dear Hiring Manager" (already in header area)
        pdf.multi_cell(0, 7, para_text, align="J")
        pdf.ln(4)

    # Signature
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, "Sincerely,", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, candidate_name, new_x="LMARGIN", new_y="NEXT")

    # Save
    pdf.output(str(out_path))
    abs_path = str(out_path.resolve())
    logger.info("Cover letter PDF generated: %s", abs_path)
    return abs_path
