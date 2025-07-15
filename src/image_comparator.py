# image_comparator.py
import numpy as np
from PIL import Image
import cv2

class ImageComparator:
    def __init__(self, threshold = 1):
        self.threshold = threshold
          # Umbral para diferencias (0-255)
        self.min_contour_area = 180
        self.kernel = np.ones((2, 2), np.uint8)
    
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
        5. Resalta píxeles diferentes en verde claro sobre la imagen original en color
        """

        # 1) Cargar imágenes
        #img1 = self.load_image(img1_input)
        #img2 = self.load_image(img2_input)

        img1 = self.load_image(img1_input)

        img2 = self.load_image(img2_input)

        if img1.shape != img2.shape:
            print("Resizing img2....")
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]), interpolation=cv2.INTER_AREA)

        # 2) Asegurar que son B/N para procesarlas
        if len(img1.shape) > 2:
            img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        if len(img2.shape) > 2:
            img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        # 3) Binarización (umbral)
        _, bin1 = cv2.threshold(img1, 230, 255, cv2.THRESH_BINARY)
        _, bin2 = cv2.threshold(img2, 230, 255, cv2.THRESH_BINARY)

        # 4) Diferencia absoluta
        diff = cv2.absdiff(bin1, bin2)

        # 5) Operaciones morfológicas para limpiar ruido
        diff_processed = cv2.dilate(diff, self.kernel, iterations=1)

        # Guardar máscara si quieres revisar
        cv2.imwrite("diff_mask.png", diff_processed)

        # 6) Encontrar contornos significativos
        contours, _ = cv2.findContours(diff_processed, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        significant_contours = [c for c in contours if cv2.contourArea(c) >= self.min_contour_area]

        print("Contours:", len(contours))
        print("Significant contours:", len(significant_contours))

        # 7) Extraer coordenadas de los contornos
        diff_coords = []
        for contour in significant_contours:
            for point in contour:
                x, y = point[0]
                diff_coords.append((x, y))

        # 8) --> INTEGRACIÓN NUEVA: resaltar con máscara en la imagen ORIGINAL EN COLOR

        # A) Cargar de nuevo la imagen original en color (no la B/N)
        img2_orig_color = self.load_image(img2_input)
        if len(img2_orig_color.shape) == 2:
            img2_orig_color = cv2.cvtColor(img2_orig_color, cv2.COLOR_GRAY2BGR)

        # B) Verificar que diff_processed y img2_orig_color tengan misma forma base
        print("diff_processed",diff_processed.shape)
        print("img1_orig_color",img1.shape)
        if diff_processed.shape[:2] != img2_orig_color.shape[:2]:
            print(f"Redimensionando diff_processed de {diff_processed.shape} a {img2_orig_color.shape[:2]}")
            diff_processed = cv2.resize(
                diff_processed,
                (img2_orig_color.shape[1], img2_orig_color.shape[0]),
                interpolation=cv2.INTER_NEAREST
            )

        print("diff_processed",diff_processed.shape)
        print("img2_orig_color",img2_orig_color.shape)

        # Crear máscara booleana
        mask = diff_processed == 255

        # Crear máscara en color verde
        mask_color = np.zeros((diff_processed.shape[0], diff_processed.shape[1], 3), dtype=np.uint8)
        mask_color[mask] = [0, 255, 0]

        # OPCIONAL: guarda para revisar
        cv2.imwrite("mask_green.png", mask_color)

        # Asegurar tamaños iguales
        if mask_color.shape != img2_orig_color.shape:
            print("No son del mismo tamano")
            mask_color = cv2.resize(
                mask_color,
                (img2_orig_color.shape[1], img2_orig_color.shape[0]),
                interpolation=cv2.INTER_NEAREST
            )
        else:
            print("Son del mismo tamano")

        # Combina con la imagen original usando addWeighted
        highlighted = cv2.addWeighted(img2_orig_color, 1.0, mask_color, 1.0, 0)
        
        # Usa PIL para guardar con DPI
        #im_pil = Image.fromarray(cv2.cvtColor(highlighted, cv2.COLOR_BGR2RGB))
        #im_pil.save("highlighted_result.png", dpi=(300, 300))  # O el DPI que uses en tu PDF

        # 9) Devuelve coordenadas de diferencias + imagen resaltada + tamaño
        return diff_coords, highlighted, img1.shape