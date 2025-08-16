# json_saver.py
import json
import os
import datetime

class PDFJsonSaver:
    """
    Class to save changes applied to a PDF into a JSON file.
    """
    def __init__(self, output_dir='data/output'):
        self.output_dir = output_dir
        self.output_path = None
        os.makedirs(output_dir, exist_ok=True)
    
    def save_changes_to_json(self, original_pdf, formatted_circles_by_page, 
                           highlights_by_page=None, rotations_by_page=None, 
                           watermarks=None, output_path=None, dpi=300):
        """
        Saves changes applied to a PDF into a JSON file.
        
        Args:
            original_pdf: Path to the original PDF
            formatted_circles_by_page: Dictionary of changes per page
            highlights_by_page: Dictionary of highlights per page
            rotations_by_page: Dictionary of rotations per page
            watermarks: List of applied watermarks
            output_path: Path to save the JSON file
            dpi: DPI used for image conversion
        
        Returns:
            Path to the saved JSON file
        """
        if not output_path:
            base_name = os.path.basename(original_pdf)
            self.output_path = os.path.join(self.output_dir, f"{os.path.splitext(base_name)[0]}_changes.json")
        
        # Inicializar estructura del JSON
        json_data = {
            "metadata": {
                "original_pdf": original_pdf,
                "processed_date": datetime.datetime.now().isoformat(),
                "version": "1.0",
                "dpi": dpi
            },
            "pages": {},
            "watermarks": watermarks or []
        }
        
        # Add change information per page
        for page_num, changes in formatted_circles_by_page.items():
            # Convert to string since JSON keys must be strings
            page_key = str(page_num)
            
            if page_key not in json_data["pages"]:
                json_data["pages"][page_key] = {
                    "changes": [],
                    "highlights": [],
                    "rotation": 0
                }
            
            # Add changes to the page
            for change in changes:
                change_data = {
                    "x": change["x"],
                    "y": change["y"],
                    "radius": change["radius"],
                    "change_type": change.get("change_type", "unknown"),
                    "description": change.get("description", f"Cambio {len(json_data['pages'][page_key]['changes']) + 1}"),
                    "selected": change.get("selected", True)
                }
                json_data["pages"][page_key]["changes"].append(change_data)
        
        # Add highlights per page if available
        if highlights_by_page:
            for page_num, highlights in highlights_by_page.items():
                page_key = str(page_num)
                
                if page_key not in json_data["pages"]:
                    json_data["pages"][page_key] = {
                        "changes": [],
                        "highlights": [],
                        "rotation": 0
                    }
                
                json_data["pages"][page_key]["highlights"] = highlights
        
        # Add rotations per page if available
        if rotations_by_page:
            for page_num, rotation in rotations_by_page.items():
                page_key = str(page_num)
                
                if page_key not in json_data["pages"]:
                    json_data["pages"][page_key] = {
                        "changes": [],
                        "highlights": [],
                        "rotation": 0
                    }
                
                json_data["pages"][page_key]["rotation"] = rotation
        
        # Save JSON
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        
        return self.output_path
    
    def extract_highlights_from_pdf(self, pdf_document, dpi=300):
        """
        Extracts highlight annotations from a PDF document.
        
        Args:
            pdf_document: PDF document opened with PyMuPDF
            dpi: DPI used for image conversion
        
        Returns:
            Dictionary with highlight information per page
        """
        highlights_by_page = {}
        
        # Scale factor to convert from PDF coordinates to image coordinates
        scale_factor = dpi / 72
        
        # Iterate through each page in the document
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            highlights = []
            
            # Search for highlight annotations
            for annot in page.annots():
                if annot.type[1] == "Highlight":
                    rect = annot.rect
                    
                    # Convert PDF coordinates to image coordinates
                    x0 = rect.x0 * scale_factor
                    y0 = rect.y0 * scale_factor
                    x1 = rect.x1 * scale_factor
                    y1 = rect.y1 * scale_factor
                    
                    # Extract color
                    color = annot.colors.get("stroke", [1, 1, 0])  # Amarillo por defecto
                    
                    # Extract opacity
                    opacity = getattr(annot, "opacity", 0.7)
                    
                    highlight_data = {
                        "x0": x0,
                        "y0": y0,
                        "x1": x1,
                        "y1": y1,
                        "color": color,
                        "opacity": opacity
                    }
                    
                    highlights.append(highlight_data)
            
            if highlights:
                highlights_by_page[page_num] = highlights
        
        return highlights_by_page
    
    def extract_rotations_from_pdf(self, pdf_document):
        """
        Extracts rotation information from a PDF document.
        
        Args:
            pdf_document: PDF document opened with PyMuPDF
        
        Returns:
            Dictionary with rotation information per page
        """
        rotations_by_page = {}
        
        # Iterate through each page in the document
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            rotation = page.rotation
            
            if rotation != 0:
                rotations_by_page[page_num] = rotation
        
        return rotations_by_page
