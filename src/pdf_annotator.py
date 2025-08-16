# pdf_annotator.py
import fitz  # PyMuPDF
import os
import json
import datetime

class PDFAnnotator:
    def __init__(self, output_dir='data/output'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def add_circle_annotations(self, input_pdf, circles_by_page, output_pdf=None, dpi=300):
        """
        Adds circles as annotations to the PDF.
        """
        if output_pdf is None:
            base_name = os.path.basename(input_pdf)
            output_pdf = os.path.join(self.output_dir, f"annotated_{base_name}")

        # Ensure that output_pdf is not the same as input_pdf
        if os.path.abspath(output_pdf) == os.path.abspath(input_pdf):
            base_name = os.path.basename(input_pdf)
            output_pdf = os.path.join(self.output_dir, f"annotated_{base_name}")
            print(f"Saving annotations to a new file: {output_pdf}")

        doc = fitz.open(input_pdf)
        scale_factor = 72 / dpi

        for page_num, circles in circles_by_page.items():
            page = doc[int(page_num)]
            for x, y, radius in circles:
                x_pdf = x * scale_factor
                y_pdf = y * scale_factor
                radius_pdf = radius * scale_factor
                circle = page.add_circle_annot((
                    x_pdf - radius_pdf, y_pdf - radius_pdf,
                    x_pdf + radius_pdf, y_pdf + radius_pdf
                ))
                circle.set_border(width=2)
                circle.set_colors(stroke=(1, 0, 0))
                circle.update(opacity=0.7)
                circle.set_flags(0)

        doc.save(output_pdf)
        doc.close()
        return output_pdf

    def save_changes_to_json(self, original_pdf, formatted_circles_by_page, 
                           highlights_by_page=None, rotations_by_page=None, 
                           watermarks=None, output_path=None, dpi=300):
        print("Changes", formatted_circles_by_page)
        """
        Saves the changes applied to a PDF to a JSON file.
        
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
            output_path = os.path.join(self.output_dir, f"{os.path.splitext(base_name)[0]}_changes.json")
        
        # Initialize JSON structure
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
        
        # Add page changes information
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
                    "x": change[0],
                    "y": change[1],
                    "radius": change[2],
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
        
        # Save JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        
        return output_path