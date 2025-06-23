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
        Añade círculos como anotaciones al PDF.
        
        Args:
            input_pdf: Ruta al PDF original
            circles_by_page: Diccionario {num_página: [(x, y, radio), ...]}
            output_pdf: Ruta donde guardar el PDF anotado
            dpi: DPI usados para la conversión a imagen (para escalar coordenadas)
        """
        if output_pdf is None:
            base_name = os.path.basename(input_pdf)
            output_pdf = os.path.join(self.output_dir, f"annotated_{base_name}")
            self.input_pdf = input_pdf
        # Abrir documento
        doc = fitz.open(input_pdf)
        
        # Factor de escala para convertir de coordenadas de imagen a PDF
        scale_factor = 72 / dpi
        
        # Para cada página con círculos
        for page_num, circles in circles_by_page.items():
            page = doc[int(page_num)]
            
            for x, y, radius in circles:
                # Escalar coordenadas
                x_pdf = x * scale_factor
                y_pdf = y * scale_factor
                radius_pdf = radius * scale_factor
                
                # Crear anotación de círculo
                circle = page.add_circle_annot((x_pdf - radius_pdf, y_pdf - radius_pdf, 
                                              x_pdf + radius_pdf, y_pdf + radius_pdf))
                
                # Configurar propiedades
                circle.set_border(width=2)
                circle.set_colors(stroke=(1, 0, 0))  # Rojo
                circle.update(opacity=0.7)
                
                # Hacer la anotación toggle-able
                circle.set_flags(0)  # No ocultar por defecto
        
        # Guardar documento
        doc.save(output_pdf)
        doc.close()
        
        return output_pdf
    '''            
    def save_circles_to_json(self, circles_by_page, output_path):
        """Guarda la información de los círculos en un archivo JSON."""
        with open(output_path, 'w') as f:
            json.dump(circles_by_page, f, indent=2)
    '''
    def save_changes_to_json(self, original_pdf, formatted_circles_by_page, 
                           highlights_by_page=None, rotations_by_page=None, 
                           watermarks=None, output_path=None, dpi=300):
        print("Changes", formatted_circles_by_page)
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
            output_path = os.path.join(self.output_dir, f"{os.path.splitext(base_name)[0]}_changes.json")
        
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
                    "x": change[0],
                    "y": change[1],
                    "radius": change[2],
                    #"change_type": change.get("change_type", "unknown"),
                    #"description": change.get("description", f"Cambio {len(json_data['pages'][page_key]['changes']) + 1}"),
                    #"selected": change.get("selected", True)
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
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        
        return output_path