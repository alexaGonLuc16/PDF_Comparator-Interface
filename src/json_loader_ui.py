# Implementación de la sección de carga de JSON en la interfaz de usuario

from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                           QFileDialog, QFrame, QMessageBox, QDialog, QSplitter,
                           QWidget, QTabWidget)
from PyQt5.QtCore import Qt, pyqtSignal
import os

from src.json_loader import PDFJsonLoader
from src.json_saver import PDFJsonSaver

class JsonLoaderUI(QWidget):
    add_changes_list = pyqtSignal(str, dict, bool)  # ruta de archivo, diccionario de cambios
    update_changes_list_signal = pyqtSignal(dict)  # diccionario de cambios
    """
    Widget para cargar cambios desde un archivo JSON.
    """
    def __init__(self, pdf_viewer, parent=None):
        super(JsonLoaderUI, self).__init__(parent)
        self.pdf_viewer = pdf_viewer
        self.json_loader = PDFJsonLoader()
        self.json_saver = PDFJsonSaver()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Título
        title_label = QLabel("Load Changes")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Sección de carga
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
        
        # Estado de carga
        self.load_status_label = QLabel("No files loaded")
        layout.addWidget(self.load_status_label)
        
        # Separador
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator2)
        
        # Sección de guardado
        save_section_label = QLabel("Save changes to JSON")
        save_section_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(save_section_label)
        
        save_layout = QHBoxLayout()
        
        self.save_json_button = QPushButton("Save changes")
        self.save_json_button.clicked.connect(self.save_changes)
        
        save_layout.addWidget(self.save_json_button)
        
        layout.addLayout(save_layout)
        
        # Información
        info_label = QLabel(
            "Esta funcionalidad permite guardar y cargar cambios detectados en PDFs "
            "sin necesidad de reprocesarlos nuevamente."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-style: italic;")
        layout.addWidget(info_label)
        
        # Variables para seguimiento
        self.json_path = None
        self.pdf_path = None
    
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
            if self.json_loader.load_json(file_path):
                self.json_path = file_path
                self.update_load_status()
                
                # Habilitar botón de aplicar si también hay PDF cargado
                if self.pdf_path:
                    self.apply_changes_button.setEnabled(True)
                
                QMessageBox.information(self, "JSON Cargado", 
                                      f"Archivo JSON cargado correctamente: {os.path.basename(file_path)}")
            else:
                QMessageBox.warning(self, "Error de Carga", 
                                  "No se pudo cargar el archivo JSON. Verifique que tenga el formato correcto.")
    
    def load_pdf_file(self):
        """Carga un archivo PDF al que se aplicarán los cambios."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Archivo PDF", "",
            "Archivos PDF (*.pdf);;Todos los archivos (*)", 
            options=options
        )
        
        if file_path:
            self.pdf_path = file_path
            self.update_load_status()
            
            # Habilitar botón de aplicar si también hay JSON cargado
            if self.json_path:
                self.apply_changes_button.setEnabled(True)
            
            QMessageBox.information(self, "PDF Cargado", 
                                  f"Archivo PDF cargado correctamente: {os.path.basename(file_path)}")
    
    def apply_changes(self):
        """Aplica los cambios del JSON al PDF y muestra el resultado."""
        if not self.json_path or not self.pdf_path:
            QMessageBox.warning(self, "Error", "Debe cargar tanto un archivo JSON como un PDF.")
            return
        
        try:
            # Generar nombre de salida
            base_name = os.path.basename(self.pdf_path)
            output_path = f"loaded_{base_name}"
            
            # Aplicar cambios
            result_path = self.json_loader.apply_changes_to_pdf(self.pdf_path, output_path)

            if result_path != None:
                # Extraer cambios para mostrar en el visor
                changes_by_page = self.json_loader.extract_changes_by_page()
                
                # Convertir de formato de diccionario a formato de lista si es necesario
                formatted_changes = {}
                for page_num, changes in changes_by_page.items():
                    formatted_changes[page_num] = changes
                
                # Obtener dimensiones del PDF (hardcodeamos valores para el ejemplo)
                # En una implementación real, deberías obtener esto del PDF
                page_width = 612  # Ancho estándar de una página A4 en puntos
                page_height = 792  # Alto estándar de una página A4 en puntos
                
                # Cargar PDF en el visor
                self.pdf_viewer.load_pdf(result_path)
                
                # Configurar círculos
                self.add_changes_list.emit(result_path, formatted_changes, True)
                self.update_changes_list_signal.emit(formatted_changes)

                #Agregar changes list widget a la ventana principal
                QMessageBox.information(self, "Cambios Aplicados", 
                                      "Los cambios han sido aplicados correctamente al PDF.")

            else:
                QMessageBox.warning(self, "Error", "No se pudieron aplicar los cambios al PDF.")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al aplicar cambios: {str(e)}")

    def save_changes(self):
        """Guarda los cambios actuales en un archivo JSON."""
        if not hasattr(self.pdf_viewer, 'formatted_circles_by_page') or not self.pdf_viewer.formatted_circles_by_page:
            QMessageBox.warning(self, "Error", "No hay cambios para guardar.")
            return
        
        if not hasattr(self.pdf_viewer, 'file_path') or not self.pdf_viewer.file_path:
            QMessageBox.warning(self, "Error", "No hay un PDF cargado.")
            return
        
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Cambios en JSON", "",
            "Archivos JSON (*.json);;Todos los archivos (*)", 
            options=options
        )
        
        if file_path:
            try:
                # Extraer highlights si es posible
                highlights_by_page = None
                if hasattr(self.pdf_viewer, 'document') and self.pdf_viewer.document:
                    highlights_by_page = self.json_saver.extract_highlights_from_pdf(
                        self.pdf_viewer.document, self.pdf_viewer.dpi)
                
                # Extraer rotaciones si es posible
                rotations_by_page = None
                if hasattr(self.pdf_viewer, 'document') and self.pdf_viewer.document:
                    rotations_by_page = self.json_saver.extract_rotations_from_pdf(
                        self.pdf_viewer.document)
                
                # No tenemos información de marcas de agua, así que pasamos None
                watermarks = None
                
                # Guardar cambios
                result_path = self.json_saver.save_changes_to_json(
                    self.pdf_viewer.file_path,
                    self.pdf_viewer.formatted_circles_by_page,
                    highlights_by_page,
                    rotations_by_page,
                    watermarks,
                    file_path,
                    self.pdf_viewer.dpi
                )
                
                QMessageBox.information(self, "Cambios Guardados", 
                                      f"Los cambios han sido guardados en: {result_path}")
            
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al guardar cambios: {str(e)}")
    
    def update_load_status(self):
        """Actualiza la etiqueta de estado de carga."""
        status = []
        
        if self.json_path:
            status.append(f"JSON: {os.path.basename(self.json_path)}")
        
        if self.pdf_path:
            status.append(f"PDF: {os.path.basename(self.pdf_path)}")
        
        if status:
            self.load_status_label.setText("Archivos cargados: " + ", ".join(status))
        else:
            self.load_status_label.setText("No hay archivos cargados")
