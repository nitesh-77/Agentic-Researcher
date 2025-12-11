import os
import markdown2
from xhtml2pdf import pisa
from datetime import datetime
import tempfile
from typing import Optional

class PDFGenerator:
    """Generate PDF reports from markdown content"""

    def __init__(self):
        self.temp_dir = "temp"
        os.makedirs(self.temp_dir, exist_ok=True)

    def markdown_to_html(self, markdown_content: str, title: str = "Research Report") -> str:
        """Convert markdown to HTML with styling"""

        # Add header with metadata
        header = f"""
# {title}

**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Research Session:** Technical Analysis

---

"""

        full_content = header + markdown_content

        # Convert to HTML with extras
        html_content = markdown2.markdown(
            full_content,
            extras=[
                'fenced-code-blocks',
                'tables',
                'header-ids',
                'toc',
                'code-friendly'
            ]
        )

        # Add CSS styling for the PDF
        styled_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{title}</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1 {{
                    color: #2c3e50;
                    border-bottom: 3px solid #3498db;
                    padding-bottom: 10px;
                    margin-bottom: 20px;
                }}
                h2 {{
                    color: #34495e;
                    border-bottom: 2px solid #ecf0f1;
                    padding-bottom: 5px;
                    margin-top: 30px;
                }}
                h3 {{
                    color: #7f8c8d;
                    margin-top: 25px;
                }}
                code {{
                    background-color: #f8f9fa;
                    padding: 2px 4px;
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                    font-size: 0.9em;
                }}
                pre {{
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    overflow-x: auto;
                    border-left: 4px solid #3498db;
                }}
                blockquote {{
                    border-left: 4px solid #3498db;
                    margin: 20px 0;
                    padding-left: 20px;
                    font-style: italic;
                    color: #555;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 20px 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 12px;
                    text-align: left;
                }}
                th {{
                    background-color: #f8f9fa;
                    font-weight: bold;
                }}
                .source {{
                    font-size: 0.9em;
                    color: #666;
                    background-color: #f8f9fa;
                    padding: 5px 10px;
                    border-radius: 3px;
                    margin: 5px 0;
                }}
                .metadata {{
                    background-color: #ecf0f1;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                    font-size: 0.9em;
                }}
                p {{
                    margin: 10px 0;
                    text-align: justify;
                }}
                ul, ol {{
                    margin: 10px 0;
                    padding-left: 25px;
                }}
                li {{
                    margin: 5px 0;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        return styled_html

    def generate_pdf(self, markdown_content: str, session_id: str, title: str = "Research Report") -> Optional[str]:
        """
        Generate a PDF from markdown content
        Returns the path to the generated PDF file
        """
        print("📄 Generating PDF report")

        try:
            # Convert to HTML
            html_content = self.markdown_to_html(markdown_content, title)

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"research_report_{session_id}_{timestamp}.pdf"
            filepath = os.path.join(self.temp_dir, filename)

            # Create PDF
            with open(filepath, 'w+b') as pdf_file:
                # Convert HTML to PDF
                pisa_status = pisa.CreatePDF(
                    html_content,
                    dest=pdf_file,
                    encoding='utf-8'
                )

                if pisa_status.err:
                    print(f"❌ Error generating PDF: {pisa_status.err}")
                    return None

            print(f"✅ PDF generated successfully: {filepath}")
            return filepath

        except Exception as e:
            print(f"❌ Exception generating PDF: {e}")
            return None

    def generate_entity_report(self, entities: dict, session_id: str) -> Optional[str]:
        """Generate a supplementary PDF with entity analysis"""
        markdown_content = f"""
# Entity Analysis Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary of Discovered Entities

This report provides a structured analysis of the key entities identified during the research process.

"""

        for category, items in entities.items():
            if items:
                markdown_content += f"## {category.title()}\n\n"
                for item in items[:20]:  # Top 20 per category
                    markdown_content += f"- {item}\n"
                markdown_content += f"\n*Total {category}: {len(items)} entities*\n\n"

        return self.generate_pdf(markdown_content, session_id + "_entities", "Entity Analysis Report")

def cleanup_temp_files(hours_old: int = 24):
    """Clean up old temporary files"""
    import glob
    import time

    temp_dir = "temp"
    if not os.path.exists(temp_dir):
        return

    current_time = time.time()
    cutoff_time = current_time - (hours_old * 3600)

    for file_path in glob.glob(os.path.join(temp_dir, "*.pdf")):
        try:
            if os.path.getmtime(file_path) < cutoff_time:
                os.remove(file_path)
                print(f"🗑️  Removed old temp file: {file_path}")
        except Exception as e:
            print(f"⚠️  Could not remove {file_path}: {e}")