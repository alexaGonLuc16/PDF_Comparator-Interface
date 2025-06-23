# Integración de la carga/guardado JSON en la aplicación principal

# Importaciones necesarias
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, QSplitter, QHBoxLayout, QLabel, QGroupBox, QPushButton, QRadioButton, QButtonGroup, QSpinBox, QLineEdit, QProgressBar, QCheckBox
from PyQt5.QtCore import Qt
import sys
import os

# Importar componentes de la aplicación
from ui.pdf_viewer import PDFViewer
from json_loader_ui import JsonLoaderUI
from image_comparator import ImageComparator
from pdf_annotator import PDFAnnotator

class PDFComparatorApp(QMainWindow):
    def __init__(self):
        super(PDFComparatorApp, self).__init__()
        self.setWindowTitle("PDF Comparator")
        self.setGeometry(100, 100, 1200, 800)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        
        # Pestañas principales
        self.tabs = QTabWidget()
        
        # Pestaña de comparación
        self.comparison_tab = QWidget()
        self.setup_comparison_tab()
        self.tabs.addTab(self.comparison_tab, "Comparar PDFs")
        
        # Pestaña de carga/guardado JSON
        self.json_tab = QWidget()
        self.setup_json_tab()
        self.tabs.addTab(self.json_tab, "Cargar/Guardar Cambios")
        
        # Agregar pestañas al layout principal
        main_layout.addWidget(self.tabs)
    
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
        self.pdf2_button = QPushButton("Upload file")
        self.pdf2_button.clicked.connect(self.select_pdf2)
        
        pdf2_layout.addWidget(self.pdf2_label)
        pdf2_layout.addWidget(self.pdf2_path)
        pdf2_layout.addWidget(self.pdf2_button)
        
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

        self.apply_json_button = QPushButton("Apply JSON Annotations")
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
        self.rotation_handler = PDFRotationUIHandler(self, self.annotated_viewer, title = "Rotate Annotated PDF")

        self.rotation_original = PDFRotationUIHandler(self, self.original_viewer, self.rotation_handler, title = "Rotate Original PDF")
         
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

        print("UI de MainWindow inicializada")
        
    def setup_json_tab(self):
        """Configura la pestaña de carga/guardado de JSON."""
        layout = QVBoxLayout(self.json_tab)
        
        # Crear un divisor horizontal
        splitter = QSplitter(Qt.Horizontal)
        
        # Panel izquierdo: Visor de PDF
        self.json_pdf_viewer = PDFViewer("PDF con Cambios Cargados")
        
        # Panel derecho: Controles de JSON
        json_control_widget = QWidget()
        self.json_loader_ui = JsonLoaderUI(self.json_pdf_viewer)
        
        # Configurar layout para el panel de control
        json_control_layout = QVBoxLayout(json_control_widget)
        json_control_layout.addWidget(self.json_loader_ui)
        
        # Agregar paneles al divisor
        splitter.addWidget(self.json_pdf_viewer)
        splitter.addWidget(json_control_widget)
        
        # Configurar ancho relativo (70% visor, 30% controles)
        splitter.setSizes([700, 300])
        
        # Agregar divisor al layout
        layout.addWidget(splitter)
    
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

# Punto de entrada de la aplicación
def main():
    app = QApplication(sys.argv)
    window = PDFComparatorApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
