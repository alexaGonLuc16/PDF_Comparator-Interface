# pdf_processor.py
import os
import fitz  # PyMuPDF
import numpy as np
import cv2
from PIL import Image

class PDFProcessor:
    def __init__(self):
        self.output_dir = 'data/temp'
        os.makedirs(self.output_dir, exist_ok=True)
    
    def pdf_to_images(self, pdf_path, dpi=300, selected_pages=None):
        print("Selected pages",selected_pages)
        """
        Convert selected pages of a PDF to JPG images.
        
        Args:
        pdf_path: Path to the PDF file
        dpi: Resolution in dots per inch
        selected_pages: List of page indices to convert (0-based), or None for all
        """
        try:
            doc = fitz.open(pdf_path)
            image_paths = []
            
            # Determine which pages to process
            if selected_pages is None:
                # Process all pages
                pages_to_process = range(len(doc))
            else:
                # Process only selected pages
                # Ensure that indices are within the valid range
                pages_to_process = [p for p in selected_pages if 0 <= p < len(doc)]
                print(f"Procesando páginas seleccionadas: {[p+1 for p in pages_to_process]}")
            
            for page_num in pages_to_process:
                try:
                    # Render page
                    page = doc[page_num]
                    pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
                    image_path = os.path.join(self.output_dir, f"{os.path.basename(pdf_path)}_page_{page_num}.jpg")
                    
                    # Save image
                    pix.save(image_path, output="jpeg", jpg_quality=90)
                    image_paths.append((page_num, image_path))  # Save page number along with the path
                    print(f"Page {page_num+1} successfully converted")
                except Exception as e:
                    print(f"Error processing page {page_num+1}: {e}")
                    # Code to handle page-specific errorsa
            
            doc.close()
            # Sort by page number to maintain correct order
            image_paths.sort(key=lambda x: x[0])
            # Return only image paths
            return [path for _, path in image_paths]
        except Exception as e:
            print(f"Error opening PDF {pdf_path}: {e}")
            return []

    
    def get_image_dimensions(self, pdf_path, page_num=0, dpi=300):
        """Gets the dimensions of a specific page."""
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
        width, height = pix.width, pix.height
        doc.close()
        return width, height
    
    def repair_pdf(self, input_path, output_path=None):
        """Attempts to repair a damaged PDF."""
        if output_path is None:
            base_name = os.path.basename(input_path)
            output_path = os.path.join(self.output_dir, f"repaired_{base_name}")
        
        try:
            print(f"Attempting to repair PDF: {input_path}")
            # Open the PDF in repair mode
            doc = fitz.open(input_path)
            # Save the repaired PDF
            doc.save(output_path, garbage=4, clean=True, deflate=True)
            doc.close()
            print(f"Repaired PDF saved at: {output_path}")
            return output_path
        except Exception as e:
            print(f"Could not repair the PDF: {e}")
            return 
        
    