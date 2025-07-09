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
        Convierte páginas seleccionadas de un PDF a imágenes JPG.
        
        Args:
            pdf_path: Ruta al archivo PDF
            dpi: Resolución en puntos por pulgada
            selected_pages: Lista de índices de página a convertir (base 0), o None para todas
        """
        try:
            doc = fitz.open(pdf_path)
            image_paths = []
            
            # Determinar qué páginas procesar
            if selected_pages is None:
                # Procesar todas las páginas
                pages_to_process = range(len(doc))
            else:
                # Procesar solo las páginas seleccionadas
                # Asegurarse de que los índices están dentro del rango
                pages_to_process = [p for p in selected_pages if 0 <= p < len(doc)]
                print(f"Procesando páginas seleccionadas: {[p+1 for p in pages_to_process]}")
            
            for page_num in pages_to_process:
                try:
                    # Renderizar página
                    page = doc[page_num]
                    pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
                    image_path = os.path.join(self.output_dir, f"{os.path.basename(pdf_path)}_page_{page_num}.jpg")
                    
                    # Guardar imagen
                    pix.save(image_path, output="jpeg", jpg_quality=90)
                    print("pathhhhhhhhhhhhhh",image_path)
                    image_paths.append((page_num, image_path))  # Guardar número de página junto con la ruta
                    print(f"Página {page_num+1} convertida exitosamente")
                except Exception as e:
                    print(f"Error al procesar la página {page_num+1}: {e}")
                    # Código para manejar errores de página
            
            doc.close()
            # Ordenar por número de página para mantener el orden correcto
            image_paths.sort(key=lambda x: x[0])
            # Devolver solo las rutas de las imágenes
            return [path for _, path in image_paths]
        except Exception as e:
            print(f"Error al abrir el PDF {pdf_path}: {e}")
            return []

    
    def get_image_dimensions(self, pdf_path, page_num=0, dpi=300):
        """Obtiene las dimensiones de una página específica."""
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
        width, height = pix.width, pix.height
        doc.close()
        return width, height
    
    def repair_pdf(self, input_path, output_path=None):
        """Intenta reparar un PDF dañado."""
        if output_path is None:
            base_name = os.path.basename(input_path)
            output_path = os.path.join(self.output_dir, f"repaired_{base_name}")
        
        try:
            print(f"Intentando reparar PDF: {input_path}")
            # Abrir el PDF en modo de reparación
            doc = fitz.open(input_path)
            # Guardar el PDF reparado
            doc.save(output_path, garbage=4, clean=True, deflate=True)
            doc.close()
            print(f"PDF reparado guardado en: {output_path}")
            return output_path
        except Exception as e:
            print(f"No se pudo reparar el PDF: {e}")
            return 
        
    