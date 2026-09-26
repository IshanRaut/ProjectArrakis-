---
name: visual-docs
description: Build a designed PDF from a self-contained HTML/CSS source and inspect the rendered result before delivery.
---
# Visual documents

Use `python3 scripts/render_pdf.py source.html output.pdf` from the project root. Chromium is required. Use a consistent palette, type scale and spacing, with one clear idea per page. Use only licensed images you have rights to use; cite factual claims. The output is a PDF, not an editable PowerPoint. Then render each page to images or open the PDF, inspect actual pixels for overflow, crop, contrast, missing glyphs, and hierarchy, and fix it before sharing. If an editable PPTX is required, do not pretend this PDF is editable; ask for a separate route.
