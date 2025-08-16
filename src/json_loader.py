# json_loader.py
import json
import os
import glob
import fitz  # PyMuPDF
from PyQt5.QtCore import pyqtSignal, QObject

class PDFJsonLoader(QObject):
    extracted_changes_signal = pyqtSignal(dict)  # Page, change, enabled

    """
    Class to load and apply saved changes from a JSON file to a PDF.
    """
    def __init__(self):
        super().__init__()
        self.json_data = None
        self.pdf_path = None
    
    def load_json(self, json_path):
        """Loads data from a JSON file."""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                self.json_data = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading JSON file: {e}")
            return False
    
    def extract_changes_by_page(self):
        """Extracts changes per page from the loaded JSON."""
        if not self.json_data:
            return {}
        
        self.changes_by_page = {}
        
        # Iterate over pages in the JSON
        for page_num, page_data in self.json_data.get("pages", {}).items():
            # Convert to integer since JSON keys are strings
            page_num_int = int(page_num)
            changes = page_data.get("changes", [])
            
            if changes:
                self.changes_by_page[page_num_int] = changes
            print(self.changes_by_page)
            self.extracted_changes_signal.emit(self.changes_by_page)
        return self.changes_by_page
    
    def extract_highlights_by_page(self):
        """Extracts highlights per page from the loaded JSON."""
        if not self.json_data:
            return {}
        
        highlights_by_page = {}
        
        # Iterate over pages in the JSON
        for page_num, page_data in self.json_data.get("pages", {}).items():
            # Convert to integer since JSON keys are strings
            page_num_int = int(page_num)
            highlights = page_data.get("highlights", [])
            
            if highlights:
                highlights_by_page[page_num_int] = highlights
        
        return highlights_by_page
    
    def extract_rotations_by_page(self):
        """Extracts page rotations from the loaded JSON."""
        if not self.json_data:
            return {}
        
        rotations_by_page = {}
        
        # Iterate over pages in the JSON
        for page_num, page_data in self.json_data.get("pages", {}).items():
            # Convert to integer since JSON keys are strings
            page_num_int = int(page_num)
            rotation = page_data.get("rotation", 0)
            
            if rotation != 0:
                rotations_by_page[page_num_int] = rotation
        
        return rotations_by_page
    
    def extract_watermarks(self):
        """Extracts watermark information from the loaded JSON."""
        if not self.json_data:
            return {}
        
        watermarks_by_page = {}
        
        # Iterate over pages in the JSON
        for page_num, page_data in self.json_data.get("pages", {}).items():
            # Convert to integer since JSON keys are strings
            page_num_int = int(page_num)
            watermark = page_data.get("watermarks")

            watermarks_by_page[page_num_int] = watermark
        
        return watermarks_by_page
    
    def apply_changes_to_pdf(self, pdf_path, output_path=None):
        """
        Applies changes saved in the JSON to a PDF.
        
        Args:
            pdf_path: Path to the PDF to which changes will be applied
            output_path: Path to save the PDF with applied changes
        
        Returns:
            Path to the PDF with applied changes
        """
        if not self.json_data:
            print("No JSON data loaded")
            return None
        
        if not output_path:
            base_name = os.path.basename(pdf_path)
            output_path = f"loaded_{base_name}"
        
        # Extract information from JSON
        changes_by_page = self.extract_changes_by_page()
        highlights_by_page = self.extract_highlights_by_page()
        rotations_by_page = self.extract_rotations_by_page()
        watermarks_by_page = self.extract_watermarks()
        
        # Get DPI from metadata or use default value
        dpi = self.json_data.get("metadata", {}).get("dpi", 300)
        
        # Open the PDF
        doc = fitz.open(pdf_path)
        
        # Scaling factor to convert from image coordinates to PDF
        scale_factor = 72 / dpi
        
        # Apply rotations
        for page_num, rotation in rotations_by_page.items():
            if 0 <= page_num < doc.page_count:
                page = doc[page_num]
                page.set_rotation(rotation)
        
        # Apply highlights
        for page_num, highlights in highlights_by_page.items():
            if 0 <= page_num < doc.page_count:
                page = doc[page_num]
                
                for highlight in highlights:
                    x0 = highlight["x0"] 
                    y0 = highlight["y0"] 
                    x1 = highlight["x1"]
                    y1 = highlight["y1"] 
                    
                    # Create rectangle for highlight
                    rect = fitz.Rect(x0, y0, x1, y1)
                    
                    # Get color and opacity if available
                    color = highlight.get("color", [1, 1, 0])  # Amarillo por defecto
                    opacity = highlight.get("opacity", 0.7)
                    
                    # Apply highlight
                    annot = page.add_highlight_annot(rect)
                    annot.set_colors(stroke=color)
                    annot.update(opacity=opacity)

        # Apply circles for changes
        for page_num, changes in changes_by_page.items():
            if 0 <= page_num < doc.page_count:
                page = doc[page_num]
                
                for change in changes:
                    x = change["x"] * scale_factor
                    y = change["y"] * scale_factor
                    radius = change["radius"] * scale_factor
                    change_type = change.get("change_type", "unknown")
                    
                    # Create circle annotation
                    circle = page.add_circle_annot((x - radius, y - radius, x + radius, y + radius))
                    
                    # Determine color based on change type
                    if change_type == "added":
                        color = (0, 0, 1)  # Blue
                    elif change_type == "removed":
                        color = (1, 0, 0)  # Red
                    elif change_type == "modified":
                        color = (0, 1, 0)  # Green
                    else:
                        color = (0.5, 0.5, 0.5)  # Gray
                    
                    # Set properties
                    circle.set_border(width=2)
                    circle.set_colors(stroke=color)
                    circle.update(opacity=0.7)
                    
                    # Save change type in metadata
                    info = circle.info
                    info["change_type"] = change_type
                    circle.set_info(info)
                    
                    # Make annotation toggle-able
                    circle.set_flags(0)
        
        print("watermarks by page", watermarks_by_page)
        try:
            # Apply watermarks
            for page_num, watermark in watermarks_by_page.items():

                if 0 <= page_num < doc.page_count and watermark != []:
                    page = doc[page_num]

                    page_rect = page.rect
                    
                    # Create a new image to maintain transparency
                    # In recent PyMuPDF versions we can use alpha directly
                    try:
                        # Try direct method with alpha parameter (recent versions)
                        page.insert_image(page_rect, filename = watermark["path"], overlay=False, alpha=watermark["opacity"])
                    except TypeError:
                        # If version doesn’t support alpha, use an alternative approach
                        img = fitz.open(watermark["path"])
                        pix = img[0].get_pixmap(alpha=True)
                        
                        # Manually adjust opacity
                        import numpy as np
                        samples = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                        if pix.alpha:  # If image has alpha channel
                            alpha_channel = samples[:, :, -1]
                            alpha_channel = (alpha_channel * opacity).astype(np.uint8)
                            samples[:, :, -1] = alpha_channel
                        
                        # Create a new pixmap with modified samples
                        new_pix = fitz.Pixmap(pix.colorspace, pix.width, pix.height, samples.tobytes(), alpha=pix.alpha)
                        page.insert_image(page_rect, pixmap=new_pix, overlay=False)
                        
                        # Clean up
                        img.close()
                        path = watermark["path"]
                    print(f"Watermark applied from: {path} with opacity {opacity:.1%}")
                    return True
            
        except Exception as e:
            print(f"Error applying watermark: {e}")
            
        # Apply watermarks
        # Note: This would require access to the original images.
        # To fully implement this functionality, we would need to:
        # 1. Verify that the images exist
        # 2. Implement a mechanism to store/retrieve the images
        
        # Save document
        doc.save(output_path)
        doc.close()
        
        return output_path
