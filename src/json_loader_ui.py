# Implementation of the JSON loading section in the user interface

from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                           QFileDialog, QFrame, QMessageBox, QDialog, QSplitter,
                           QWidget, QTabWidget)
from PyQt5.QtCore import Qt, pyqtSignal
import os

from src.json_loader import PDFJsonLoader
from src.json_saver import PDFJsonSaver

class JsonLoaderUI(QWidget):
    add_changes_list = pyqtSignal(str, dict, bool)  # file path, dictionary of changes
    update_changes_list_signal = pyqtSignal(dict)  # dictionary of changes
    """
    Widget to load changes from a JSON file.
    """
    def __init__(self, pdf_viewer, parent=None):
        super(JsonLoaderUI, self).__init__(parent)
        self.pdf_viewer = pdf_viewer
        self.json_loader = PDFJsonLoader()
        self.json_saver = PDFJsonSaver()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Load Changes")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Load section
        load_section_label = QLabel("Load changes from a JSON")
        load_section_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(load_section_label)
        
        load_layout = QHBoxLayout()
        
        self.load_json_button = QPushButton("Load JSON")
        self.load_json_button.clicked.connect(self.load_json_file)
        
        self.load_pdf_button = QPushButton("Load PDF")
        self.load_pdf_button.clicked.connect(self.load_pdf_file)
        
        self.apply_changes_button = QPushButton("Apply Changes")
        self.apply_changes_button.clicked.connect(self.apply_changes)
        self.apply_changes_button.setEnabled(False)
        
        load_layout.addWidget(self.load_json_button)
        load_layout.addWidget(self.load_pdf_button)
        load_layout.addWidget(self.apply_changes_button)
        
        layout.addLayout(load_layout)
        
        # Load status
        self.load_status_label = QLabel("No files loaded")
        layout.addWidget(self.load_status_label)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator2)
        
        # Save section
        save_section_label = QLabel("Save changes to JSON")
        save_section_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(save_section_label)
        
        save_layout = QHBoxLayout()
        
        self.save_json_button = QPushButton("Save changes")
        self.save_json_button.clicked.connect(self.save_changes)
        
        save_layout.addWidget(self.save_json_button)
        
        layout.addLayout(save_layout)
        
        # Information
        info_label = QLabel(
            "This feature allows you to save and load changes detected in PDFs "
            "without needing to reprocess them again."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-style: italic;")
        layout.addWidget(info_label)
        
        # Variables for tracking
        self.json_path = None
        self.pdf_path = None
    
    def load_json_file(self):
        """Loads a JSON file with change information."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select JSON File", "",
            "JSON Files (.json);;All Files ()", 
            options=options
        )
        
        if file_path:
            # Cargar el JSON
            if self.json_loader.load_json(file_path):
                self.json_path = file_path
                self.update_load_status()
                
                # Habilitar botón de aplicar si también hay PDF cargado
                if self.pdf_path:
                    self.apply_changes_button.setEnabled(True)
                
                QMessageBox.information(self, "JSON Loaded", 
                                      f"JSON file loaded successfully: {os.path.basename(file_path)}")
            else:
                QMessageBox.warning(self, "Load Error", 
                                  "The JSON file could not be loaded. Please verify it has the correct format.")
    
    def load_pdf_file(self):
        """Loads a PDF file to apply changes to."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF File", "",
            "PDF Files (.pdf);;All Files ()", 
            options=options
        )
        
        if file_path:
            self.pdf_path = file_path
            self.update_load_status()
            
            # Enable "Apply Changes" button if a JSON is also loaded
            if self.json_path:
                self.apply_changes_button.setEnabled(True)
            
            QMessageBox.information(self, "PDF Loaded", 
                                  f"PDF file loaded successfully: {os.path.basename(file_path)}")
    
    def apply_changes(self):
        """Applies the changes from the JSON to the PDF and shows the result."""
        if not self.json_path or not self.pdf_path:
            QMessageBox.warning(self, "Error", "You must load both a JSON file and a PDF.")
            return
        
        try:
            # Generate output file name
            base_name = os.path.basename(self.pdf_path)
            output_path = f"loaded_{base_name}"
            
            # Apply changes
            result_path = self.json_loader.apply_changes_to_pdf(self.pdf_path, output_path)

            if result_path != None:
                # Extract changes to display in the viewer
                changes_by_page = self.json_loader.extract_changes_by_page()
                
                # Convert from dictionary format to list format if necessary
                formatted_changes = {}
                for page_num, changes in changes_by_page.items():
                    formatted_changes[page_num] = changes
                
                # Get PDF dimensions (hardcoded for the example)
                # In a real implementation, you should get this from the PDF
                page_width = 612  # Standard width of an A4 page in points
                page_height = 792  # Standard height of an A4 page in points
                
                # Load PDF into the viewer
                self.pdf_viewer.load_pdf(result_path)
                
                # Configure circles
                self.add_changes_list.emit(result_path, formatted_changes, True)
                self.update_changes_list_signal.emit(formatted_changes)

                # Add changes list widget to the main window
                QMessageBox.information(self, "Changes Applied", 
                                      "The changes have been successfully applied to the PDF.")

            else:
                QMessageBox.warning(self, "Error", "The changes could not be applied to the PDF.")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error applying changes: {str(e)}")

    def save_changes(self):
        """Saves the current changes to a JSON file."""
        if not hasattr(self.pdf_viewer, 'formatted_circles_by_page') or not self.pdf_viewer.formatted_circles_by_page:
            QMessageBox.warning(self, "Error", "There are no changes to save.")
            return
        
        if not hasattr(self.pdf_viewer, 'file_path') or not self.pdf_viewer.file_path:
            QMessageBox.warning(self, "Error", "No PDF is loaded.")
            return
        
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Changes to JSON", "",
            "JSON Files (.json);;All Files ()", 
            options=options
        )
        
        if file_path:
            try:
                # Extract highlights if possible
                highlights_by_page = None
                if hasattr(self.pdf_viewer, 'document') and self.pdf_viewer.document:
                    highlights_by_page = self.json_saver.extract_highlights_from_pdf(
                        self.pdf_viewer.document, self.pdf_viewer.dpi)
                
                # Extract rotations if possible
                rotations_by_page = None
                if hasattr(self.pdf_viewer, 'document') and self.pdf_viewer.document:
                    rotations_by_page = self.json_saver.extract_rotations_from_pdf(
                        self.pdf_viewer.document)
                
                # No watermark information available, so pass None
                watermarks = None
                
                # Save changes
                result_path = self.json_saver.save_changes_to_json(
                    self.pdf_viewer.file_path,
                    self.pdf_viewer.formatted_circles_by_page,
                    highlights_by_page,
                    rotations_by_page,
                    watermarks,
                    file_path,
                    self.pdf_viewer.dpi
                )
                
                QMessageBox.information(self, "Changes Saved", 
                                      f"The changes have been saved to: {result_path}")
            
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error saving changes: {str(e)}")
    
    def update_load_status(self):
        """Updates the load status label."""
        status = []
        
        if self.json_path:
            status.append(f"JSON: {os.path.basename(self.json_path)}")
        
        if self.pdf_path:
            status.append(f"PDF: {os.path.basename(self.pdf_path)}")
        
        if status:
            self.load_status_label.setText("Loaded files: " + ", ".join(status))
        else:
            self.load_status_label.setText("No files loaded")
