# image_comparator.py
import numpy as np
from PIL import Image
import cv2

class ImageComparator:
    def __init__(self, threshold=3):
        self.threshold = threshold  # Umbral para diferencias (0-255)
        self.min_contour_area = 5
        self.kernel = np.ones((3, 3), np.uint8)
    
    @staticmethod
    def load_image(image_input):
        #Carga una imagen desde ruta o la convierte si es PIL
        if isinstance(image_input, str):  # Si es una ruta
            img = cv2.imread(image_input)
            if img is None:
                raise ValueError(f"No se pudo cargar la imagen: {image_input}")
            return img
        elif isinstance(image_input, Image.Image):  # Si es PIL (de pdf2image)
            return cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
        else:
            return image_input  # Asume que ya es OpenCV
    
    def find_differences(self, img1_input, img2_input):
        """
        Detecta diferencias en imágenes B/N usando solo OpenCV:
        1. Convierte a escala de grises (si no lo están)
        2. Binariza las imágenes
        3. Encuentra diferencias absolutas
        4. Filtra y resalta cambios
        """

        img1 = self.load_image(img1_input)
        img2 = self.load_image(img2_input)

        # Asegurar que son imágenes B/N (1 canal)
        if len(img1.shape) > 2:
            img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        if len(img2.shape) > 2:
            img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        # Binarización (thresholding adaptativo para mayor robustez)
        _, bin1 = cv2.threshold(img1, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _, bin2 = cv2.threshold(img2, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Diferencia absoluta/pixeles que cambian entre ambas imagenes
        diff = cv2.absdiff(bin1, bin2)
        
        # Operaciones morfológicas para mejorar la detección(limpiar ruido)
        diff_processed = cv2.morphologyEx(diff, cv2.MORPH_OPEN, self.kernel)
        diff_processed = cv2.dilate(diff_processed, self.kernel, iterations=1)
        
        # Encontrar contornos significativos
        contours, _ = cv2.findContours(diff_processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        significant_contours = [c for c in contours if cv2.contourArea(c) >= self.min_contour_area]

        # Extraer coordenadas de los contornos encontrados
        diff_coords = []
        img2_color =  img2

        if len(significant_contours) < 90:

            for contour in significant_contours:
                for point in contour:
                    x, y = point[0]  # Obtener coordenadas (x, y)
                    diff_coords.append((x, y))
            
            # Resaltar cambios en la imagen original (en color rojo)
            if len(img2.shape) == 2:  # Si la imagen de entrada era B/N, la convertimos a color para el resaltado
                img2_color = cv2.cvtColor(img2, cv2.COLOR_GRAY2BGR)
            else:
                img2_color = img2.copy()
                
            cv2.drawContours(img2_color, significant_contours, -1, (0, 0, 255), 2)
            
            # Devolver coordenadas de diferencias + imagen resaltada
        return diff_coords, img2_color, img1.shape
    