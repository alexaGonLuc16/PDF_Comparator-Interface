# main.py
import os
import sys
import fitz
import cv2
import img2pdf
from PyQt5.QtWidgets import QApplication
import argparse
from src.ui.main_window import MainWindow
from src.pdf_processor import PDFProcessor
from src.image_comparator import ImageComparator
from src.circle_detector import CircleDetector
from src.pdf_annotator import PDFAnnotator

print("Iniciando app...")

#establecer el directorio de trabajo de la carpeta del script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESTART_CODE = 1001  # Código especial para reinicio
os.chdir(BASE_DIR)

# Crear directorios necesarios
TEMP_DIR = os.path.join(BASE_DIR, 'data', 'temp')
OUTPUT_DIR = os.path.join(BASE_DIR, 'data', 'output')
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Asegurarse de que src esté en el path
sys.path.append(BASE_DIR)
print(f"Path actualizado: {sys.path}")

# Intentar importar los módulos necesarios
print("Importando módulos...")
try:
    from src.ui.main_window import MainWindow
    from src.pdf_processor import PDFProcessor
    from src.image_comparator import ImageComparator
    from src.circle_detector import CircleDetector
    from src.pdf_annotator import PDFAnnotator
    print("Módulos importados correctamente")
except Exception as e:
    print(f"Error al importar módulos: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

def process_command_line():
    print("EJECUTANDO FUNCIOOOOON")
    """Procesa los PDFs desde la línea de comandos"""
    parser = argparse.ArgumentParser(description='Herramienta para comparar y destacar diferencias entre dos PDFs')
    parser.add_argument('data\input\original.pdf', help='Ruta al PDF original')
    parser.add_argument('data\input\modified.pdf', help='Ruta al PDF modificado')
    parser.add_argument('--output', '-o', help='Ruta para guardar el PDF anotado')
    parser.add_argument('--dpi', type=int, default=300, help='DPI para la conversión a imágenes')
    parser.add_argument('--threshold', type=int, default=10, help='Umbral para detectar diferencias (0-255)')
    parser.add_argument('--eps', type=float, default=15, help='Parámetro eps para DBSCAN')
    parser.add_argument('--min-samples', type=int, default=5, help='Parámetro min_samples para DBSCAN')
    args = parser.parse_args()
    
    # Inicializar componentes
    pdf_processor = PDFProcessor(TEMP_DIR)
    image_comparator = ImageComparator(threshold=args.threshold)
    circle_detector = CircleDetector(eps=args.eps, min_samples=args.min_samples)
    pdf_annotator = PDFAnnotator(OUTPUT_DIR)
    
    # Paso 1: Convertir PDFs a imágenes
    print(f"Convirtiendo PDFs a imágenes (DPI: {args.dpi})...")
    images1 = pdf_processor.pdf_to_images(args.pdf1, dpi=args.dpi)
    images2 = pdf_processor.pdf_to_images(args.pdf2, dpi=args.dpi)
    
    # Paso 2 y 3: Comparar imágenes y obtener diferencias
    print("Comparando imágenes y encontrando diferencias...")
    circles_by_page = {}
    
    #---
    output_pdf_path = os.path.join(OUTPUT_DIR, f"processed_{os.path.basename(args.pdf2)}")
    # Abrir el PDF una sola vez fuera del bucle
    #---
    doc = fitz.open(args.pdf2)

    for i, (img1, img2) in enumerate(zip(images1, images2)):
        print(f"Procesando página {i+1}/{len(images1)}...")
        
        # Comparar imágenes y obtener coordenadas de diferencias
        diff_coords, processed_img, _ = image_comparator.find_differences(img1, img2)
        
        # --- Guardar processed_img ---
        processed_img_path = os.path.join(TEMP_DIR, f"page_{i+1}_processed.png")
        cv2.imwrite(processed_img_path, processed_img)

            # --- Convertir a PDF ---
        processed_pdf_path = os.path.join(TEMP_DIR, f"page_{i+1}_processed.pdf")
        with open(processed_pdf_path, "wb") as f:
            f.write(img2pdf.convert(processed_img_path))

        # --- Reemplazar página ---
        replacement = fitz.open(processed_pdf_path)
        doc[i] = replacement[0]  # Sustituye la página i con la nueva
        replacement.close()

        # Paso 4: Agrupar diferencias en círculos
        if diff_coords:
            circles = circle_detector.group_points_into_circles(diff_coords)
            circles = circle_detector.merge_overlapping_circles(circles)
            
            if circles:
                circles_by_page[str(i)] = circles
    
    # Guardar PDF final reemplazado
    doc.save(output_pdf_path)
    print("-----------------------------------------------------------------------------------------------------------outputdir!!!!!!!!!!!!!!!!!!!!!!!!!!!!",output_pdf_path)
    doc.close()

    # Paso 5: Anotar el PDF con círculos
    print("Añadiendo anotaciones al PDF...")
    output_pdf_path = args.output if args.output else os.path.join(OUTPUT_DIR, f"annotated_{os.path.basename(args.pdf2)}")
    pdf_annotator.add_circle_annotations(args.pdf2, circles_by_page, output_pdf_path, dpi=args.dpi)
    
    # Guardar información de círculos para posible uso posterior
    pdf_annotator.save_changes_to_json(pdf_annotator.input_pdf ,circles_by_page)
    
    print(f"Proceso completado. PDF anotado guardado en: {output_pdf_path}")
    return output_pdf_path

if __name__ == "__main__":
    while True:
        # Limpiar directorio temporal (tu código existente)
        try:
            temp_dir = os.path.join(BASE_DIR, 'data', 'temp')
            print(f"Limpiando directorio temporal al inicio: {temp_dir}")
            
            for filename in os.listdir(temp_dir):
                if filename.endswith('.jpg'):
                    file_path = os.path.join(temp_dir, filename)
                    try:
                        os.remove(file_path)
                        print(f"Borrada imagen temporal anterior: {filename}")
                    except Exception as e:
                        print(f"Error al borrar {filename}: {e}")
        except Exception as e:
            print(f"Error durante la limpieza inicial: {e}")
        
        # Crear aplicación
        app = QApplication(sys.argv)
        
        try:
            window = MainWindow()
            window.show()
        except Exception as e:
            print(f"Error al crear/mostrar ventana: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        exit_code = app.exec_()
        
        if exit_code != RESTART_CODE:
            # Salir normalmente
            sys.exit(exit_code)
        
        # Si llegamos aquí, es un reinicio
        print("Reiniciando aplicación...")
        del app  # Limpiar la aplicación anterior

    # Verificar si se proporcionaron argumentos
    #if len(sys.argv) > 1:
        # Modo línea de comandos
        #process_command_line()
        #process_command_line(selected_pages)
    #else:
        # Limpiar directorio temporal antes de iniciar la aplicación
        #try:
            #temp_dir = os.path.join(BASE_DIR, 'data', 'temp')
            #print(f"Limpiando directorio temporal al inicio: {temp_dir}")
            
            #for filename in os.listdir(temp_dir):
                #if filename.endswith('.jpg'):
                    #file_path = os.path.join(temp_dir, filename)
                    #try:
                        #os.remove(file_path)
                        #print(f"Borrada imagen temporal anterior: {filename}")
                    #except Exception as e:
                        #print(f"Error al borrar {filename}: {e}")
        #except Exception as e:
            #print(f"Error durante la limpieza inicial: {e}")
        
        # Modo interfaz gráfica
        #print("Creando aplicación Qt...")
        #app = QApplication(sys.argv)
        
        #print("Creando ventana principal...")

        #try:
            #window = MainWindow()
            #print("Ventana principal creada")
            #window.show()
            #print("Ventana mostrada")
        #except Exception as e:
            #print(f"Error al crear/mostrar ventana: {e}")
            #import traceback
            #traceback.print_exc()
            #sys.exit(1)
        
        #print("Iniciando bucle de eventos...")
        #sys.exit(app.exec_())


