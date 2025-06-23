# json_saver.py
import json
import os
import datetime

class PDFJsonSaver:
    """
    Clase para guardar cambios aplicados a un PDF en un archivo JSON.
    """
    def __init__(self, output_dir='data/output'):
        self.output_dir = output_dir
        self.output_path = None
        os.makedirs(output_dir, exist_ok=True)
    
    def save_changes_to_json(self, original_pdf, formatted_circles_by_page, 
                           highlights_by_page=None, rotations_by_page=None, 
                           watermarks=None, output_path=None, dpi=300):
        """
        Guarda los cambios aplicados a un PDF en un archivo JSON.
        
        Args:
            original_pdf: Ruta al PDF original
            formatted_circles_by_page: Diccionario de cambios por página
            highlights_by_page: Diccionario de highlights por página
            rotations_by_page: Diccionario de rotaciones por página
            watermarks: Lista de marcas de agua aplicadas
            output_path: Ruta donde guardar el archivo JSON
            dpi: DPI usados para la conversión a imagen
        
        Returns:
            Ruta al archivo JSON guardado
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
        
        # Agregar información de cambios por página
        for page_num, changes in formatted_circles_by_page.items():
            # Convertir a string ya que las claves JSON deben ser strings
            page_key = str(page_num)
            
            if page_key not in json_data["pages"]:
                json_data["pages"][page_key] = {
                    "changes": [],
                    "highlights": [],
                    "rotation": 0
                }
            
            # Agregar cambios a la página
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
        
        # Agregar highlights por página si están disponibles
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
        
        # Agregar rotaciones por página si están disponibles
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
        
        # Guardar el JSON
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        
        return self.output_path
    
    def extract_highlights_from_pdf(self, pdf_document, dpi=300):
        """
        Extrae información de highlights de un documento PDF.
        
        Args:
            pdf_document: Documento PDF abierto con PyMuPDF
            dpi: DPI usados para la conversión a imagen
        
        Returns:
            Diccionario con información de highlights por página
        """
        highlights_by_page = {}
        
        # Factor de escala para convertir de coordenadas PDF a imagen
        scale_factor = dpi / 72
        
        # Recorrer cada página del documento
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            highlights = []
            
            # Buscar anotaciones de tipo highlight
            for annot in page.annots():
                if annot.type[1] == "Highlight":
                    rect = annot.rect
                    
                    # Convertir coordenadas de PDF a imagen
                    x0 = rect.x0 * scale_factor
                    y0 = rect.y0 * scale_factor
                    x1 = rect.x1 * scale_factor
                    y1 = rect.y1 * scale_factor
                    
                    # Extraer color
                    color = annot.colors.get("stroke", [1, 1, 0])  # Amarillo por defecto
                    
                    # Extraer opacidad
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
        Extrae información de rotaciones de un documento PDF.
        
        Args:
            pdf_document: Documento PDF abierto con PyMuPDF
        
        Returns:
            Diccionario con información de rotaciones por página
        """
        rotations_by_page = {}
        
        # Recorrer cada página del documento
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            rotation = page.rotation
            
            if rotation != 0:
                rotations_by_page[page_num] = rotation
        
        return rotations_by_page
