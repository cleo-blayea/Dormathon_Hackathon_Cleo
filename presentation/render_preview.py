"""Render PDF pages as PNG for verification."""
import pypdfium2 as pdfium
import os

pdf_path = r"C:\Users\cleol\Documents\Dormathon\GenBuddy_Hackathon\presentation\GenBuddy_DORMATHON_2026.pdf"
out_dir = r"C:\Users\cleol\Documents\Dormathon\GenBuddy_Hackathon\presentation\preview"
os.makedirs(out_dir, exist_ok=True)

pdf = pdfium.PdfDocument(pdf_path)
n_pages = len(pdf)
print(f"PDF has {n_pages} pages")

for i in range(n_pages):
    page = pdf[i]
    bitmap = page.render(scale=1.0)
    pil_image = bitmap.to_pil()
    out_path = os.path.join(out_dir, f"pdf_slide_{i+1}.png")
    pil_image.save(out_path)
    print(f"Saved {out_path} ({pil_image.width}x{pil_image.height})")