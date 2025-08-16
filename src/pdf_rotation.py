import tempfile
import os
import shutil
import datetime
import json
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (
    QAction, QMenu, QToolBar, QToolButton, 
    QMessageBox, QDialog, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog
)
from PyQt5.QtGui import QIcon, QTransform, QPixmap, QImage
from PyQt5.QtCore import Qt, pyqtSignal, QByteArray, QObject

class PDFRotator:
    """Class to handle PDF file rotation."""
    
    def __init__(self, document_handler):
        """
        Initialize the PDF rotator. 
        Args: 
        document_handler: Object that manages the current PDF document 
        """
        self.document_handler = document_handler
        # Variable to track if there are unsaved changes
        self.has_unsaved_changes = False
        self.temp_path = None
        self.rotations_by_page = {} # dictionary of rotation by page (index, value)
        self.changes_by_page = {} # copy of the changes (circles) for the json
        self.highlights_by_page = {}
        self.watermarks_by_page = {} 

    def rotate_page(self, page_index, degrees):
        """
        Rotate a specific page of the PDF.
        Args:
        page_index: Page index (starting at 0)
        degrees: Degrees of rotation (90, 180, 270)

        Returns:
        bool: True if the rotation was successful, False otherwise
        """
        if not self.document_handler.document:
            return False
        
        try:
            # Get the current rotation value
            page = self.document_handler.document[page_index]
            current_rotation = page.rotation
            
            # Calculate the new rotation (sum and normalize to 0, 90, 180, 270)
            new_rotation = (current_rotation + degrees) % 360
            
            # Set the new rotation for the page
            page.set_rotation(new_rotation)

            # Apply zoom
            matrix = fitz.Matrix(self.document_handler.zoom_factor, self.document_handler.zoom_factor)
            # Obtén el mapa de píxeles de la página rotada
            pix = page.get_pixmap(matrix =  matrix)

            # Convert to QImage/QPixmap
            img_data = QByteArray(pix.samples)
            qimg = QImage(img_data, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            
            # Show on the label
            self.document_handler.page_label.setPixmap(pixmap)
            self.document_handler.page_label.resize(pixmap.size())

            # Mark that there are changes not saved
            self.has_unsaved_changes = True

            return True
        except Exception as e:
            print(f"Error rotating the page: {str(e)}")
            return False
    
    def rotate_all_pages(self, degrees):
        """
        Rotate all pages of the PDF.
        Args:
        degrees: Rotation degrees (90, 180, 270)
        
        Returns:
        bool: True if the rotation was successful, False otherwise.
        """
        if not self.document_handler.document:
            return False
        
        try:
            for page_idx in range(len(self.document_handler.document)):
                self.rotate_page(page_idx, degrees)
            return True
        except Exception as e:
            print(f"Error rotating all pages: {str(e)}")
            return False
    
    def save_document(self, file_path=None):
        
        """
        Save the document with the applied rotations.
        Args:
            file_path: Path where to save the file. 
        
        Returns:
            bool: True if the save was successful, False otherwise.
        """
        if not self.document_handler.document:
            return False
        
        try:
            # If no path is provided, use the current path of the document.
            save_path = file_path or self.document_handler.file_path
            current_page = self.document_handler.current_page  # Save the current page
            
            # Save in a temporary file first
            # Create a temporary file
            temp_fd, self.temp_path = tempfile.mkstemp(suffix=".pdf")

            print("Temp file",self.temp_path)
            os.close(temp_fd)
            
            doc_copy = fitz.open()
            
            for page_idx in range(len(self.document_handler.document)):
                doc_copy.insert_pdf(self.document_handler.document, from_page=page_idx, to_page=page_idx)
            
            # Save the temporary copy
            doc_copy.save(
                self.temp_path,
                garbage=4,  # Maximum cleanliness
                deflate=True,  # compress
                clean=True  # Clean and reduce size
            )
            
            # Close the temporary document
            doc_copy.close()
    
            # Replace the destination file with the temporary one.
            shutil.copy2(self.temp_path, save_path)

            # Delete the temporary file
            os.unlink(self.temp_path)
            
            # Restart the changes variable without saving
            self.has_unsaved_changes = False
            
            json_path = os.path.splitext(save_path)[0] + "_changes.json"
            print("Path for json file", json_path)

            self.save_changes_to_json(original_pdf = save_path, 
                                    formatted_circles_by_page = self.changes_by_page ,
                                    highlights_by_page = self.highlights_by_page, 
                                    rotations_by_page = self.rotations_by_page, 
                                    watermarks_by_page=self.watermarks_by_page,
                                    output_path = json_path)
            
            return True, current_page
        except Exception as e:
            print(f"Error saving the document: {str(e)}")
            return False, 0
        
    def save_changes_to_json(self, original_pdf, formatted_circles_by_page = None, 
                           highlights_by_page=None, rotations_by_page=None, 
                           watermarks_by_page =None, output_path=None, dpi=300):
        print("Changes before saving to json", formatted_circles_by_page)
        """
        Save the changes made to a PDF in a JSON file.
        
        Args:
            original_pdf: Path to the original PDF
            formatted_circles_by_page: Dictionary of changes by page
            highlights_by_page: Dictionary of highlights by page
            rotations_by_page: Dictionary of rotations by page
            watermarks: List of watermarks applied
            output_path: Path to save the JSON filedpi: DPI used for image conversion
        
        Returns:
            Path to the saved JSON file
        """
    
        try:
            # Initialize JSON structure
            json_data = {
                "metadata": {
                    "original_pdf": original_pdf,
                    "processed_date": datetime.datetime.now().isoformat(),
                    "version": "1.0",
                    "dpi": dpi
                },
                "pages": {}
            }

            if formatted_circles_by_page:
                # Add change information per page
                for page_num, changes in formatted_circles_by_page.items():
                    # Convert to string since JSON keys must be strings
                    page_key = str(page_num)
                    
                    if page_key not in json_data["pages"]:
                        json_data["pages"][page_key] = {
                            "changes": [],
                            "highlights": [],
                            "rotation": 0,
                            "watermarks": watermarks_by_page or []
                        }
                    # Add changes to the page
                    for change in changes:
                        change_data = {
                            "x": change['x'],
                            "y": change['y'],
                            "radius": change['radius'],
                            "description": change.get("description", f"Difference {len(json_data['pages'][page_key]['changes']) + 1}"),
                            "selected": change.get("selected", True)
                        }
                        
                        json_data["pages"][page_key]["changes"].append(change_data)

            # Add highlights per page if available
            if highlights_by_page:
                for page_num, highlights in highlights_by_page.items():
                    page_key = str(page_num)
                    
                    if page_key not in json_data["pages"]:
                        json_data["pages"][page_key] = {
                            "changes": [],
                            "highlights": [],
                            "rotation": 0,
                            "watermarks": watermarks_by_page or []
                        }
                    
                    json_data["pages"][page_key]["highlights"] = highlights

            # Add rotations per page if available
            if rotations_by_page:
                for page_num, rotation in rotations_by_page.items():
                    page_key = str(page_num)
                    
                    if page_key not in json_data["pages"]:
                        json_data["pages"][page_key] = {
                            "changes": [],
                            "highlights": [],
                            "rotation": 0,
                            "watermarks": watermarks_by_page or []
                        }
                    
                    json_data["pages"][page_key]["rotation"] = rotation
            
            # Add watermarks per page if available
            if watermarks_by_page:
                for page_num, watermark in watermarks_by_page.items():
                    page_key = str(page_num)
                    
                    if page_key not in json_data["pages"]:
                        json_data["pages"][page_key] = {
                            "changes": [],
                            "highlights": [],
                            "rotation": 0
                        }
                    
                    json_data["pages"][page_key]["watermarks"] = watermark

            # Save JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2)

            print("Json saved successfully!")
            
            return output_path
        except Exception as e:
            print(f"Error saving json: {str(e)}")
            return ""
    
class RotationDialog(QDialog):
    """Dialogue to confirm and select rotation options."""
    
    def __init__(self, parent=None, title ="Rotate PDF"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(300, 150)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        self.info_label = QLabel("Select the rotation you want to apply:")
        layout.addWidget(self.info_label)
        
        # Rotation buttons
        btn_layout = QHBoxLayout()
        
        self.rotate90_btn = QPushButton("Rotate 90° ↻")
        self.rotate180_btn = QPushButton("Rotate 180° ↻↻")
        self.rotate270_btn = QPushButton("Rotate 270° ↺")
        
        btn_layout.addWidget(self.rotate90_btn)
        btn_layout.addWidget(self.rotate180_btn)
        btn_layout.addWidget(self.rotate270_btn)
        
        layout.addLayout(btn_layout)
        
        # Option to rotate all pages or just the current one
        self.scope_layout = QHBoxLayout()
        self.current_page_btn = QPushButton("Current page")
        self.all_pages_btn = QPushButton("All pages")
        
        self.scope_layout.addWidget(self.current_page_btn)
        self.scope_layout.addWidget(self.all_pages_btn)
        
        layout.addLayout(self.scope_layout)
        
        # Cancelar button
        self.cancel_btn = QPushButton("Cancel")
        layout.addWidget(self.cancel_btn)
        
        self.setLayout(layout)
        
        # Conect signals
        self.rotate90_btn.clicked.connect(lambda: self.accept_rotation(90))
        self.rotate180_btn.clicked.connect(lambda: self.accept_rotation(180))
        self.rotate270_btn.clicked.connect(lambda: self.accept_rotation(270))
        self.current_page_btn.clicked.connect(lambda: self.set_scope("current"))
        self.all_pages_btn.clicked.connect(lambda: self.set_scope("all"))
        self.cancel_btn.clicked.connect(self.reject)
        
        # Initial values
        self.rotation_degrees = None
        self.rotation_scope = None
    
    def accept_rotation(self, degrees):
        """Store the selected rotation value."""
        self.rotation_degrees = degrees
        if self.rotation_scope:
            self.accept()
    
    def set_scope(self, scope):
        """Store the scope of the rotation."""
        self.rotation_scope = scope
        if self.rotation_degrees:
            self.accept()
    
    def get_rotation_params(self):
        """Returns the selected rotation parameters."""
        return self.rotation_degrees, self.rotation_scope


class PDFRotationUIHandler(QObject):
    """    ""User interface handler for PDF rotation."""
    save_doc_signal = pyqtSignal(bool)

    def __init__(self, main_window, document_handler, secondary_pdf = None, title = "Rotate PDF"):
        super().__init__()
        """
        Initialize the UI handler for rotation.
        Args:
            main_window: Main application window (where to add UI)
            document_handler: Object that manages the current PDF document
        """
        self.main_window = main_window
        self.document_handler = document_handler
        self.secondary_pdf = secondary_pdf
        self.rotator = PDFRotator(document_handler)
        self.file_path = None
        self.original_file_path = None
        self.title = title
        self.rotate_both = False
        
        # Initialize UI elements
        self.setup_ui_elements()
    
    def setup_ui_elements(self):
        """Set up the UI elements for rotation."""
        # # Create actions
        self.rotate_action = QAction(QIcon("C:/PDF_Comparator/src/ui/icons/rotate.png"), "Rotate " + self.title , self.main_window)
        self.rotate_action.setStatusTip("Turn pages of the PDF")
        self.rotate_action.triggered.connect(self.show_rotation_dialog)
        
        # Create save action (save pdf and json with the annotations)
        self.save_action = QAction(QIcon("C:/PDF_Comparator/src/ui/icons/save.png"), "Save " + self.title, self.main_window)
        self.save_action.setStatusTip("Save the changes made to the PDF")
        self.save_action.triggered.connect(self.save_document)
        
        # Add to menu (assuming there is a 'Tools' menu)
        tools_menu = None
        for menu in self.main_window.menuBar().findChildren(QMenu):
            if menu.title() == "Rotate":
                tools_menu = menu
                break
        
        if not tools_menu:
            tools_menu = self.main_window.menuBar().addMenu("Rotate")
        
        tools_menu.addAction(self.rotate_action)
        
        # Add the save button to the File menu
        file_menu = None
        for menu in self.main_window.menuBar().findChildren(QMenu):
            if menu.title() == "File":
                file_menu = menu
                break
        
        if not file_menu:
            file_menu = self.main_window.menuBar().addMenu("File")
        
        file_menu.addAction(self.save_action)
    
    def show_rotation_dialog(self):
        """Show the rotation dialog."""
        if not self.document_handler.document:
            QMessageBox.warning(
                self.main_window,
                "Warning",
                "You must open a PDF document first.."
            )
            return
        
        # Check if we are in joint rotation mode
        dialog_title = "Rote both PDFs" if self.rotate_both else self.title
        
        dialog = RotationDialog(self.main_window, self.title)
        # Adjust message according to the mode
        if self.rotate_both:
            dialog.info_label.setText("Select the rotation for both PDFs:")
        else:
            dialog.info_label.setText(f"Select the rotation for {self.title}:")

        if dialog.exec_():
            degrees, scope = dialog.get_rotation_params()
            self.apply_rotation(degrees, scope)

    def apply_rotation(self, degrees, scope):
        """
        Apply the rotation to the document according to the parameters.
        
        Args:
            degrees: Degrees of rotation (90, 180, 270) 
            scope: Scope of rotation ('current' or 'all')
        """
        success = False
        
        #check if both PDFs need to be rotated or just one
        if self.rotate_both:
            if scope == "current":
                # Rotate only the current page
                current_page = self.secondary_pdf.document_handler.current_page
                success = self.secondary_pdf.rotator.rotate_page(current_page, degrees)
                
                #save rotation in dictionary for the json
                self.rotator.rotations_by_page[current_page] = degrees

            else:  # scope == "all pages"
                # Rotate all pages
                success = self.secondary_pdf.rotator.rotate_all_pages(degrees)
                print("Success",success)
            
            if success:
                pass
            else:
                QMessageBox.critical(
                    self.main_window,
                    "Error",
                    "The rotation could not be applied to the document."
                )

        if scope == "current":
            # Rotate only the current page
            current_page = self.document_handler.current_page
            success = self.rotator.rotate_page(current_page, degrees)

            #save rotation in dictionary for the json
            self.rotator.rotations_by_page[current_page] = degrees

        else:  # scope == "all"
            # Rotate all pages
            success = self.rotator.rotate_all_pages(degrees)
            print("Success",success)
        
        if success:
            # Update the view without saving
            if hasattr(self.document_handler, 'update_display'):
                self.document_handler.update_display()

            # Notify that there are unsaved changes
            self.mark_document_as_modified()
            
            QMessageBox.information(
                self.main_window,
                "Applied rotation",
                f"The rotation of {degrees}° it was applied correctly.\n\n"
                "Remember to save the changes with the 'Save changes' button.'."
            )
            print("Rotation applied",degrees)
        
        else:
            QMessageBox.critical(
                self.main_window,
                "Error",
                "The rotation could not be applied to the document.."
            )
    
    def set_rotate_both(self, state):
        """Update the joint rotation status."""
        self.rotate_both = state

    def save_document(self):
        """Save the document with the changes applied."""
        if not self.document_handler.document:
            QMessageBox.warning(
                self.main_window,
                "Warning",
                "There is no document open to save."
            )
            return
    
        # Ask if they want to overwrite or save as
        reply = QMessageBox.question(
            self.main_window,
            "Save changes",
            "Do you want to overwrite the original file?\n\n"
            "Select 'No' to save as a new file",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
        )
        
        if reply == QMessageBox.Cancel:
            return
        
        file_path = None
        
        if reply == QMessageBox.Yes:
            # Use the current file path
            file_path = self.document_handler.file_path
            print("Path of the current file",file_path)
            
            if not file_path:
                QMessageBox.warning(
                    self.main_window,
                    "Warning",
                    "The path of the original file is not known.."
                )
                return
        
        if reply == QMessageBox.No:
            # Save as new file
            file_path, _ = QFileDialog.getSaveFileName(
                self.main_window,
                "Save PDF as",
                "",
                "PDF files (*.pdf)"
            )
            
            if not file_path:
                return  # User canceled the dialog
        
        # Save the document (this will close the document if necessary)
        
        self.save_doc_signal.emit(True) #emit signal to update change circles
        success, current_page = self.rotator.save_document(file_path)
        
        if success:
            # Just update the reference to the file path
            self.document_handler.file_path = file_path

            # Reopen the document in the new location
            self.document_handler.document = fitz.open(file_path)

            # Restore the current page
            if self.document_handler.current_page >= len(self.document_handler.document):
                self.document_handler.current_page = 0
            
            # Update the display
            if hasattr(self.document_handler, 'load_pdf'):
                self.document_handler.load_pdf(file_path, c_page = current_page)
                self.document_handler.prev_button.setEnabled(self.document_handler.current_page > 0)
            
            # Update UI status
            self.mark_document_as_saved()
            
            QMessageBox.information(
                self.main_window,
                "Success",
                "The document was saved correctly.."
            )
        else:
            QMessageBox.critical(
                self.main_window,
                "Error",
                "the document could not be saved."
            )
    
    def mark_document_as_modified(self, doc_modified = ""):
        """Mark the document as modified in the UI."""
        # Notify the main window that the document has been modified.
        if hasattr(self.main_window, 'on_document_modified'):
            self.main_window.on_document_modified(self.title)
        
        # You could also change the window title
        import os
        filename = "No title"
        self.main_window.setWindowTitle(f"PDF Comparator - {filename} *")
    
    def mark_document_as_saved(self):
        """Mark the document as saved in the UI."""
        # Update the window title to remove the asterisk

        filename = os.path.basename(self.document_handler.file_path) if self.document_handler.file_path else "No title"
        self.main_window.setWindowTitle(f"PDF Comparator - {filename}")
        
        # Notify the main window if necessary
        if hasattr(self.main_window, 'on_document_saved'):
            self.main_window.on_document_saved()
