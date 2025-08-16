import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QFileDialog, QLabel, QCheckBox,
                            QProgressBar, QSpinBox, QGroupBox, QRadioButton,QLineEdit,QButtonGroup, QMenu, QToolBar, QAction, QMessageBox, QTabWidget, QSplitter, QSizePolicy)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from src.pdf_rotation import PDFRotationUIHandler, RotationDialog
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
from PyQt5.QtGui import QColor
import fitz  # PyMuPDF
from src.json_loader_ui import JsonLoaderUI
from src.pdf_processor import PDFProcessor
from src.image_comparator import ImageComparator
from src.circle_detector import CircleDetector
from src.pdf_annotator import PDFAnnotator
from src.ui.pdf_viewer import PDFViewer, ChangesListWidget
import cv2
from PIL import Image

# Import application components

RESTART_CODE = 1001  # RESTART_CODE = 1001 # Special code for restart

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
        # Initialize components
        # Use absolute paths for directories

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        temp_dir = os.path.join(base_dir, 'data', 'temp')
        output_dir = os.path.join(base_dir, 'data', 'output')
        
        pdf_processor = PDFProcessor()
        image_comparator = ImageComparator(threshold=self.threshold)
        circle_detector = CircleDetector(eps=self.eps, min_samples=self.min_samples)
        pdf_annotator = PDFAnnotator(output_dir)

        source_pdf1 = self.pdf1
        source_pdf2 = self.pdf2

        # Step 1: Open the original PDF (pdf2) to replace.
        output_pdf_path = os.path.join(output_dir, f"processed_{os.path.basename(self.pdf2)}")
        doc = fitz.open(source_pdf2)

        # Step 2: Convert PDFs to images (only selected pages)
        self.progress.emit(20)
        images1 = pdf_processor.pdf_to_images(source_pdf1, dpi=self.dpi, selected_pages=self.selected_pages)
        self.progress.emit(35)
        images2 = pdf_processor.pdf_to_images(source_pdf2, dpi=self.dpi, selected_pages=self.selected_pages)
        self.progress.emit(50)
        
        # Step 3: Compare images and find differences
        circles_by_page = {}
        
        total_pages = min(len(images1), len(images2))
        if self.selected_pages == None:
            self.selected_pages = list(range(total_pages))

        for i, (img1, img2) in enumerate(zip(images1, images2)):
            # Compare images and obtain coordinates of differences (V2 with respect to V1)
            diff_coords_added, processed_img , image_dim = image_comparator.find_differences(img1, img2)
            if diff_coords_added != None:
                global page_height 
                global page_width

                page_height = image_dim[0]
                page_width = image_dim[1]

                im_pil = Image.fromarray(cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB))
                im_pil.save(f"highlighted_result.png", dpi=(300, 300))  

                page = doc[self.selected_pages[i]]
        
                # Open image to get dimensions in px
                img = Image.open(f"highlighted_result.png")
                width_px, height_px = img.size

                # Convert px to points (1 inch = 72 pt)
                dpi = 300  # It must match your image
                width_pt = width_px * 72 / dpi
                height_pt = height_px * 72 / dpi

                # Insert image with the exact Rect size
                rect = fitz.Rect(0, 0, width_pt, height_pt)
                page.insert_image(rect, filename=f"highlighted_result_red.png")

                # Step 4: Group differences in circles
                if diff_coords_added:
                    circles = circle_detector.group_points_into_circles(diff_coords_added)
                    circles = circle_detector.merge_overlapping_circles(circles)                
                    
                    if circles:
                        if self.selected_pages != None:
                            circles_by_page[self.selected_pages[i]] = circles
                        else:
                            circles_by_page[i] = circles

                # Update progress
                progress = 50 + int((i + 1) / total_pages * 40)
                self.progress.emit(progress)

        # Save the PDF with replaced pages
        doc.save(output_pdf_path)
        doc.close()

        # Step 5: Write on the replaced PDF
        pdf_annotator.add_circle_annotations(input_pdf = output_pdf_path, circles_by_page = circles_by_page, output_pdf = output_pdf_path, dpi=self.dpi)
        
        # Store circle information for use in the UI
        pdf_annotator.save_changes_to_json(self.pdf1, circles_by_page)
        
        self.progress.emit(100)
        self.finished.emit(output_pdf_path, circles_by_page)

class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("PDF Comparator")
        self.setGeometry(100, 100, 1200, 800)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setObjectName("MyContainer")
        central_widget.setStyleSheet("""
            #MyContainer {
                background-color: #0047AB;
            }
        """)

        central_widget.setStyleSheet("""
            /* Fondo global */
            QWidget {
                background-color: #f4f6f8;
                font-family: "Segoe UI", Arial;
                font-size: 14px;
                color: #333;
            }
            
            /* QTabWidget */
            QTabWidget::pane {
                border: 1px solid #dcdcdc;
                background: #ffffff;
                border-radius: 8px;
            }
                                     
            QTabBar::tab {
                background: #eaeaea;
                border-radius: 6px;
                padding: 8px 14px;
                margin: 2px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #333;
                font-weight: bold;
            }

            /* Botones claros con hover azul */
            QPushButton {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #dcdcdc;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #d9ecfa;
                border: 1px solid #90c8f0;
            }
            QPushButton:pressed {
                background-color: #c0e0f8;
                border: 1px solid #70b9ec;
            }

            QScrollBar:vertical {
                border: none;
                background: #f0f4f8;
                width: 20px;
                margin: 0px;
                border-radius: 4px;
            }

            QScrollBar::handle:vertical {
                background: #c0c9d2;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a5b1bd;
            }

            QScrollBar:horizontal {
                border: none;
                background: #f0f4f8;
                height: 20px;
                margin: 0px;
                border-radius: 4px;
            }

            QScrollBar::handle:horizontal {
                background: #c0c9d2;
                border-radius: 4px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #a5b1bd;
            }

            QScrollBar::add-line, QScrollBar::sub-line {
                background: none;
                border: none;
                width: 0;
                height: 0;
            }   
                                     
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #dcdcdc;
                border-radius: 8px;
                margin-top: 12px;
                padding: 10px;
                font-weight: bold;
            }
            QGroupBox:title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 4px 10px;
                background-color: #f4f6f8;
                border-radius: 4px;
                color: #333;
            }

            /* QLabel */
            QLabel {
                color: #333333;
                font-size: 15px;
            }
                            
            QToolBar {
                background-color: #f4f6f8;
                border-bottom: 1px solid #dcdcdc;
            }
                                     
            QMessageBox {
                background-color: #ffffff;
                border-radius: 8px;
            }
                                     
            QFileDialog {
                background-color: #ffffff;
                border-radius: 8px;
            }
                                
            QVBoxLayout{
                background-color: #ffffff;
                border: 1px solid #dcdcdc;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        
        # Main Layout
        main_layout = QVBoxLayout(central_widget)
        
        # Main tabs
        self.tabs = QTabWidget()
        self.apply_shadow(self.tabs)
        # Loading/saving JSON tab
        self.setup_json_tab()

        # Comparison tab
        self.comparison_tab = QWidget()
        self.comparison_tab.setObjectName("MyContainer")
        
        self.setup_comparison_tab()
        self.tabs.addTab(self.comparison_tab, "Compare PDFs")
        
        # Add tabs to the main layout
        main_layout.addWidget(self.tabs)
        # Connect the reset signal
        self.annotated_viewer.restart_signal.connect(self.handle_restart)
    
    def handle_restart(self):
        """Handle the restart request by asking whether to save changes"""
        # Check for unsaved changes
        if self.annotated_viewer.document_modified or self.original_viewer.document_modified:
            reply = QMessageBox.question(
                self, 'Save changes',
                'Do you want to save the changes before restarting?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                return  # Cancel restart process
            elif reply == QMessageBox.StandardButton.Yes:
                if self.annotated_viewer.document_modified:
                    self.rotation_handler.save_document()  
                else:
                    self.rotation_original.save_document()  

        # Restart the application
        self.restart_application()
    
    def restart_application(self):
        """Restart the application completely"""
        QApplication.exit(RESTART_CODE)  # RESTART_CODE is defined further down.
    
    def setup_comparison_tab(self):
        self.main_layout = QVBoxLayout(self.comparison_tab)
        
        # Create a container widget for the configuration
        self.config_container = QWidget()
        # Configuration Area
        self.config_layout = QHBoxLayout()
        
        # File selection
        file_group = QGroupBox("Choose the files")
        file_layout = QVBoxLayout(file_group)
        
        # original PDF 
        pdf1_layout = QHBoxLayout()
        self.pdf1_label = QLabel("Original PDF:")

        self.pdf1_path = QLabel("not selected")
        self.pdf1_button = QPushButton("Upload file")
        self.pdf1_button.clicked.connect(self.select_pdf1)
        self.apply_shadow(self.pdf1_button)
        
        pdf1_layout.addWidget(self.pdf1_label)
        pdf1_layout.addWidget(self.pdf1_path)
        pdf1_layout.addWidget(self.pdf1_button)
        
        # Modified PDF 
        pdf2_layout = QHBoxLayout()
        self.pdf2_label = QLabel("Modified version:")
        self.pdf2_path = QLabel("not selected")
        self.pdf1_button = QPushButton("Upload file")
        self.pdf1_button.clicked.connect(self.select_pdf1)
        self.pdf2_button = QPushButton("Upload PDF")
        self.pdf2_button.clicked.connect(self.select_pdf2)
        self.apply_shadow(self.pdf2_button)

        self.json_button = QPushButton("Upload JSON")
        self.json_button.clicked.connect(self.load_json_file)
        self.apply_shadow(self.json_button)
        
        pdf2_layout.addWidget(self.pdf2_label)
        pdf2_layout.addWidget(self.pdf2_path)
        pdf2_layout.addWidget(self.pdf2_button)
        pdf2_layout.addWidget(self.json_button)
        
        # "Save as" option
        save_layout = QHBoxLayout()
        self.save_label = QLabel("Save as:")
        self.save_path = QLabel("not selected")
        self.save_button = QPushButton("Select path")
        self.save_button.clicked.connect(self.select_save_path)
        self.apply_shadow(self.save_button)
        
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
        self.apply_shadow(self.compare_button)

        self.apply_json_button = QPushButton("Apply JSON annotations")
        self.apply_json_button.clicked.connect(self.json_loader_ui.apply_changes)
        self.apply_json_button.setEnabled(False)
        self.apply_shadow(self.apply_json_button)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        
        action_layout.addWidget(self.apply_json_button)
        action_layout.addWidget(self.compare_button)
        action_layout.addWidget(self.progress_bar)
        
        self.config_layout.addWidget(file_group, 3)
        self.config_layout.addWidget(param_group, 2)
        self.config_layout.addWidget(action_group, 1)

        #Add container to the main layout
        self.main_layout.addWidget(self.config_container)
        
        # Visualization area
        self.view_layout = QHBoxLayout()
        # Original viewer (left)
        self.original_viewer = PDFViewer("Original PDF")

        # Annotated viewer (right)
        self.annotated_viewer = PDFViewer("Annotated PDF", other_visor = self.original_viewer)
        #self.original_viewer.scroll_area = self.annotated_viewer

        self.rotation_handler = PDFRotationUIHandler(self, self.annotated_viewer, title = "Annotated PDF")
        self.annotated_viewer.document_modified = False

        self.rotation_original = PDFRotationUIHandler(self, self.original_viewer, self.rotation_handler, title = "Original PDF")
        self.original_viewer.document_modified = False
         
        # Container of the annotated viewer with the circle checkbox
        self.annotated_container = QWidget()
        self.annotated_layout = QVBoxLayout(self.annotated_container)
        self.annotated_layout.setContentsMargins(0, 0, 0, 0)
        
        self.annotated_layout.addWidget(self.annotated_viewer)
        
        self.toggle_circles = QCheckBox("Show circles")
        self.toggle_circles.setChecked(True)
        self.toggle_circles.stateChanged.connect(self.toggle_circle_visibility)

        self.toggle_side_by_side = QCheckBox("Side by side view")
        self.toggle_side_by_side.setChecked(False) 
        self.toggle_side_by_side.stateChanged.connect(self.toggle_side_by_side_mode)

        self.rotate_both_pdfs = QCheckBox("Rotate both pdfs")
        self.rotate_both_pdfs.setChecked(False) 
        self.rotate_both_pdfs.stateChanged.connect(self.rotate_both)

        # Add the checkbox to the layout after toggle_circles.
        checkbox_layout = QHBoxLayout()
        checkbox_layout.addWidget(self.toggle_circles)
        checkbox_layout.addWidget(self.toggle_side_by_side)
        checkbox_layout.addWidget(self.rotate_both_pdfs)
        self.annotated_layout.addLayout(checkbox_layout)

        # Contenedor para la lista de cambios (derecha)
        self.changes_container = QWidget()
        changes_layout = QVBoxLayout(self.changes_container)
        changes_layout.setContentsMargins(5, 5, 5, 5)
        
        # Title of the change list
        changes_title = QLabel("Detected Changes")
        changes_title.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        changes_title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        changes_title.setStyleSheet("font-size: 11pt; font-weight: bold;")

        changes_layout.addWidget(changes_title)

        # Only add the default annotated viewer
        # Configure the view
        self.view_layout.addWidget(self.annotated_container,5) # The PDF viewer takes up 5/6 of the screen.
        self.view_layout.addWidget(self.changes_container, 1) # The change list occupies 1/6 of the screen.
        
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
        self.annotated_viewer.set_clicks_enabled(False)  # inicialmente deshabilitado
        
        #Connect signals to update circle changes
        self.rotation_handler.save_doc_signal.connect(self.update_annotations_by_page_json)
        self.rotation_original.save_doc_signal.connect(self.update_annotations_by_page_json)
        self.json_loader_ui.add_changes_list.connect(self.comparison_finished)

        print("UI de MainWindow inicializada")
        
    def update_annotations_by_page_json(self, signal_update):
        # To make a copy of the identified circles for the json
        if signal_update:
            self.rotation_handler.rotator.changes_by_page = self.annotated_viewer.formatted_circles_by_page
            self.rotation_handler.rotator.highlights_by_page = self.annotated_viewer.highlights_by_page
            self.rotation_handler.rotator.watermarks_by_page = self.annotated_viewer.watermarks_by_page

            print("Hihglights by page", self.rotation_handler.rotator.highlights_by_page)
            print("Watermarks by page", self.rotation_handler.rotator.watermarks_by_page)

    def setup_json_tab(self):
        """Configura la pestaña de carga/guardado de JSON."""
        
        # Left panel: PDF viewer
        self.json_pdf_viewer = PDFViewer("Annotated PDF")
        
        # Right panel: PDF viewer
        json_control_widget = QWidget()
        self.json_loader_ui = JsonLoaderUI(self.json_pdf_viewer)
        
        # Update changes in formatted circles by page
        self.json_loader_ui.json_loader.extracted_changes_signal.connect(self.update_extracted_circles)
        self.json_loader_ui.update_changes_list_signal.connect(self.update_extracted_circles)
        
        # Configure layout for the control panel
        json_control_layout = QVBoxLayout(json_control_widget)
    
    def load_pdf_for_comparison(self, pdf1_path, pdf2_path):
        """Carga dos PDFs para comparación."""
        # Upload PDFs to the viewers
        print("Problem here 450")
        self.original_viewer.load_pdf(pdf1_path)
        print("Problem here 452")
        self.annotated_viewer.load_pdf(pdf2_path)
        
        # Switch to the comparison tab
        self.tabs.setCurrentIndex(0)
    
    def load_pdf_with_json(self, pdf_path, json_path):
        """Carga un PDF con sus cambios desde un archivo JSON."""
        # This function could be called from outside the class.
        self.json_loader_ui.pdf_path = pdf_path
        self.json_loader_ui.json_path = json_path
        self.json_loader_ui.update_load_status()
        self.json_loader_ui.apply_changes()
        
        # Switch to the JSON tab
        self.tabs.setCurrentIndex(1)

    def on_document_modified(self, doc_modified = ""):
        if doc_modified == "Original PDF":
            self.original_viewer.document_modified = True
        else:
            self.annotated_viewer.document_modified = True
        # Update title or interface to reflect the changes
        self.update_ui_for_unsaved_changes()

    def update_ui_for_unsaved_changes(self):
        """
        Actualiza la interfaz de usuario para indicar que hay cambios sin guardar.
        """
        # 1. Update the window title by adding an asterisk
        import os
        filename = "Modificado"
        self.setWindowTitle(f"PDF Comparator - {filename} *")
        
        # Enable the save button/action (if it exists)
        if hasattr(self, 'save_action'):
            self.save_action.setEnabled(True)
        
        # 3. Optional: Change the color or state of some visual indicator
        if hasattr(self, 'status_label'):
            self.status_label.setText("Documento modificado - Cambios sin guardar")
            
        # Set an internal variable to ask when closing
        self.document_modified = True

    def handle_circle_click(self, page_num, clicked_circle, new_state):
        """Maneja clics en círculos para actualizar anotaciones."""
        print(f"Círculo clickeado en página {page_num}: {clicked_circle}")
        
        # Modification of the circle if necessary or update (self.updated_annotations --> list of changes on the page)
        self.updated_annotations = self.annotated_viewer.modify_annotations(page_num, clicked_circle, new_state)
        
        # Call update_annotations to reflect changes
        self.update_annotations(page_num, self.updated_annotations)
    
    def update_extracted_circles(self, changes_by_page): 
        self.annotated_viewer.formatted_circles_by_page = changes_by_page
        # reflect changes in the changes list widget
        self.annotated_viewer.changes_list_widget.update_changes_list(self.annotated_viewer.formatted_circles_by_page)
  
    def update_annotations(self, page_num, new_annotations, dpi=300):
        """Actualiza las anotaciones del PDF según las modificaciones del usuario."""
        if not hasattr(self.annotated_viewer, 'document') or not self.annotated_viewer.document:
            print("No hay un documento cargado en annotated_viewer.")
            return

        try:
            page = self.annotated_viewer.document[page_num]
            print("Si, page num")
            # Scale factor to convert from image coordinates to PDF
            scale_factor = 72 / dpi
            # Remove previous annotations of type 'Circle'
            annot = page.first_annot
            while annot:
                next_annot = annot.next  # Save reference before deleting
                if annot.type[1] == 'Circle':
                    page.delete_annot(annot)  # Correct method to delete annotations
                annot = next_annot  # Go to the next page
            
            for circle in new_annotations:
                if circle['selected'] == False:
                    continue
                else:
                    x_pdf = circle['x'] * scale_factor
                    y_pdf = circle['y'] * scale_factor
                    radius_pdf = circle['radius'] * scale_factor

                    # Create circle annotation
                    circle_annot = page.add_circle_annot(
                        (x_pdf - radius_pdf, y_pdf - radius_pdf, x_pdf + radius_pdf, y_pdf + radius_pdf)
                    )
                    # Configure properties
                    circle_annot.set_border(width=2)
                    circle_annot.set_colors(stroke=(0, 0, 1))  # Set blue color
                    circle_annot.update(opacity=0.7)

            # Refresh the display to show updates
            self.annotated_viewer.reload_page()

        except Exception as e:
            print(f"Error updating annotations: {e}")


    def clean_temp_directory(self):
        """Clean the temporary directory at the start of the application"""
        try:
            # Obtener la ruta del directorio temporal
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            temp_dir = os.path.join(base_dir, 'data', 'temp')
            
            print(f"Cleaning temporary directory at startup: {temp_dir}")
            
            # Borrar todas las imágenes JPG en el directorio temporal
            for filename in os.listdir(temp_dir):
                if filename.endswith('.jpg'):
                    file_path = os.path.join(temp_dir, filename)
                    try:
                        os.remove(file_path)
                        print(f"Previous temporary image deleted: {filename}")
                    except Exception as e:
                        print(f"Error deleting {filename}: {e}")
        except Exception as e:
            print(f"Error during the initial cleaning: {e}")

    def rotate_both(self, state):
        """Update the joint rotation status and control the visibility of the buttons.."""
        is_checked = (state == Qt.Checked)
        
        # Update the status in the rotation handlers
        if hasattr(self, 'rotation_original') and self.rotation_original:
            self.rotation_original.rotate_both = is_checked
            
            # Show or hide the original PDF button depending on the status.
            if hasattr(self.rotation_original, 'rotate_action'):
                self.rotation_original.rotate_action.setVisible(not is_checked)
            
        if hasattr(self, 'rotation_handler') and self.rotation_handler:
            self.rotation_handler.rotate_both = is_checked
            
            # Hide or show the rotation button of the annotated PDF
            if hasattr(self.rotation_handler, 'rotate_action'):
                self.rotation_handler.rotate_action.setVisible(not is_checked)
        
        # Create or show the 'Rotate both PDFs' button if the checkbox is enabled
        if is_checked:
            # If the rotate both button already exists, just show it.
            if hasattr(self, 'rotate_both_action'):
                self.rotate_both_action.setVisible(True)
            else:
                # Create the rotation button for both PDFs
                print("Creando accion")
                self.rotate_both_action = QAction(QIcon("C:/PDF_Comparator/src/ui/icons/rotate.png"), "Rotar ambos PDFs", self)
                self.rotate_both_action.setStatusTip("Rotar ambos PDFs simultáneamente")
                self.rotate_both_action.triggered.connect(self.show_both_rotation_dialog)
                
                # Add to the toolbar
                toolbar = self.findChild(QToolBar)
                toolbar = self.addToolBar("Principal")
                if toolbar:
                    toolbar.addAction(self.rotate_both_action)
        else:
            # Hide the rotate both button if it exists
            if hasattr(self, 'rotate_both_action'):
                self.rotate_both_action.setVisible(False)
        
        # Update the toolbar geometry
        toolbar = self.findChild(QToolBar)
        if toolbar:
            toolbar.updateGeometry()
        
        print(f"Joint rotation state: {'Enabled' if is_checked else 'Disabled'}")

    def show_both_rotation_dialog(self):
        """Show the dialog to rotate both PDFs."""
        # Verify that both viewers are available
        if (not hasattr(self, 'original_viewer') or not self.original_viewer or 
            not hasattr(self, 'annotated_viewer') or not self.annotated_viewer):
            print("Error: PDF viewers not found")
            return
        
        # Verify that both documents are uploaded.
        if (not self.original_viewer.document or not self.annotated_viewer.document):
            QMessageBox.warning(
                self,
                "Warning",
                "You must open both PDF documents first.."
            )
            return
        
        dialog = RotationDialog(self, "Rotate both PDFs")
        dialog.info_label.setText("Select the rotation for both PDFs:")
        
        if dialog.exec_():
            degrees, scope = dialog.get_rotation_params()
            
            # Apply the rotation to both PDFs
            rotated_original = False
            rotated_annotated = False
            
            # Rotate original PDF
            if scope == "current":
                current_page = self.original_viewer.current_page
                rotated_original = self.rotation_original.rotator.rotate_page(current_page, degrees)
            else:  # scope == "all"
                rotated_original = self.rotation_original.rotator.rotate_all_pages(degrees)
            
            # Rotate annotated PDF
            if scope == "current":
                current_page = self.annotated_viewer.current_page
                rotated_annotated = self.rotation_handler.rotator.rotate_page(current_page, degrees)
            else:  # scope == "all"
                rotated_annotated = self.rotation_handler.rotator.rotate_all_pages(degrees)
            
            # Update display
            if rotated_original:
                self.original_viewer.render_current_page()
            
            if rotated_annotated:
                self.annotated_viewer.render_current_page()
            
            # Show result message
            if rotated_original or rotated_annotated:
                QMessageBox.information(
                    self,
                    "Rotation was applied",
                    f"The rotation of {degrees}° was applied correctly to the PDFs.\n\n"
                    "Remember to save the changes with the 'Save changes' button."
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "The rotation could not be applied to the documents."
                )


    def toggle_side_by_side_mode(self, state):
        """Switch between single viewer mode and two viewers side by side"""
        is_side_by_side = (state == Qt.Checked)
        
        if is_side_by_side == self.side_by_side_mode:
            return  # There is no change
        
        self.side_by_side_mode = is_side_by_side

        if not self.view_layout:
            return
        
        # Clean the layout
        while self.view_layout.count():
            item = self.view_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
        
        # Recreate layout according to the mode
        if is_side_by_side:
            # In side-by-side mode, show both viewers
            self.view_layout.addWidget(self.original_viewer, 4)
            self.view_layout.addWidget(self.annotated_container, 4)
            self.view_layout.addWidget(self.changes_container, 1)  # Change list takes up 1/6 of the screen
            
            # Upload the original PDF if it is not uploaded.
            if self.pdf1_file and not self.original_viewer.document:
                print("Problem here 724")
                self.original_viewer.load_pdf(self.pdf1_file)
    
                #Synchronize the current page
                self.original_viewer.current_page = self.annotated_viewer.current_page
                self.original_viewer.render_current_page()
            
            #Synchronize navigation
            self.sync_page_navigation()
        else:
            # In normal mode, show only the annotated viewer
            self.view_layout.addWidget(self.annotated_container,5)
            self.view_layout.addWidget(self.changes_container, 1)  # Change list takes up 1/6 of the screen

        # Add layouts to the main layout
        self.main_layout.addLayout(self.view_layout)
        
        #Show widgets
        for i in range(self.view_layout.count()):
            item = self.view_layout.itemAt(i)
            if item.widget():
                item.widget().show()

    # Alternation method for the text field
    def toggle_pages_input(self, checked):
        self.specific_pages_input.setEnabled(self.specific_pages_radio.isChecked())
        
    # Method for analyzing page selection
    def parse_page_selection(self, selection_str):
        """
        Convert a string like "1-5,8,10-12" into a list of page numbers [1,2,3,4,5,8,10,11,12]
        """
        pages = []
        
        if not selection_str.strip():
            return None  # Empty chain means all pages
        
        parts = selection_str.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                # Page range (e.g., 1-5)
                start, end = part.split('-')
                try:
                    start_page = int(start.strip())
                    end_page = int(end.strip())
                    if start_page < 1 or end_page < start_page:
                        raise ValueError("Invalid page range")
                    pages.extend(range(start_page, end_page + 1))
                except ValueError:
                    raise ValueError(f"Invalid range: {part}")
            else:
                # Individual page
                try:
                    page = int(part)
                    if page < 1:
                        raise ValueError("The page number must be positive")
                    pages.append(page)
                except ValueError:
                    raise ValueError(f"Invalid page number: {part}")
        
        # Convert to base-0 indices for internal use
        return [p - 1 for p in pages]  # Subtract 1 because the pages are indexed from 0 internally.

    def select_pdf1(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Original PDF", "", "PDF Files (*.pdf)")
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
        file_path, _ = QFileDialog.getOpenFileName(self, "Select modified PDF", "", "PDF Files (*.pdf)")
        if file_path:
            self.pdf2_file = file_path
            self.json_loader_ui.pdf_path = file_path
            self.pdf2_path.setText(os.path.basename(file_path))
            self.update_compare_button()
            self.update_apply_json_button()
    
    def select_save_path(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Annotated PDF", "", "PDF Files (*.pdf)")
        if file_path:
            self.output_file = file_path
            self.save_path.setText(os.path.basename(file_path))
            self.update_compare_button()
            self.update_apply_json_button()
            self.annotated_viewer.file_path = file_path
            self.rotation_handler.file_path = file_path
    
    def load_json_file(self):
        """Upload a JSON file with change information."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select JSON File", "",
            "JSON files (*.json);;TAll files (*)", 
            options=options
        )
        
        if file_path:
            # Load JSON file
            if self.json_loader_ui.json_loader.load_json(file_path):
                self.json_loader_ui.json_path = file_path
                self.json_loader_ui.update_load_status()
                
                # Enable apply button if there is also a PDF uploaded
                if self.json_loader_ui.pdf_path:
                    self.json_loader_ui.apply_changes_button.setEnabled(True)
                
                QMessageBox.information(self, "Loaded json", 
                                      f"JSON file loaded successfully: {os.path.basename(file_path)}")
            else:
                QMessageBox.warning(self, "Load Error", 
                                  "The JSON file could not be loaded. Please check that it has the correct format.")
        #Update button state
        self.update_apply_json_button()        
            
    def update_compare_button(self):
        # Check if both paths exist and are not None
        if self.pdf1_file is not None and self.pdf2_file is not None:
            self.compare_button.setEnabled(True)
        else:
            self.compare_button.setEnabled(False)

    def update_apply_json_button(self):
        # Check if both paths exist and are not None
        if self.pdf1_file is not None and self.pdf2_file is not None and self.json_loader_ui.json_path is not None:
            self.apply_json_button.setEnabled(True)
        else:
            self.apply_json_button.setEnabled(False)

    def start_comparison(self):
        if not self.pdf1_file or not self.pdf2_file:
            return
        
        # If no output path was selected, create a default one.
        if not self.output_file:
            # Use absolute path for output
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(base_dir, 'data', 'output')
            self.output_file = os.path.join(output_dir, f"annotated_{os.path.basename(self.pdf2_file)}")
            self.save_path.setText(os.path.basename(self.output_file))
        
        # Get the pages to compare
        selected_pages = None  # None means all pages
        if self.specific_pages_radio.isChecked():
            try:
                selected_pages = self.parse_page_selection(self.specific_pages_input.text())
                if not selected_pages:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Page selection", 
                                    "Invalid page format. Using all pages.")
                    selected_pages = None
            except Exception as e:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Error", 
                                f"Error interpreting the page selection: {e}")
                selected_pages = None
        
        # Disable buttons during processing
        self.compare_button.setEnabled(False)
        self.pdf1_button.setEnabled(False)
        self.pdf2_button.setEnabled(False)
        self.save_button.setEnabled(False)
        
        # Create only one instance of the WorkerThread
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
        self.config_layout_visible = False  # Mark as hidden

        # Enable circle_clicked event
        self.circle_clicked_flag = True
        self.annotated_viewer.set_clicks_enabled(True)  # enable clicks
        
        # Enable buttons
        self.compare_button.setEnabled(True)
        self.pdf1_button.setEnabled(True)
        self.pdf2_button.setEnabled(True)
        self.save_button.setEnabled(True)
        
        # Save circle data
        self.circles_by_page = circles_by_page
        
        # Load annotated PDF
        print("Problem here 932")
        self.annotated_viewer.load_pdf(output_path, self.pdf1_file)
        
        # If we are in side by side mode, also update the original viewer.
        if self.side_by_side_mode and self.original_viewer:
            print("Problem here 937")
            self.original_viewer.load_pdf(self.pdf1_file)
            self.original_viewer.current_page = self.annotated_viewer.current_page
            self.original_viewer.render_current_page()

        page_width = 7013
        page_height = 4959

        # Update visibility of circles
        self.annotated_viewer.set_circles(circles_by_page, page_width, page_height, json_loaded)

        # IMPORTANT: Apply filtering immediately to the visible annotations.
        if json_loaded:
            for page_num in self.circles_by_page:
                self.update_annotations(page_num, self.circles_by_page[page_num])
        else:
            for page_num in self.annotated_viewer.formatted_circles_by_page:
                self.update_annotations(page_num, self.annotated_viewer.formatted_circles_by_page[page_num])

        # Update visibility of circles
        self.toggle_circle_visibility(self.toggle_circles.isChecked())
        
        # Show the list of changes in the right container
        if hasattr(self.annotated_viewer, 'changes_list_widget') and self.annotated_viewer.changes_list_widget:
            # Obtain the change log from the viewer
            changes_widget = self.annotated_viewer.changes_list_widget
            
            # Clean the layout of the changes container
            changes_layout = self.changes_container.layout()
            while changes_layout.count() > 1:  # Keep only the title
                item = changes_layout.itemAt(changes_layout.count() - 1)
                widget = item.widget()
                if widget:
                    changes_layout.removeWidget(widget)
                    widget.setParent(None)
            
            # Add the changes widget to the container
            changes_layout.addWidget(changes_widget)
            
            # Make sure that the widget is visible
            changes_widget.setVisible(True)
            self.changes_container.setVisible(True)

        # Remove the config_layout from the main_layout
        if hasattr(self, 'config_layout') and self.config_layout in [self.main_layout.itemAt(i).layout() for i in range(self.main_layout.count())]:
            # First, hide all the widgets inside the config_layout
            for i in range(self.config_layout.count()):
                item = self.config_layout.itemAt(i)
                if item.widget():
                    item.widget().hide()
            
            # Then, remove the layout from the main_layout.
            self.main_layout.removeItem(self.config_layout)
            
            # Update the main layout
            self.main_layout.update()
        
        # Make sure that the PDFs and controls are visible
        if hasattr(self, 'annotated_container'):
            self.annotated_container.show()
        if hasattr(self, 'changes_container'):
            self.changes_container.show()
        if self.side_by_side_mode and hasattr(self, 'original_viewer'):
            self.original_viewer.show()

    def restore_config_layout(self):
        if hasattr(self, 'config_layout_visible') and not self.config_layout_visible:
            # Restore to the beginning of the main layout
            self.main_layout.insertLayout(0, self.config_layout)
            
            # Show widgets
            for i in range(self.config_layout.count()):
                item = self.config_layout.itemAt(i)
                if item.widget():
                    item.widget().show()
            
            self.config_layout_visible = True

    def sync_page_navigation(self):
        """Connect the navigation signals between both viewers."""
        if hasattr(self, 'original_viewer') and self.original_viewer and hasattr(self, 'annotated_viewer') and self.annotated_viewer:
            # When the page changes in the original viewer, update the annotated viewer.
            self.original_viewer.prev_button.clicked.disconnect()  # Desconectar conexiones existentes
            self.original_viewer.next_button.clicked.disconnect()
            self.annotated_viewer.prev_button.clicked.disconnect() 
            self.annotated_viewer.next_button.clicked.disconnect()
            
            self.original_viewer.prev_button.clicked.connect(self.sync_prev_page)
            self.original_viewer.next_button.clicked.connect(self.sync_next_page)
            self.annotated_viewer.prev_button.clicked.connect(self.sync_prev_page)
            self.annotated_viewer.next_button.clicked.connect(self.sync_next_page)

    def sync_prev_page(self):
        """Disconnect existing connections."""
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
        """Navigate to the next page in both viewers."""
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
                
                # Refresh view
                current_page = self.annotated_viewer.current_page
                self.annotated_viewer.reload_page()
            except Exception as e:
                print(f"Error changing visibility of circles: {e}")
        
    def closeEvent(self, event):
        # If there is an active thread, stop it properly.
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()  
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            temp_dir = os.path.join(base_dir, 'data', 'temp')
            
            # Processed file identifiers
            pdf_identifiers = []
            if self.pdf1_file:
                pdf_identifiers.append(os.path.basename(self.pdf1_file))
            if self.pdf2_file:
                pdf_identifiers.append(os.path.basename(self.pdf2_file))
            
            # Only delete images related to these PDFs
            for filename in os.listdir(temp_dir):
                if filename.endswith('.jpg') and any(pdf_id in filename for pdf_id in pdf_identifiers):
                    file_path = os.path.join(temp_dir, filename)
                    try:
                        os.remove(file_path)
                        print(f"Image deleted: {filename}")
                    except Exception as e:
                        print(f"Error deleting {filename}: {e}")
            
            event.accept()
        except Exception as e:
            print(f"Error during cleaning: {e}")
            event.accept()

    def apply_shadow(self, widget, blur=15, x_offset=0, y_offset=2, alpha=40):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur)  # Blurring of the shadow
        shadow.setXOffset(x_offset)  # Horizontal shadow
        shadow.setYOffset(y_offset)  # Vertical shadow
        shadow.setColor(QColor(0, 0, 0, alpha))  # Black color with transparency
        widget.setGraphicsEffect(shadow)

# Application entry point
def main():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()