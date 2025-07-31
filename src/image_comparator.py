# image_comparator.py
import numpy as np
from PIL import Image
import cv2

class ImageComparator:
    def __init__(self, threshold = 1):
        self.threshold = threshold
          # Umbral para diferencias (0-255)
        self.min_contour_area = 180
        self.kernel_erode = np.ones((2, 2), np.uint8)
        self.kernel_dilate = np.ones((2, 2), np.uint8)
    
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

        img1 = self.load_image(img1_input)
        img2 = self.load_image(img2_input)

        #merged_color_original = cv2.bitwise_and(img1, img2)
        #cv2.imwrite("merged_color_original.png", merged_color_original)

        if img1.shape != img2.shape:
            print("Resizing img2....")
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]), interpolation=cv2.INTER_AREA)

        # 2) Asegurar que son B/N para procesarlas
        if len(img1.shape) > 2:
            img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        if len(img2.shape) > 2:
            img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        # 3) Binarización (umbral)
        _, bin1 = cv2.threshold(img1, 240, 255, cv2.THRESH_BINARY)
        #cv2.imwrite("bin1.png", bin1)
        _, bin2 = cv2.threshold(img2, 240, 255, cv2.THRESH_BINARY)
        #cv2.imwrite("bin2.png", bin2)

        # 4) Diferencia absoluta
        diff_abs = cv2.absdiff(bin1, bin2)
        #cv2.imwrite("absolute_differences.png", diff_abs)

        #BINARIZAR MERGED image original
        #_, merged_color_original_bin = cv2.threshold(merged_color_original, 220, 255, cv2.THRESH_BINARY)
        #cv2.imwrite("absolute_differences_ORIGINAL.png", merged_color_original_bin)

        # 5) Operaciones morfológicas para limpiar ruido
        diff = cv2.dilate(diff_abs, self.kernel_erode, iterations=2)
        diff = cv2.erode(diff, self.kernel_erode, iterations=2)

        #hacer bitwise and de las dos imagenes
        print("Size of img1", bin1.shape)
        print("Size of img2", bin2.shape)
        merged_images = cv2.bitwise_and(bin1, bin2)
        #cv2.imwrite("merged_images.png", merged_images)
        #merged_inv = cv2.bitwise_not(merged_images)
        #cv2.imwrite("merged_images_inv.png", merged_inv)
        #merged_images GRAY TO BGR
        merged_color = cv2.cvtColor(merged_images, cv2.COLOR_GRAY2BGR)

        contours = []
        diff_coords = []

        # 6) Encontrar contornos significativos
        #if comparison_type == "insertions":
        contours, _ = cv2.findContours(diff, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        significant_contours = [c for c in contours if cv2.contourArea(c) >= self.min_contour_area]

        # 7) Extraer coordenadas de los contornos
        diff_coords = []
        for contour in significant_contours:
            for point in contour:
                x, y = point[0]
                diff_coords.append((x, y))

        # 4. Crear imagen en negro
        filtered_diff = np.full_like(bin1, 255)
        print("Shape of abs changes img",filtered_diff.shape)
        # 5. Dibujar contornos significativos en blanco
        cv2.drawContours(filtered_diff, significant_contours, -1, color=0, thickness=cv2.FILLED)

        # 6. Guardar o mostrar imagen final de diferencias -----------------------------------
        #cv2.imwrite('filtered_differences.png', filtered_diff)
        
        #invert image
        #inverted_img = cv2.bitwise_not(filtered_diff)
        #cv2.imwrite("inverted_filtered_differences.png", inverted_img)

        # Guardar máscara si quieres revisar
        diff_processed_bin1 = cv2.absdiff(merged_images, bin2)
        #cv2.imwrite("diff_for_bin1.png", diff_processed_bin1)
        #Encontrar contornos de la primera imagen
        diff_bin1 = cv2.dilate(diff_processed_bin1, self.kernel_erode, iterations=2)
        diff_bin1 = cv2.erode(diff_bin1, self.kernel_erode, iterations=2)
        #Save the differences from image 1
        #cv2.imwrite("diff_mask_green.png", diff_bin1)
        #invertir diferencias de la primera imagen
        #inverted_bin1 = cv2.bitwise_not(diff_bin1)
        #cv2.imwrite("diff_mask_green_inv.png", inverted_bin1)

        diff_processed_bin2 = cv2.absdiff(merged_images, bin1)
        #cv2.imwrite("diff_for_bin2.png", diff_processed_bin2)
        #Encontrar contornos de la primera imagen
        diff_bin2 = cv2.dilate(diff_processed_bin2, self.kernel_erode, iterations=2)
        diff_bin2 = cv2.erode(diff_bin2, self.kernel_erode, iterations=2)
        #Save the differences from image 2
        #cv2.imwrite("diff_mask_red.png", diff_bin2)
        #invertir diferencias de la primera imagen
        #inverted_bin2 = cv2.bitwise_not(diff_bin2)
        #cv2.imwrite("diff_mask_green_inv.png", inverted_bin2)
        
        #contornos de img1
        contours_bin1, _ = cv2.findContours(diff_bin1, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        significant_contours_bin1 = [c for c in contours_bin1 if cv2.contourArea(c) >= 1]

        #contornos de img2
        contours_bin2, _ = cv2.findContours(diff_bin2, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        significant_contours_bin2 = [c for c in contours_bin2 if cv2.contourArea(c) >= 1]

        print("Contours:", len(contours))
        print("Significant contours:", len(significant_contours))
        if len(significant_contours) > 100:
            return None,None, img1.shape
        
        #Dibujar contornos de la imagen 1
        filtered_bin1 = np.full_like(bin1, 255)
        cv2.drawContours(filtered_bin1, significant_contours_bin1, -1, color=0, thickness=cv2.FILLED)
        #cv2.imwrite('filtered_bin1.png', filtered_bin1)
        
        #Dibujar contornos de la imagen 2
        filtered_bin2 = np.full_like(bin1, 255)
        cv2.drawContours(filtered_bin2, significant_contours_bin2, -1, color=0, thickness=cv2.FILLED)
        #cv2.imwrite('filtered_bin2.png', filtered_bin2)

        # 8) --> INTEGRACIÓN NUEVA: resaltar con máscara en la imagen ORIGINAL EN COLOR
        # B) Verificar que diff_processed y img2_orig_color tengan misma forma base

        # Crear máscara boolean
        mask_img1_changes = filtered_bin1 == 0 #deleted changes
        mask_img2_changes = filtered_bin2 == 0 #added_changes

        # Crear máscara en color verde
        mask_color_green = np.zeros((filtered_diff.shape[0], filtered_diff.shape[1], 3), dtype=np.uint8)
        #if comparison_type == "insertions":
        mask_color_green[mask_img2_changes] = [25, 115, 26]
        
        rows, cols = mask_color_green.shape[:2]
        # Matriz de traslación: dx negativo mueve a la izquierda, dy negativo hacia arriba
        dx, dy = -2, -2  # píxeles a mover
        M = np.float32([[1, 0, dx], [0, 1, dy]])

        mask_color_green = cv2.warpAffine(mask_color_green, M, (cols, rows))

        # OPCIONAL: guarda para revisar
        #cv2.imwrite("mask_color_added.png", mask_color_green)
        # Combina con la imagen de cambios original con la mascara para verificar que coinciden
        #rgb_img2 = cv2.cvtColor(diff_processed_bin2, cv2.COLOR_GRAY2BGR)
        #print("Espacio de color",rgb_img2.shape)
        #highlighted_1 = cv2.addWeighted(merged_color, 1.0 , mask_color_green, 1.0, 0)
        #cv2.imwrite("mask_color_combined.png", highlighted_1)

        #highlighted_original1 = cv2.addWeighted(merged_color_original, 0.5, mask_color_green, 1.0, 0)
        #cv2.imwrite("mask_with_original.png", highlighted_original1)
        
        # A) Cargar de nuevo la imagen original en color (no la B/N)
        img2_orig_color = self.load_image(img2_input)
        if len(img2_orig_color.shape) == 2:
            img2_orig_color = cv2.cvtColor(img2_orig_color, cv2.COLOR_GRAY2BGR)

        if filtered_diff.shape[:2] != img2_orig_color.shape[:2]:
            print(f"Redimensionando diff_processed de {filtered_diff.shape} a {img2_orig_color.shape[:2]}")
            filtered_diff = cv2.resize(
                filtered_diff,
                (img2_orig_color.shape[1], img2_orig_color.shape[0]),
                interpolation=cv2.INTER_NEAREST
            )

        # Asegurar tamaños iguales
        if mask_color_green.shape != img2_orig_color.shape:
            print("No son del mismo tamano")
            mask_color_green = cv2.resize(
                mask_color_green,
                (img2_orig_color.shape[1], img2_orig_color.shape[0]),
                interpolation=cv2.INTER_NEAREST
            )
            print("Resize 2")
        else:
            print("Son del mismo tamano")

        # Combina con la imagen original usando addWeighted
        highlighted_2 = cv2.addWeighted(merged_color, 1.0 , mask_color_green, 1.0, 0)

        # Usa PIL para guardar con DPI
        im_pil = Image.fromarray(cv2.cvtColor(highlighted_2, cv2.COLOR_BGR2RGB))
        im_pil.save("highlighted_result_green.png", dpi=(300, 300))  # O el DPI que uses en tu PDF

        mask_color_red = np.zeros((filtered_diff.shape[0], filtered_diff.shape[1], 3), dtype=np.uint8)
        mask_color_red[mask_img1_changes] = [12, 12, 173]
        
        rows, cols = mask_color_red.shape[:2]
        mask_color_red = cv2.warpAffine(mask_color_red, M, (cols, rows))

        cv2.imwrite("mask_color_deleted.png", mask_color_red)
        # A) Cargar de nuevo la imagen original en color (no la B/N)
        img1_orig_color = self.load_image(img1_input)
        if len(img1_orig_color.shape) == 2:
            img1_orig_color = cv2.cvtColor(img1_orig_color, cv2.COLOR_GRAY2BGR)

        if filtered_diff.shape[:2] != img1_orig_color.shape[:2]:
            print(f"Redimensionando diff_processed de {filtered_diff.shape} a {img1_orig_color.shape[:2]}")
            filtered_diff = cv2.resize(
                filtered_diff,
                (img1_orig_color.shape[1], img1_orig_color.shape[0]),
                interpolation=cv2.INTER_NEAREST
            )

        # Asegurar tamaños iguales
        if mask_color_red.shape != img1_orig_color.shape:
            print("No son del mismo tamano")
            mask_color_red = cv2.resize(
                mask_color_red,
                (img1_orig_color.shape[1], img1_orig_color.shape[0]),
                interpolation=cv2.INTER_NEAREST
            )
        else:
            print("Son del mismo tamano")
        
        # Combina con la imagen original usando addWeighted
        highlighted_final = cv2.addWeighted(highlighted_2, 1.0, mask_color_red, 1.0, 0)
        #highlighted_final_processed = cv2.erode(highlighted_final, self.kernel_erode, iterations=1)
        #highlighted_final = cv2.dilate(highlighted_final, self.kernel_erode, iterations=1)

        # Usa PIL para guardar con DPI
        im_pil = Image.fromarray(cv2.cvtColor(highlighted_final, cv2.COLOR_BGR2RGB))
        im_pil.save("highlighted_result_red.png", dpi=(300, 300))  # O el DPI que uses en tu PDF

        # 9) Devuelve coordenadas de diferencias + imagen resaltada + tamaño
        return diff_coords, highlighted_final, img1.shape