# json_loader.py
import json
import os
import fitz  # PyMuPDF
from PyQt5.QtCore import pyqtSignal, QObject

class PDFJsonLoader(QObject):
    extracted_changes_signal = pyqtSignal(dict)  # Página, cambio, activado

    """
    Clase para cargar y aplicar cambios guardados en un archivo JSON a un PDF.
    """
    def __init__(self):
        super().__init__()
        self.json_data = None
        self.pdf_path = None
    
    def load_json(self, json_path):
        """Carga los datos desde un archivo JSON."""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                self.json_data = json.load(f)
            return True
        except Exception as e:
            print(f"Error al cargar el archivo JSON: {e}")
            return False
    
    def extract_changes_by_page(self):
        """Extrae los cambios por página del JSON cargado."""
        if not self.json_data:
            return {}
        
        self.changes_by_page = {}
        
        # Recorrer las páginas en el JSON
        for page_num, page_data in self.json_data.get("pages", {}).items():
            # Convertir a entero ya que las claves JSON son strings
            page_num_int = int(page_num)
            changes = page_data.get("changes", [])
            
            if changes:
                self.changes_by_page[page_num_int] = changes
            print(self.changes_by_page)
            self.extracted_changes_signal.emit(self.changes_by_page)
        return self.changes_by_page
    
    def extract_highlights_by_page(self):
        """Extrae los highlights por página del JSON cargado."""
        if not self.json_data:
            return {}
        
        highlights_by_page = {}
        
        # Recorrer las páginas en el JSON
        for page_num, page_data in self.json_data.get("pages", {}).items():
            # Convertir a entero ya que las claves JSON son strings
            page_num_int = int(page_num)
            highlights = page_data.get("highlights", [])
            
            if highlights:
                highlights_by_page[page_num_int] = highlights
        
        return highlights_by_page
    
    def extract_rotations_by_page(self):
        """Extrae las rotaciones por página del JSON cargado."""
        if not self.json_data:
            return {}
        
        rotations_by_page = {}
        
        # Recorrer las páginas en el JSON
        for page_num, page_data in self.json_data.get("pages", {}).items():
            # Convertir a entero ya que las claves JSON son strings
            page_num_int = int(page_num)
            rotation = page_data.get("rotation", 0)
            
            if rotation != 0:
                rotations_by_page[page_num_int] = rotation
        
        return rotations_by_page
    
    def extract_watermarks(self):
        """Extrae la información de marcas de agua del JSON cargado."""
        if not self.json_data:
            return {}
        
        watermarks_by_page = {}
        
        # Recorrer las páginas en el JSON
        for page_num, page_data in self.json_data.get("pages", {}).items():
            # Convertir a entero ya que las claves JSON son strings
            page_num_int = int(page_num)
            watermark = page_data.get("watermarks")

            watermarks_by_page[page_num_int] = watermark
        
        return watermarks_by_page
    
    def apply_changes_to_pdf(self, pdf_path, output_path=None):
        """
        Aplica los cambios guardados en el JSON a un PDF.
        
        Args:
            pdf_path: Ruta al PDF al que se aplicarán los cambios
            output_path: Ruta donde guardar el PDF con cambios aplicados
        
        Returns:
            Ruta al PDF con cambios aplicados
        """
        if not self.json_data:
            print("No hay datos JSON cargados")
            return None
        
        if not output_path:
            base_name = os.path.basename(pdf_path)
            output_path = f"loaded_{base_name}"
        
        # Extraer información del JSON
        changes_by_page = self.extract_changes_by_page()
        highlights_by_page = self.extract_highlights_by_page()
        rotations_by_page = self.extract_rotations_by_page()
        watermarks_by_page = self.extract_watermarks()
        
        # Obtener DPI de los metadatos o usar valor por defecto
        dpi = self.json_data.get("metadata", {}).get("dpi", 300)
        
        # Abrir el PDF
        doc = fitz.open(pdf_path)
        
        # Factor de escala para convertir de coordenadas de imagen a PDF
        scale_factor = 72 / dpi
        
        # Aplicar rotaciones
        for page_num, rotation in rotations_by_page.items():
            if 0 <= page_num < doc.page_count:
                page = doc[page_num]
                page.set_rotation(rotation)
        
        # Aplicar highlights
        for page_num, highlights in highlights_by_page.items():
            if 0 <= page_num < doc.page_count:
                page = doc[page_num]
                
                for highlight in highlights:
                    x0 = highlight["x0"] 
                    y0 = highlight["y0"] 
                    x1 = highlight["x1"]
                    y1 = highlight["y1"] 
                    
                    # Crear el rectángulo para el highlight
                    rect = fitz.Rect(x0, y0, x1, y1)
                    
                    # Obtener color y opacidad si están disponibles
                    color = highlight.get("color", [1, 1, 0])  # Amarillo por defecto
                    opacity = highlight.get("opacity", 0.7)
                    
                    # Aplicar highlight
                    annot = page.add_highlight_annot(rect)
                    annot.set_colors(stroke=color)
                    annot.update(opacity=opacity)

        # Aplicar círculos para cambios
        for page_num, changes in changes_by_page.items():
            if 0 <= page_num < doc.page_count:
                page = doc[page_num]
                
                for change in changes:
                    x = change["x"] * scale_factor
                    y = change["y"] * scale_factor
                    radius = change["radius"] * scale_factor
                    change_type = change.get("change_type", "unknown")
                    
                    # Crear anotación de círculo
                    circle = page.add_circle_annot((x - radius, y - radius, x + radius, y + radius))
                    
                    # Determinar color según el tipo de cambio
                    if change_type == "added":
                        color = (0, 0, 1)  # Azul
                    elif change_type == "removed":
                        color = (1, 0, 0)  # Rojo
                    elif change_type == "modified":
                        color = (0, 1, 0)  # Verde
                    else:
                        color = (0.5, 0.5, 0.5)  # Gris
                    
                    # Configurar propiedades
                    circle.set_border(width=2)
                    circle.set_colors(stroke=color)
                    circle.update(opacity=0.7)
                    
                    # Guardar tipo de cambio en los metadatos
                    info = circle.info
                    info["change_type"] = change_type
                    circle.set_info(info)
                    
                    # Hacer la anotación toggle-able
                    circle.set_flags(0)
        
        print("watermarks by page", watermarks_by_page)
        try:
            # Aplicar watermarks
            for page_num, watermark in watermarks_by_page.items():

                if 0 <= page_num < doc.page_count:
                    page = doc[page_num]

                    page_rect = page.rect
                    
                    # Crear una nueva imagen para mantener la transparencia
                    # En versiones recientes de PyMuPDF podemos usar alpha directamente
                    try:
                        # Intenta usar el método directo con parámetro alpha (versiones recientes)
                        page.insert_image(page_rect, filename = watermark["path"], overlay=False, alpha=watermark["opacity"])
                    except TypeError:
                        # Si la versión no soporta alpha, usamos un enfoque alternativo
                        img = fitz.open(watermark["path"])
                        pix = img[0].get_pixmap(alpha=True)
                        
                        # Ajustar opacidad manualmente
                        import numpy as np
                        samples = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                        if pix.alpha:  # Si la imagen tiene canal alfa
                            alpha_channel = samples[:, :, -1]
                            alpha_channel = (alpha_channel * opacity).astype(np.uint8)
                            samples[:, :, -1] = alpha_channel
                        
                        # Crear un nuevo pixmap con los samples modificados
                        new_pix = fitz.Pixmap(pix.colorspace, pix.width, pix.height, samples.tobytes(), alpha=pix.alpha)
                        page.insert_image(page_rect, pixmap=new_pix, overlay=False)
                        
                        # Limpiar
                        img.close()
                        path = watermark["path"]
                    print(f"Marca de agua aplicada desde: {path} con opacidad {opacity:.1%}")
                    return True
            
        except Exception as e:
            print(f"Error al aplicar la marca de agua: {e}")
            
        # Aplicar marcas de agua
        # Nota: Esto requeriría acceso a las imágenes originales.
        # Para implementar completamente esta funcionalidad, se necesitaría:
        # 1. Verificar que las imágenes existen
        # 2. Implementar un mecanismo para almacenar/recuperar las imágenes
        
        # Guardar el documento
        doc.save(output_path)
        doc.close()
        
        return output_path
