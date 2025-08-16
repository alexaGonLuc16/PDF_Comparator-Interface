from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, QSplitter, QHBoxLayout, QLabel, QGroupBox, QPushButton, QRadioButton, QButtonGroup, QSpinBox, QLineEdit, QProgressBar, QCheckBox
from PyQt5.QtCore import Qt
import sys
import os

# Application components
from ui.pdf_viewer import PDFViewer
from json_loader_ui import JsonLoaderUI
from image_comparator import ImageComparator
from pdf_annotator import PDFAnnotator
from pdf_rotation import PDFRotationUIHandler

class PDFComparatorApp(QMainWindow):
    def __init__(self):
        super(PDFComparatorApp, self).__init__()
        self.setWindowTitle("PDF Comparator")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main Layout
        main_layout = QVBoxLayout(central_widget)
        
        # Main tabs
        self.tabs = QTabWidget()
        
        # Comparison tab
        self.comparison_tab = QWidget()
        self.setup_comparison_tab()
        self.tabs.addTab(self.comparison_tab, "Comparar PDFs")
        
        # Loading/saving JSON tab
        self.json_tab = QWidget()
        self.setup_json_tab()
        self.tabs.addTab(self.json_tab, "Cargar/Guardar Cambios")
        
        # Add tabs to the main layout
        main_layout.addWidget(self.tabs)
    
    def setup_comparison_tab(self):
        self.main_layout = QVBoxLayout(self.comparison_tab)
        
        #Create a container widget for the configuration
        self.config_container = QWidget()
        # Configuration Area
        self.config_layout = QHBoxLayout()
        
        # File Selection
        file_group = QGroupBox("Choose the files")
        file_layout = QVBoxLayout(file_group)
        
        # Original PDF 
        pdf1_layout = QHBoxLayout()
        self.pdf1_label = QLabel("Original PDF:")
        self.pdf1_path = QLabel("not selected")
        self.pdf1_button = QPushButton("Upload file")
        self.pdf1_button.clicked.connect(self.select_pdf1)
        
        pdf1_layout.addWidget(self.pdf1_label)
        pdf1_layout.addWidget(self.pdf1_path)
        pdf1_layout.addWidget(self.pdf1_button)
        
        # Modified PDF
        pdf2_layout = QHBoxLayout()
        self.pdf2_label = QLabel("Modified version:")
        self.pdf2_path = QLabel("not selected")
        self.pdf2_button = QPushButton("Upload file")
        self.pdf2_button.clicked.connect(self.select_pdf2)
        
        pdf2_layout.addWidget(self.pdf2_label)
        pdf2_layout.addWidget(self.pdf2_path)
        pdf2_layout.addWidget(self.pdf2_button)
        
        # Save as
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
        
        # Parameters
        param_group = QGroupBox("Parameters")
        param_layout = QVBoxLayout(param_group)
        
        # DPI
        dpi_layout = QHBoxLayout()
        dpi_layout.addWidget(QLabel("DPI:"))
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(300)
        dpi_layout.addWidget(self.dpi_spin)
        
        # Threshold
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

        # Action buttons
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

        # Add container to the main layout
        self.main_layout.addWidget(self.config_container)
        
        # Visualization area
        self.view_layout = QHBoxLayout()
        # Original viewer (left)
        self.original_viewer = PDFViewer("Original PDF")

        # Annotated viewer (right)
        self.annotated_viewer = PDFViewer("Annotated PDF")
        self.rotation_handler = PDFRotationUIHandler(self, self.annotated_viewer, title = "Rotate Annotated PDF")

        self.rotation_original = PDFRotationUIHandler(self, self.original_viewer, self.rotation_handler, title = "Rotate Original PDF")
         
        # Container of the annotated viewer with the circle checkbox
        self.annotated_container = QWidget()
        self.annotated_layout = QVBoxLayout(self.annotated_container)
        self.annotated_layout.setContentsMargins(0, 0, 0, 0)
        
        self.annotated_layout.addWidget(self.annotated_viewer)
        
        self.toggle_circles = QCheckBox("Show circles")
        self.toggle_circles.setChecked(True)
        self.toggle_circles.stateChanged.connect(self.toggle_circle_visibility)

        self.toggle_side_by_side = QCheckBox("Side by side view")
        self.toggle_side_by_side.setChecked(False) #disabled by default
        self.toggle_side_by_side.stateChanged.connect(self.toggle_side_by_side_mode)

        self.rotate_both_pdfs = QCheckBox("Rotate both pdfs")
        self.rotate_both_pdfs.setChecked(False) #disabled by default
        self.rotate_both_pdfs.stateChanged.connect(self.rotate_both)

        # Add the checkbox to the layout after toggle_circles
        checkbox_layout = QHBoxLayout()
        checkbox_layout.addWidget(self.toggle_circles)
        checkbox_layout.addWidget(self.toggle_side_by_side)
        checkbox_layout.addWidget(self.rotate_both_pdfs)
        self.annotated_layout.addLayout(checkbox_layout)

        # Container for the change list (right)
        self.changes_container = QWidget()
        changes_layout = QVBoxLayout(self.changes_container)
        changes_layout.setContentsMargins(5, 5, 5, 5)
        
        # Title of the change list
        changes_title = QLabel("Detected Changes")
        changes_title.setAlignment(Qt.AlignCenter)
        changes_title.setStyleSheet("font-size: 11pt; font-weight: bold;")
        
        changes_layout.addWidget(changes_title)

        # Configure view
        self.view_layout.addWidget(self.annotated_container,5)  # PDF viewer occupies 5/6 of the screen
        self.view_layout.addWidget(self.changes_container, 1)  # Change list takes up 1/6 of the screen
        
        # Add layouts to the main layout
        self.main_layout.addLayout(self.config_layout, 1)
        self.main_layout.addLayout(self.view_layout, 4)
        
        # State variables
        self.pdf1_file = None
        self.pdf2_file = None
        self.output_file = None
        self.circles_by_page = {}
        self.side_by_side_mode = False

        # Flag to enable circle_click event
        self.circle_clicked_flag = False
        self.annotated_viewer.circle_clicked.connect(self.handle_circle_click)
        self.annotated_viewer.update_annotations.connect(self.update_annotations)
        self.annotated_viewer.set_clicks_enabled(False) 
        
        #connect signal to update circle changes
        self.rotation_handler.save_doc_signal.connect(self.update_annotations_by_page_json)
        self.rotation_original.save_doc_signal.connect(self.update_annotations_by_page_json)

        print("MainWindow UI initialized")
        
    def setup_json_tab(self):
        """Configure the JSON load/save tab."""
        layout = QVBoxLayout(self.json_tab)
        
        # Create a horizontal divider
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel: PDF viewer
        self.json_pdf_viewer = PDFViewer("PDF con Cambios Cargados")
        
        # Right panel: JSON controls
        json_control_widget = QWidget()
        self.json_loader_ui = JsonLoaderUI(self.json_pdf_viewer)
        
        # Set up layout for the control panel
        json_control_layout = QVBoxLayout(json_control_widget)
        json_control_layout.addWidget(self.json_loader_ui)
        
        # Add panels to the divider
        splitter.addWidget(self.json_pdf_viewer)
        splitter.addWidget(json_control_widget)
        
        # Set relative width (70% viewer, 30% controls)
        splitter.setSizes([700, 300])
        
        # Add divider to the layout
        layout.addWidget(splitter)
    
    def load_pdf_for_comparison(self, pdf1_path, pdf2_path):
        """Upload two PDFs for comparison."""
        # Load PDFs in the viewers
        self.original_viewer.load_pdf(pdf1_path)
        self.annotated_viewer.load_pdf(pdf2_path)
        
        # Switch to the comparison tab
        self.tabs.setCurrentIndex(0)
    
    def load_pdf_with_json(self, pdf_path, json_path):
        """Upload a PDF with its changes from a JSON file."""
        # This function could be called from outside the class.
        self.json_loader_ui.pdf_path = pdf_path
        self.json_loader_ui.json_path = json_path
        self.json_loader_ui.update_load_status()
        self.json_loader_ui.apply_changes()
        
        # Switch to the JSON tab
        self.tabs.setCurrentIndex(1)

# Punto de entrada de la aplicación
def main():
    app = QApplication(sys.argv)
    window = PDFComparatorApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
