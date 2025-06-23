import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QFileDialog, QLabel, QCheckBox,
                            QProgressBar, QSpinBox, QGroupBox, QRadioButton,QLineEdit,QButtonGroup, QMenu, QToolBar, QAction, QMessageBox, QTabWidget, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from src.pdf_rotation import PDFRotationUIHandler, RotationDialog

import fitz  # PyMuPDF - importante para la función toggle_circle_visibility

from src.json_loader_ui import JsonLoaderUI
from src.pdf_processor import PDFProcessor
from src.image_comparator import ImageComparator
from src.circle_detector import CircleDetector
from src.pdf_annotator import PDFAnnotator
from src.ui.pdf_viewer import PDFViewer, ChangesListWidget
# Importar componentes de la aplicación

RESTART_CODE = 1001  # Código especial para reinicio

class WorkerThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str, dict)
    
    def __init__(self, pdf1, pdf2, output_path, dpi, threshold, eps, min_samples, selected_pages = None):
        super().__init__()
        self.pdf1 = pdf1
        self.pdf2 = pdf2
        self.output_path = output_path
        self.dpi = dpi
        self.threshold = threshold
        self.eps = eps
        self.min_samples = min_samples
        self.selected_pages = selected_pages
        self.updated_annotations = {}

    def run(self):
        # Inicializar componentes
        # Usar rutas absolutas para los directorios
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        temp_dir = os.path.join(base_dir, 'data', 'temp')
        output_dir = os.path.join(base_dir, 'data', 'output')
        
        pdf_processor = PDFProcessor()
        image_comparator = ImageComparator(threshold=self.threshold)
        circle_detector = CircleDetector(eps=self.eps, min_samples=self.min_samples)
        pdf_annotator = PDFAnnotator(output_dir)

        source_pdf1 = self.pdf1
        source_pdf2 = self.pdf2

        # Paso 2: Convertir PDFs a imágenes (solo páginas seleccionadas)
        self.progress.emit(20)
        images1 = pdf_processor.pdf_to_images(source_pdf1, dpi=self.dpi, selected_pages=self.selected_pages)
        self.progress.emit(35)
        images2 = pdf_processor.pdf_to_images(source_pdf2, dpi=self.dpi, selected_pages=self.selected_pages)
        self.progress.emit(50)
        
        # El resto del código sigue igual...
        # Paso 3: Comparar imágenes y obtener diferencias
        circles_by_page = {}
        
        total_pages = min(len(images1), len(images2))
        for i, (img1, img2) in enumerate(zip(images1, images2)):
            # Comparar imágenes y obtener coordenadas de diferencias
            diff_coords,_, image_dim  = image_comparator.find_differences(img1, img2)
            global page_height 
            global page_width

            page_height = image_dim[0]
            page_width = image_dim[1]

            # Paso 4: Agrupar diferencias en círculos
            if diff_coords:
                circles = circle_detector.group_points_into_circles(diff_coords)
                circles = circle_detector.merge_overlapping_circles(circles)
                
                
                if circles:
                    if self.selected_pages != None:
                        circles_by_page[self.selected_pages[i]] = circles
                    else:
                        circles_by_page[i] = circles

            # Actualizar progreso
            progress = 50 + int((i + 1) / total_pages * 40)
            self.progress.emit(progress)
        
        # Paso 5: Anotar el PDF con círculos
        # Usar el PDF2 reparado si está disponible
        pdf_annotator.add_circle_annotations(source_pdf2, circles_by_page, self.output_path, dpi=self.dpi)
        
        # Guardar información de círculos para uso en la UI
        pdf_annotator.save_changes_to_json(self.pdf1, circles_by_page)
        
        self.progress.emit(100)
        self.finished.emit(self.output_path, circles_by_page)
        #habilitar click event para descarte de circulos

class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("PDF Comparator")
        self.setGeometry(100, 100, 1200, 800)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        
        # Pestañas principales
        self.tabs = QTabWidget()
        
        # Pestaña de carga/guardado JSON
        #self.json_tab = QWidget()
        self.setup_json_tab()
        #self.tabs.addTab(self.json_tab, "Cargar/Guardar Cambios")

        # Pestaña de comparación
        self.comparison_tab = QWidget()
        self.setup_comparison_tab()
        self.tabs.addTab(self.comparison_tab, "Comparar PDFs")
        
        # Agregar pestañas al layout principal
        main_layout.addWidget(self.tabs)
        # Conectar la señal de reinicio
        self.annotated_viewer.restart_signal.connect(self.handle_restart)
    
    def handle_restart(self):
        """Maneja la solicitud de reinicio, preguntando por guardar cambios"""
        # Verificar si hay cambios no guardados
        if self.annotated_viewer.document_modified or self.original_viewer.document_modified:
            reply = QMessageBox.question(
                self, 'Guardar cambios',
                '¿Deseas guardar los cambios antes de reiniciar?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                return  # Cancelar el reinicio
            elif reply == QMessageBox.StandardButton.Yes:
                if self.annotated_viewer.document_modified:
                    self.rotation_handler.save_document()  
                else:
                    self.rotation_original.save_document()  

        # Reiniciar la aplicación
        self.restart_application()
    
    def restart_application(self):
        """Reinicia completamente la aplicación"""
        QApplication.exit(RESTART_CODE)  # Definiremos RESTART_CODE más abajo
    
    def setup_comparison_tab(self):
        self.main_layout = QVBoxLayout(self.comparison_tab)
        
        #Crear un widget contenedor para la configuracion
        self.config_container = QWidget()
        # Área de configuración
        self.config_layout = QHBoxLayout()
        
        # Selección de archivos
        file_group = QGroupBox("Choose the files")
        file_layout = QVBoxLayout(file_group)
        
        # PDF original
        pdf1_layout = QHBoxLayout()
        self.pdf1_label = QLabel("Original PDF:")

        self.pdf1_path = QLabel("not selected")
        self.pdf1_button = QPushButton("Upload file")
        self.pdf1_button.clicked.connect(self.select_pdf1)
        
        pdf1_layout.addWidget(self.pdf1_label)
        pdf1_layout.addWidget(self.pdf1_path)
        pdf1_layout.addWidget(self.pdf1_button)
        
        # PDF modificado
        pdf2_layout = QHBoxLayout()
        self.pdf2_label = QLabel("Modified version:")
        self.pdf2_path = QLabel("not selected")
        self.pdf1_button = QPushButton("Upload file")
        self.pdf1_button.clicked.connect(self.select_pdf1)
        self.pdf2_button = QPushButton("Upload PDF")
        self.pdf2_button.clicked.connect(self.select_pdf2)

        self.json_button = QPushButton("Upload JSON")
        self.json_button.clicked.connect(self.load_json_file)
        
        pdf2_layout.addWidget(self.pdf2_label)
        pdf2_layout.addWidget(self.pdf2_path)
        pdf2_layout.addWidget(self.pdf2_button)
        pdf2_layout.addWidget(self.json_button)
        
        # Guardar como
        save_layout = QHBoxLayout()
        self.save_label = QLabel("Save as:")
        self.save_path = QLabel("not selected")
        self.save_button = QPushButton("Upload file")
        self.save_button.clicked.connect(self.select_save_path)
        
        save_layout.addWidget(self.save_label)
        save_layout.addWidget(self.save_path)
        save_layout.addWidget(self.save_button)
        
        file_layout.addLayout(pdf1_layout)
        file_layout.addLayout(pdf2_layout)
        file_layout.addLayout(save_layout)
        
        # Parámetros
        param_group = QGroupBox("Parameters")
        param_layout = QVBoxLayout(param_group)
        
        # DPI
        dpi_layout = QHBoxLayout()
        dpi_layout.addWidget(QLabel("DPI:"))
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(300)
        dpi_layout.addWidget(self.dpi_spin)
        
        # Umbral
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Threshold:"))
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(1, 50)
        self.threshold_spin.setValue(10)
        threshold_layout.addWidget(self.threshold_spin)
        
        # Epsilon
        eps_layout = QHBoxLayout()
        eps_layout.addWidget(QLabel("Epsilon:"))
        self.eps_spin = QSpinBox()
        self.eps_spin.setRange(1, 100)
        self.eps_spin.setValue(15)
        eps_layout.addWidget(self.eps_spin)
        
        # Min Samples
        min_samples_layout = QHBoxLayout()
        min_samples_layout.addWidget(QLabel("Min Samples:"))
        self.min_samples_spin = QSpinBox()
        self.min_samples_spin.setRange(1, 50)
        self.min_samples_spin.setValue(5)
        min_samples_layout.addWidget(self.min_samples_spin)
        
        param_layout.addLayout(dpi_layout)
        param_layout.addLayout(threshold_layout)
        param_layout.addLayout(eps_layout)
        param_layout.addLayout(min_samples_layout)
        
        page_select_layout = QHBoxLayout()
        page_select_layout.addWidget(QLabel("Pages to compare:"))

        self.all_pages_radio = QRadioButton("All")
        self.all_pages_radio.setChecked(True)
        self.specific_pages_radio = QRadioButton("Specific Pages")
        self.specific_pages_input = QLineEdit()
        self.specific_pages_input.setPlaceholderText("Ex: 1-5,8,10-12")
        self.specific_pages_input.setEnabled(False)

        page_select_group = QButtonGroup(self)
        page_select_group.addButton(self.all_pages_radio)
        page_select_group.addButton(self.specific_pages_radio)

        self.all_pages_radio.toggled.connect(self.toggle_pages_input)
        self.specific_pages_radio.toggled.connect(self.toggle_pages_input)

        page_select_layout.addWidget(self.all_pages_radio)
        page_select_layout.addWidget(self.specific_pages_radio)
        page_select_layout.addWidget(self.specific_pages_input)

        param_layout.addLayout(page_select_layout)

        # Botones de acción
        action_group = QGroupBox("Actions")
        action_layout = QVBoxLayout(action_group)
        
        self.compare_button = QPushButton("Compare PDFs")
        self.compare_button.clicked.connect(self.start_comparison)
        self.compare_button.setEnabled(False)

        self.apply_json_button = QPushButton("Apply JSON annotations")
        self.apply_json_button.clicked.connect(self.json_loader_ui.apply_changes)
        self.apply_json_button.setEnabled(False)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        
        action_layout.addWidget(self.apply_json_button)
        action_layout.addWidget(self.compare_button)
        action_layout.addWidget(self.progress_bar)
        
        self.config_layout.addWidget(file_group, 3)
        self.config_layout.addWidget(param_group, 2)
        self.config_layout.addWidget(action_group, 1)

        #anadir contenedor al layout principal
        self.main_layout.addWidget(self.config_container)
        
        # Área de visualización
        self.view_layout = QHBoxLayout()
        # Visor original (izquierda)
        self.original_viewer = PDFViewer("Original PDF")

        # Visor anotado (derecha)
        self.annotated_viewer = PDFViewer("Annotated PDF")
        self.rotation_handler = PDFRotationUIHandler(self, self.annotated_viewer, title = "Annotated PDF")
        self.annotated_viewer.document_modified = False

        self.rotation_original = PDFRotationUIHandler(self, self.original_viewer, self.rotation_handler, title = "Original PDF")
        self.original_viewer.document_modified = False
         
        # Contenedor del visor anotado con el checkbox de círculos
        self.annotated_container = QWidget()
        self.annotated_layout = QVBoxLayout(self.annotated_container)
        self.annotated_layout.setContentsMargins(0, 0, 0, 0)
        
        self.annotated_layout.addWidget(self.annotated_viewer)
        
        self.toggle_circles = QCheckBox("Show circles")
        self.toggle_circles.setChecked(True)
        self.toggle_circles.stateChanged.connect(self.toggle_circle_visibility)

        self.toggle_side_by_side = QCheckBox("Side by side view")
        self.toggle_side_by_side.setChecked(False) #por defecto desactivado
        self.toggle_side_by_side.stateChanged.connect(self.toggle_side_by_side_mode)

        self.rotate_both_pdfs = QCheckBox("Rotate both pdfs")
        self.rotate_both_pdfs.setChecked(False) #por defecto desactivado
        self.rotate_both_pdfs.stateChanged.connect(self.rotate_both)

        # Añadir el checkbox al layout después de toggle_circles
        checkbox_layout = QHBoxLayout()
        checkbox_layout.addWidget(self.toggle_circles)
        checkbox_layout.addWidget(self.toggle_side_by_side)
        checkbox_layout.addWidget(self.rotate_both_pdfs)
        self.annotated_layout.addLayout(checkbox_layout)

        # Contenedor para la lista de cambios (derecha)
        self.changes_container = QWidget()
        changes_layout = QVBoxLayout(self.changes_container)
        changes_layout.setContentsMargins(5, 5, 5, 5)
        
        # Título de la lista de cambios
        changes_title = QLabel("Detected Changes")
        changes_title.setAlignment(Qt.AlignCenter)
        changes_title.setStyleSheet("font-size: 11pt; font-weight: bold;")
        
        changes_layout.addWidget(changes_title)

        #anadir solo el visor anotado por defecto
        # Configurar la vista
        self.view_layout.addWidget(self.annotated_container,5)  # PDF visor ocupa 5/6 de la pantalla
        self.view_layout.addWidget(self.changes_container, 1)  # Lista de cambios ocupa 1/6 de la pantalla
        
        # Añadir layouts al layout principal
        self.main_layout.addLayout(self.config_layout, 1)
        self.main_layout.addLayout(self.view_layout, 4)
        
        # Variables de estado
        self.pdf1_file = None
        self.pdf2_file = None
        self.output_file = None
        self.circles_by_page = {}
        self.side_by_side_mode = False

        # Flag para habilitar circle_click event
        self.circle_clicked_flag = False
        self.annotated_viewer.circle_clicked.connect(self.handle_circle_click)
        self.annotated_viewer.update_annotations.connect(self.update_annotations)
        self.annotated_viewer.set_clicks_enabled(False)  # inicialmente deshabilitado
        
        #connect signal to update circle changes
        self.rotation_handler.save_doc_signal.connect(self.update_annotations_by_page_json)
        self.rotation_original.save_doc_signal.connect(self.update_annotations_by_page_json)
        self.json_loader_ui.add_changes_list.connect(self.comparison_finished)

        print("UI de MainWindow inicializada")
        
    def update_annotations_by_page_json(self, signal_update):
        #hacer copia de los circulos identificados para el json 
        if signal_update:
            self.rotation_handler.rotator.changes_by_page = self.annotated_viewer.formatted_circles_by_page
            self.rotation_handler.rotator.highlights_by_page = self.annotated_viewer.highlights_by_page
            self.rotation_handler.rotator.watermarks_by_page = self.annotated_viewer.watermarks_by_page

            print("Hihglights by page", self.rotation_handler.rotator.highlights_by_page)
            print("Watermarks by page", self.rotation_handler.rotator.watermarks_by_page)

    def setup_json_tab(self):
        """Configura la pestaña de carga/guardado de JSON."""
        
        # Panel izquierdo: Visor de PDF
        self.json_pdf_viewer = PDFViewer("Annotated PDF")
        
        # Panel derecho: Controles de JSON
        json_control_widget = QWidget()
        self.json_loader_ui = JsonLoaderUI(self.json_pdf_viewer)
        
        #actualizar cambios en formatted circles by page
        self.json_loader_ui.json_loader.extracted_changes_signal.connect(self.update_extracted_circles)
        self.json_loader_ui.update_changes_list_signal.connect(self.update_extracted_circles)
        
        # Configurar layout para el panel de control
        json_control_layout = QVBoxLayout(json_control_widget)
    
    def load_pdf_for_comparison(self, pdf1_path, pdf2_path):
        """Carga dos PDFs para comparación."""
        # Cargar PDFs en los visores
        self.original_viewer.load_pdf(pdf1_path)
        self.annotated_viewer.load_pdf(pdf2_path)
        
        # Cambiar a la pestaña de comparación
        self.tabs.setCurrentIndex(0)
    
    def load_pdf_with_json(self, pdf_path, json_path):
        """Carga un PDF con sus cambios desde un archivo JSON."""
        # Esta función podría ser llamada desde fuera de la clase
        self.json_loader_ui.pdf_path = pdf_path
        self.json_loader_ui.json_path = json_path
        self.json_loader_ui.update_load_status()
        self.json_loader_ui.apply_changes()
        
        # Cambiar a la pestaña de JSON
        self.tabs.setCurrentIndex(1)

    def on_document_modified(self, doc_modified = ""):
        if doc_modified == "Original PDF":
            self.original_viewer.document_modified = True
        else:
            self.annotated_viewer.document_modified = True
        # Actualizar título o interfaz para reflejar los cambios
        self.update_ui_for_unsaved_changes()

    def update_ui_for_unsaved_changes(self):
        """
        Actualiza la interfaz de usuario para indicar que hay cambios sin guardar.
        """
        # 1. Actualizar el título de la ventana añadiendo un asterisco
        import os
        filename = "Modificado"
        self.setWindowTitle(f"PDF Comparator - {filename} *")
        
        # 2. Habilitar el botón/acción de guardar (si existe)
        if hasattr(self, 'save_action'):
            self.save_action.setEnabled(True)
        
        # 3. Opcional: Cambiar el color o estado de algún indicador visual
        if hasattr(self, 'status_label'):
            self.status_label.setText("Documento modificado - Cambios sin guardar")
            
        # 4. Establecer una variable interna para preguntar al cerrar
        self.document_modified = True

    def handle_circle_click(self, page_num, clicked_circle, new_state):
        """Maneja clics en círculos para actualizar anotaciones."""
        print(f"Círculo clickeado en página {page_num}: {clicked_circle}")
        
        # Modificación del círculo si es necesario o actualización (self.updated_annotations --> list of changes in the page)
        self.updated_annotations = self.annotated_viewer.modify_annotations(page_num, clicked_circle, new_state)
        
        # Llamar a update_annotations para reflejar cambios
        self.update_annotations(page_num, self.updated_annotations)
    
    def update_extracted_circles(self, changes_by_page): 
        self.annotated_viewer.formatted_circles_by_page = changes_by_page
        #reflejar cambios en el changes list widget
        self.annotated_viewer.changes_list_widget.update_changes_list(self.annotated_viewer.formatted_circles_by_page)
  
    def update_annotations(self, page_num, new_annotations, dpi=300):
        """Actualiza las anotaciones del PDF según las modificaciones del usuario."""
        if not hasattr(self.annotated_viewer, 'document') or not self.annotated_viewer.document:
            print("No hay un documento cargado en annotated_viewer.")
            return

        try:
            page = self.annotated_viewer.document[page_num]
            print("Si, page num")
            # Factor de escala para convertir de coordenadas de imagen a PDF
            scale_factor = 72 / dpi
            # Eliminar anotaciones previas de tipo "Circle"
            annot = page.first_annot
            while annot:
                next_annot = annot.next  # Guardar referencia antes de eliminar
                if annot.type[1] == 'Circle':
                    page.delete_annot(annot)  # Método correcto para eliminar anotaciones
                annot = next_annot  # Pasar al siguiente
            
            #for circle, annotations in new_annotations.items():
            for circle in new_annotations:
                if circle['selected'] == False:
                    continue
                else:
                    x_pdf = circle['x'] * scale_factor
                    y_pdf = circle['y'] * scale_factor
                    radius_pdf = circle['radius'] * scale_factor

                    # Crear anotación de círculo
                    circle_annot = page.add_circle_annot(
                        (x_pdf - radius_pdf, y_pdf - radius_pdf, x_pdf + radius_pdf, y_pdf + radius_pdf)
                    )
                    # Configurar propiedades
                    circle_annot.set_border(width=2)
                    circle_annot.set_colors(stroke=(0, 0, 1))  # Azul
                    circle_annot.update(opacity=0.7)

            # Refrescar visor para mostrar actualizaciones
            self.annotated_viewer.reload_page()

        except Exception as e:
            print(f"Error al actualizar anotaciones: {e}")


    def clean_temp_directory(self):
        """Limpia el directorio temporal al inicio de la aplicación"""
        try:
            # Obtener la ruta del directorio temporal
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            temp_dir = os.path.join(base_dir, 'data', 'temp')
            
            print(f"Limpiando directorio temporal al inicio: {temp_dir}")
            
            # Borrar todas las imágenes JPG en el directorio temporal
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

    def rotate_both(self, state):
        """Actualiza el estado de rotación conjunta y controla la visibilidad de los botones."""
        is_checked = (state == Qt.Checked)
        
        # Actualizar el estado en los manejadores de rotación
        if hasattr(self, 'rotation_original') and self.rotation_original:
            self.rotation_original.rotate_both = is_checked
            
            # Mostrar u ocultar el botón del PDF original según el estado
            if hasattr(self.rotation_original, 'rotate_action'):
                self.rotation_original.rotate_action.setVisible(not is_checked)
            
        if hasattr(self, 'rotation_handler') and self.rotation_handler:
            self.rotation_handler.rotate_both = is_checked
            
            # Ocultar o mostrar el botón de rotación del PDF anotado
            if hasattr(self.rotation_handler, 'rotate_action'):
                self.rotation_handler.rotate_action.setVisible(not is_checked)
        
        # Crear o mostrar el botón de "Rotar ambos PDFs" si está activado el checkbox
        if is_checked:
            # Si ya existe el botón de rotar ambos, solo mostrarlo
            if hasattr(self, 'rotate_both_action'):
                self.rotate_both_action.setVisible(True)
            else:
                # Crear el botón de rotación para ambos PDFs
                print("Creando accion")
                self.rotate_both_action = QAction(QIcon("C:/PDF_Comparator/src/ui/icons/rotate.png"), "Rotar ambos PDFs", self)
                self.rotate_both_action.setStatusTip("Rotar ambos PDFs simultáneamente")
                self.rotate_both_action.triggered.connect(self.show_both_rotation_dialog)
                
                # Añadir a la barra de herramientas
                toolbar = self.findChild(QToolBar)
                toolbar = self.addToolBar("Principal")
                if toolbar:
                    toolbar.addAction(self.rotate_both_action)
        else:
            # Ocultar el botón de rotar ambos si existe
            if hasattr(self, 'rotate_both_action'):
                self.rotate_both_action.setVisible(False)
        
        # Actualizar la geometría de la barra de herramientas
        toolbar = self.findChild(QToolBar)
        if toolbar:
            toolbar.updateGeometry()
        
        print(f"Estado de rotación conjunta: {'Activado' if is_checked else 'Desactivado'}")

    def show_both_rotation_dialog(self):
        """Muestra el diálogo para rotar ambos PDFs."""
        # Verificar que ambos visores estén disponibles
        if (not hasattr(self, 'original_viewer') or not self.original_viewer or 
            not hasattr(self, 'annotated_viewer') or not self.annotated_viewer):
            print("Error: No se encuentran los visores de PDF")
            return
        
        # Verificar que ambos documentos estén cargados
        if (not self.original_viewer.document or not self.annotated_viewer.document):
            QMessageBox.warning(
                self,
                "Advertencia",
                "Debes abrir ambos documentos PDF primero."
            )
            return
        
        dialog = RotationDialog(self, "Rotar ambos PDFs")
        dialog.info_label.setText("Selecciona la rotación para ambos PDFs:")
        
        if dialog.exec_():
            degrees, scope = dialog.get_rotation_params()
            
            # Aplicar la rotación a ambos PDFs
            rotated_original = False
            rotated_annotated = False
            
            # Rotar PDF original
            if scope == "current":
                current_page = self.original_viewer.current_page
                rotated_original = self.rotation_original.rotator.rotate_page(current_page, degrees)
            else:  # scope == "all"
                rotated_original = self.rotation_original.rotator.rotate_all_pages(degrees)
            
            # Rotar PDF anotado
            if scope == "current":
                current_page = self.annotated_viewer.current_page
                rotated_annotated = self.rotation_handler.rotator.rotate_page(current_page, degrees)
            else:  # scope == "all"
                rotated_annotated = self.rotation_handler.rotator.rotate_all_pages(degrees)
            
            # Actualizar visualización
            if rotated_original:
                self.original_viewer.render_current_page()
            
            if rotated_annotated:
                self.annotated_viewer.render_current_page()
            
            # Mostrar mensaje de resultado
            if rotated_original or rotated_annotated:
                QMessageBox.information(
                    self,
                    "Rotación aplicada",
                    f"La rotación de {degrees}° se aplicó correctamente a los PDFs.\n\n"
                    "Recuerda guardar los cambios con el botón 'Guardar cambios'."
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se pudo aplicar la rotación a los documentos."
                )


    def toggle_side_by_side_mode(self, state):
        """Cambia entre modo de un solo visor y dos visores lado a lado."""
        is_side_by_side = (state == Qt.Checked)
        
        if is_side_by_side == self.side_by_side_mode:
            return  # No hay cambio
        
        self.side_by_side_mode = is_side_by_side
        
        # Obtener el layout donde están los visores
        #view_layout = None
        '''for i in range(self.centralWidget().layout().count()):
            item = self.centralWidget().layout().itemAt(i)
            if isinstance(item, QHBoxLayout) and item.count() > 0:
                view_layout = item
                break
        '''
        if not self.view_layout:
            return
        
        # Limpiar el layout
        while self.view_layout.count():
            item = self.view_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
        
        # Recrear layout según el modo
        if is_side_by_side:
            # En modo lado a lado, mostrar ambos visores
            self.view_layout.addWidget(self.original_viewer, 4)
            self.view_layout.addWidget(self.annotated_container, 4)
            self.view_layout.addWidget(self.changes_container, 1)  # Lista de cambios ocupa 1/6 de la pantalla
            
            # Cargar el PDF original si no está cargado
            if self.pdf1_file and not self.original_viewer.document:
                self.original_viewer.load_pdf(self.pdf1_file)
                # Sincronizar la página actual
                self.original_viewer.current_page = self.annotated_viewer.current_page
                self.original_viewer.render_current_page()
            
            # Sincronizar navegación
            self.sync_page_navigation()
        else:
            # En modo normal, mostrar solo el visor anotado
            self.view_layout.addWidget(self.annotated_container,5)
            self.view_layout.addWidget(self.changes_container, 1)  # Lista de cambios ocupa 1/6 de la pantalla

        # Añadir layouts al layout principal
        self.main_layout.addLayout(self.view_layout)
        
        # Mostrar widgets
        for i in range(self.view_layout.count()):
            item = self.view_layout.itemAt(i)
            if item.widget():
                item.widget().show()

    #metodo de alternancia para el campo de texto
    def toggle_pages_input(self, checked):
        self.specific_pages_input.setEnabled(self.specific_pages_radio.isChecked())
        
    #método para analizar la selección de páginas
    def parse_page_selection(self, selection_str):
        """
        Convierte una cadena como "1-5,8,10-12" en una lista de números de página [1,2,3,4,5,8,10,11,12]
        """
        pages = []
        
        if not selection_str.strip():
            return None  # Cadena vacía significa todas las páginas
        
        parts = selection_str.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                # Rango de páginas (ej: 1-5)
                start, end = part.split('-')
                try:
                    start_page = int(start.strip())
                    end_page = int(end.strip())
                    if start_page < 1 or end_page < start_page:
                        raise ValueError("Rango de páginas inválido")
                    pages.extend(range(start_page, end_page + 1))
                except ValueError:
                    raise ValueError(f"Rango inválido: {part}")
            else:
                # Página individual
                try:
                    page = int(part)
                    if page < 1:
                        raise ValueError("El número de página debe ser positivo")
                    pages.append(page)
                except ValueError:
                    raise ValueError(f"Número de página inválido: {part}")
        
        # Convertir a índices base-0 para uso interno
        return [p - 1 for p in pages]  # Restar 1 porque las páginas se indexan desde 0 internamente

    def select_pdf1(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar PDF Original", "", "PDF Files (*.pdf)")
        if file_path:
            self.pdf1_file = file_path
            self.pdf1_path.setText(os.path.basename(file_path))
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(base_dir, 'data', 'output')
            self.original_viewer.load_pdf(file_path)
            self.update_compare_button()
            self.update_apply_json_button()
            self.rotation_original.file_path = file_path
    
    def select_pdf2(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar PDF Modificado", "", "PDF Files (*.pdf)")
        if file_path:
            self.pdf2_file = file_path
            self.json_loader_ui.pdf_path = file_path
            self.pdf2_path.setText(os.path.basename(file_path))
            self.update_compare_button()
            self.update_apply_json_button()
    
    def select_save_path(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Guardar PDF Anotado", "", "PDF Files (*.pdf)")
        if file_path:
            self.output_file = file_path
            self.save_path.setText(os.path.basename(file_path))
            self.update_compare_button()
            self.update_apply_json_button()
            self.annotated_viewer.file_path = file_path
            self.rotation_handler.file_path = file_path
    
    def load_json_file(self):
        """Carga un archivo JSON con información de cambios."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Archivo JSON", "",
            "Archivos JSON (*.json);;Todos los archivos (*)", 
            options=options
        )
        
        if file_path:
            # Cargar el JSON
            if self.json_loader_ui.json_loader.load_json(file_path):
                self.json_loader_ui.json_path = file_path
                self.json_loader_ui.update_load_status()
                
                # Habilitar botón de aplicar si también hay PDF cargado
                if self.json_loader_ui.pdf_path:
                    self.json_loader_ui.apply_changes_button.setEnabled(True)
                
                QMessageBox.information(self, "JSON Cargado", 
                                      f"Archivo JSON cargado correctamente: {os.path.basename(file_path)}")
            else:
                QMessageBox.warning(self, "Error de Carga", 
                                  "No se pudo cargar el archivo JSON. Verifique que tenga el formato correcto.")
        #Update button state
        self.update_apply_json_button()        
            
    def update_compare_button(self):
        # Comprueba si ambas rutas existen y no son None
        if self.pdf1_file is not None and self.pdf2_file is not None:
            self.compare_button.setEnabled(True)
        else:
            self.compare_button.setEnabled(False)

    def update_apply_json_button(self):
        # Comprueba si ambas rutas existen y no son None
        if self.pdf1_file is not None and self.pdf2_file is not None and self.json_loader_ui.json_path is not None:
            self.apply_json_button.setEnabled(True)
        else:
            self.apply_json_button.setEnabled(False)

    def start_comparison(self):
        if not self.pdf1_file or not self.pdf2_file:
            return
        
        # Si no se seleccionó una ruta de salida, crear una predeterminada
        if not self.output_file:
            # Usar ruta absoluta para salida
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(base_dir, 'data', 'output')
            self.output_file = os.path.join(output_dir, f"annotated_{os.path.basename(self.pdf2_file)}")
            self.save_path.setText(os.path.basename(self.output_file))
        
        # Obtener las páginas a comparar
        selected_pages = None  # None significa todas las páginas
        if self.specific_pages_radio.isChecked():
            try:
                selected_pages = self.parse_page_selection(self.specific_pages_input.text())
                if not selected_pages:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Selección de páginas", 
                                    "Formato de páginas inválido. Utilizando todas las páginas.")
                    selected_pages = None
            except Exception as e:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Error", 
                                f"Error al interpretar la selección de páginas: {e}")
                selected_pages = None
        
        # Deshabilitar botones durante el procesamiento
        self.compare_button.setEnabled(False)
        self.pdf1_button.setEnabled(False)
        self.pdf2_button.setEnabled(False)
        self.save_button.setEnabled(False)
        
        # Crear solo UNA instancia del WorkerThread
        self.worker = WorkerThread(
            self.pdf1_file, 
            self.pdf2_file, 
            self.output_file,
            self.dpi_spin.value(),
            self.threshold_spin.value(),
            self.eps_spin.value(),
            self.min_samples_spin.value(),
            selected_pages
        )
        
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.comparison_finished)
        self.worker.start()

    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def comparison_finished(self, output_path, circles_by_page, json_loaded = False):
        self.config_layout_visible = False  # Marcar como oculto

        # Habilitar circle_clicked event
        self.circle_clicked_flag = True
        self.annotated_viewer.set_clicks_enabled(True)  # habilitar los clicks
        
        # Habilitar botones
        self.compare_button.setEnabled(True)
        self.pdf1_button.setEnabled(True)
        self.pdf2_button.setEnabled(True)
        self.save_button.setEnabled(True)
        
        # Guardar datos de círculos
        self.circles_by_page = circles_by_page
        
        # Cargar PDF anotado
        self.annotated_viewer.load_pdf(output_path, self.pdf1_file)
        
        # Si estamos en modo lado a lado, actualizar también el visor original
        if self.side_by_side_mode and self.original_viewer:
            self.original_viewer.load_pdf(self.pdf1_file)
            self.original_viewer.current_page = self.annotated_viewer.current_page
            self.original_viewer.render_current_page()

        page_width = 7013
        page_height = 4959

        # Actualizar visibilidad de círculos
        self.annotated_viewer.set_circles(circles_by_page, page_width, page_height, json_loaded)

        # IMPORTANTE: Aplicar inmediatamente el filtrado a las anotaciones visibles
        if json_loaded:
            for page_num in self.circles_by_page:
                self.update_annotations(page_num, self.circles_by_page[page_num])
        else:
            for page_num in self.annotated_viewer.formatted_circles_by_page:
                self.update_annotations(page_num, self.annotated_viewer.formatted_circles_by_page[page_num])

        # Actualizar visibilidad de círculos
        self.toggle_circle_visibility(self.toggle_circles.isChecked())
        
        # Mostrar la lista de cambios en el contenedor derecho
        if hasattr(self.annotated_viewer, 'changes_list_widget') and self.annotated_viewer.changes_list_widget:
            # Obtener la lista de cambios del visor
            changes_widget = self.annotated_viewer.changes_list_widget
            
            # Limpiar el layout del contenedor de cambios
            changes_layout = self.changes_container.layout()
            while changes_layout.count() > 1:  # Mantener solo el título
                item = changes_layout.itemAt(changes_layout.count() - 1)
                widget = item.widget()
                if widget:
                    changes_layout.removeWidget(widget)
                    widget.setParent(None)
            
            # Añadir el widget de cambios al contenedor
            changes_layout.addWidget(changes_widget)
            
            # Asegurarse de que el widget sea visible
            changes_widget.setVisible(True)
            self.changes_container.setVisible(True)

        # Quitar el config_layout del main_layout
        if hasattr(self, 'config_layout') and self.config_layout in [self.main_layout.itemAt(i).layout() for i in range(self.main_layout.count())]:
            # Primero, ocultar todos los widgets dentro del config_layout
            for i in range(self.config_layout.count()):
                item = self.config_layout.itemAt(i)
                if item.widget():
                    item.widget().hide()
            
            # Luego, quitar el layout del main_layout
            self.main_layout.removeItem(self.config_layout)
            
            # Actualizar el layout principal
            self.main_layout.update()
        
        # Asegurarse de que los PDF y controles sean visibles
        if hasattr(self, 'annotated_container'):
            self.annotated_container.show()
        if hasattr(self, 'changes_container'):
            self.changes_container.show()
        if self.side_by_side_mode and hasattr(self, 'original_viewer'):
            self.original_viewer.show()

    def restore_config_layout(self):
        if hasattr(self, 'config_layout_visible') and not self.config_layout_visible:
            # Restaurar al inicio del layout principal
            self.main_layout.insertLayout(0, self.config_layout)
            
            # Mostrar widgets
            for i in range(self.config_layout.count()):
                item = self.config_layout.itemAt(i)
                if item.widget():
                    item.widget().show()
            
            self.config_layout_visible = True

    def sync_page_navigation(self):
        """Conecta las señales de navegación entre ambos visores."""
        if hasattr(self, 'original_viewer') and self.original_viewer and hasattr(self, 'annotated_viewer') and self.annotated_viewer:
            # Cuando cambia la página en el visor original, actualizar el visor anotado
            self.original_viewer.prev_button.clicked.disconnect()  # Desconectar conexiones existentes
            self.original_viewer.next_button.clicked.disconnect()
            #lineas anadidas
            self.annotated_viewer.prev_button.clicked.disconnect()  # Desconectar conexiones existentes
            self.annotated_viewer.next_button.clicked.disconnect()
            
            self.original_viewer.prev_button.clicked.connect(self.sync_prev_page)
            self.original_viewer.next_button.clicked.connect(self.sync_next_page)
            #lineas anadidas
            self.annotated_viewer.prev_button.clicked.connect(self.sync_prev_page)
            self.annotated_viewer.next_button.clicked.connect(self.sync_next_page)

    def sync_prev_page(self):
        """Navega a la página anterior en ambos visores."""
        if self.annotated_viewer.current_page > 0:
            self.annotated_viewer.next_button.setEnabled(True)
            self.annotated_viewer.current_page -= 1
            self.annotated_viewer.render_current_page()
            self.annotated_viewer.update_page_info()
            
            self.original_viewer.next_button.setEnabled(True)
            self.original_viewer.current_page = self.annotated_viewer.current_page
            self.original_viewer.render_current_page()
            self.original_viewer.update_page_info()

    def sync_next_page(self):
        """Navega a la página siguiente en ambos visores."""
        if self.annotated_viewer.current_page < self.annotated_viewer.document.page_count - 1:
            self.annotated_viewer.prev_button.setEnabled(True)
            self.annotated_viewer.current_page += 1
            self.annotated_viewer.render_current_page()
            self.annotated_viewer.update_page_info()
            
            self.original_viewer.prev_button.setEnabled(True)
            self.original_viewer.current_page = self.annotated_viewer.current_page
            self.original_viewer.render_current_page()
            self.original_viewer.update_page_info()
        
    def toggle_circle_visibility(self, state):
        if hasattr(self.annotated_viewer, 'document') and self.annotated_viewer.document:
            try:
                for page_num in range(self.annotated_viewer.document.page_count):
                    page = self.annotated_viewer.document[page_num]
                    for annot in page.annots():
                        if annot.type[1] == 'Circle':
                            if state: 
                                annot.set_flags(0)
                            else: 
                                annot.set_flags(3)
                            annot.update()
                
                # Refrescar vista
                current_page = self.annotated_viewer.current_page
                self.annotated_viewer.reload_page()
            except Exception as e:
                print(f"Error al cambiar visibilidad de círculos: {e}")
        
    def closeEvent(self, event):
        # Si hay un thread activo, detenerlo adecuadamente
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()  # Esperar a que termine
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            temp_dir = os.path.join(base_dir, 'data', 'temp')
            
            # Identificadores de archivos procesados
            pdf_identifiers = []
            if self.pdf1_file:
                pdf_identifiers.append(os.path.basename(self.pdf1_file))
            if self.pdf2_file:
                pdf_identifiers.append(os.path.basename(self.pdf2_file))
            
            # Solo borrar imágenes relacionadas con estos PDFs
            for filename in os.listdir(temp_dir):
                if filename.endswith('.jpg') and any(pdf_id in filename for pdf_id in pdf_identifiers):
                    file_path = os.path.join(temp_dir, filename)
                    try:
                        os.remove(file_path)
                        print(f"Borrada imagen: {filename}")
                    except Exception as e:
                        print(f"Error al borrar {filename}: {e}")
            
            event.accept()
        except Exception as e:
            print(f"Error durante la limpieza: {e}")
            event.accept()

# Punto de entrada de la aplicación
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()