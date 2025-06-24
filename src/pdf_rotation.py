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
    """Clase para manejar la rotación de archivos PDF."""
    
    def __init__(self, document_handler):
        """
        Inicializa el rotador de PDF.
        Args:
            document_handler: Objeto que maneja el documento PDF actual
                             (debe tener atributos doc y current_page)
        """
        self.document_handler = document_handler
        # Nueva variable para rastrear si hay cambios sin guardar
        self.has_unsaved_changes = False
        self.temp_path = None
        self.rotations_by_page = {} #diccionario de rotacion por pagina(index , value)
        self.changes_by_page = {} #copia de los cambios(circulos) para el json
        self.highlights_by_page = {}
        self.watermarks_by_page = {} 

    def rotate_page(self, page_index, degrees):
        """
        Rota una página específica del PDF.
        
        Args:
            page_index: Índice de la página (comenzando en 0)
            degrees: Grados de rotación (90, 180, 270)
        
        Returns:
            bool: True si la rotación fue exitosa, False en caso contrario
        """
        if not self.document_handler.document:
            return False
        
        try:
            # Obtiene el valor actual de rotación
            page = self.document_handler.document[page_index]
            current_rotation = page.rotation
            
            # Calcula la nueva rotación (suma y normaliza a 0, 90, 180, 270)
            new_rotation = (current_rotation + degrees) % 360
            
            # Establece la nueva rotación para la página
            page.set_rotation(new_rotation)

            # Aplicar zoom
            matrix = fitz.Matrix(self.document_handler.zoom_factor, self.document_handler.zoom_factor)
            # Get the pixmap of the rotated page
            pix = page.get_pixmap(matrix =  matrix)

            # Convertir a QImage/QPixmap
            img_data = QByteArray(pix.samples)
            qimg = QImage(img_data, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            
            # Mostrar en el label
            self.document_handler.page_label.setPixmap(pixmap)
            self.document_handler.page_label.resize(pixmap.size())

            # Marcar que hay cambios sin guardar
            self.has_unsaved_changes = True

            return True
        except Exception as e:
            print(f"Error al rotar la página: {str(e)}")
            return False
    
    def rotate_all_pages(self, degrees):
        """
        Rota todas las páginas del PDF.
        
        Args:
            degrees: Grados de rotación (90, 180, 270)
        
        Returns:
            bool: True si la rotación fue exitosa, False en caso contrario
        """
        if not self.document_handler.document:
            return False
        
        try:
            for page_idx in range(len(self.document_handler.document)):
                self.rotate_page(page_idx, degrees)
            return True
        except Exception as e:
            print(f"Error al rotar todas las páginas: {str(e)}")
            return False
    
    def save_document(self, file_path=None):
        
        """
        Guarda el documento con las rotaciones aplicadas.
        
        Args:
            file_path: Ruta donde guardar el archivo. Si es None, 
                    se sobrescribe el archivo actual.
        
        Returns:
            bool: True si el guardado fue exitoso, False en caso contrario
        """
        if not self.document_handler.document:
            return False
        
        try:
            # Si no se proporciona ruta, usar la ruta actual del documento
            save_path = file_path or self.document_handler.file_path
            current_page = self.document_handler.current_page  # Guardar la página actual
            
            # Guardar en un archivo temporal primero
            # Crear un archivo temporal
            temp_fd, self.temp_path = tempfile.mkstemp(suffix=".pdf")

            print("Temp file",self.temp_path)
            os.close(temp_fd)
            
            doc_copy = fitz.open()
            
            for page_idx in range(len(self.document_handler.document)):
                doc_copy.insert_pdf(self.document_handler.document, from_page=page_idx, to_page=page_idx)
            
            # Guardar la copia temporal
            doc_copy.save(
                self.temp_path,
                garbage=4,  # Máxima limpieza
                deflate=True,  # Comprimir
                clean=True  # Limpiar y reducir tamaño
            )
            
            # Cerrar el documento temporal
            doc_copy.close()
    
            # Reemplazar el archivo de destino con el temporal
            shutil.copy2(self.temp_path, save_path)

            # Eliminar el archivo temporal
            os.unlink(self.temp_path)
            
            # Reiniciar la variable de cambios sin guardar
            self.has_unsaved_changes = False

            print("Path", file_path)
            #guardar archivo json
            print("Rotations by page: ", self.rotations_by_page)
            
            json_path = os.path.splitext(save_path)[0] + "_changes.json"
            print("Path para el json", json_path)

            self.save_changes_to_json(original_pdf = save_path, 
                                    formatted_circles_by_page = self.changes_by_page ,
                                    highlights_by_page = self.highlights_by_page, 
                                    rotations_by_page = self.rotations_by_page, 
                                    watermarks_by_page=self.watermarks_by_page,
                                    output_path = json_path)
            
            return True, current_page
        except Exception as e:
            print(f"Error al guardar el documento: {str(e)}")
            return False, 0
        
    def save_changes_to_json(self, original_pdf, formatted_circles_by_page = None, 
                           highlights_by_page=None, rotations_by_page=None, 
                           watermarks_by_page =None, output_path=None, dpi=300):
        print("Changes before saving to json", formatted_circles_by_page)
        """
        Guarda los cambios aplicados a un PDF en un archivo JSON.
        
        Args:
            original_pdf: Ruta al PDF original
            formatted_circles_by_page: Diccionario de cambios por página
            highlights_by_page: Diccionario de highlights por página
            rotations_by_page: Diccionario de rotaciones por página
            watermarks: Lista de marcas de agua aplicadas
            output_path: Ruta donde guardar el archivo JSON
            dpi: DPI usados para la conversión a imagen
        
        Returns:
            Ruta al archivo JSON guardado
        """
        '''
        if not output_path:
            #base_name = os.path.basename(original_pdf)
            #output_path = os.path.join(original_pdf, f"{os.path.splitext(base_name)[0]}_changes.json")
            output_path = 'C:/Users/alexgonzalez/Downloads/final_rotated1_changes.json'
        '''
        try:
            # Inicializar estructura del JSON
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
                # Agregar información de cambios por página
                for page_num, changes in formatted_circles_by_page.items():
                    # Convertir a string ya que las claves JSON deben ser strings
                    page_key = str(page_num)
                    
                    if page_key not in json_data["pages"]:
                        json_data["pages"][page_key] = {
                            "changes": [],
                            "highlights": [],
                            "rotation": 0,
                            "watermarks": watermarks_by_page or []
                        }
                    # Agregar cambios a la página

                    #changes es una lista de diccionarios

                    for change in changes:
                        change_data = {
                            "x": change['x'],
                            "y": change['y'],
                            "radius": change['radius'],
                            #"change_type": change.get("change_type", "unknown"),
                            "description": change.get("description", f"Difference {len(json_data['pages'][page_key]['changes']) + 1}"),
                            "selected": change.get("selected", True)
                        }
                        
                        json_data["pages"][page_key]["changes"].append(change_data)

            # Agregar highlights por página si están disponibles
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

            # Agregar rotaciones por página si están disponibles
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
            
            # Agregar watermarks por página si están disponibles
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

            # Guardar el JSON

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2)

            print("Json saved successfully!")
            
            return output_path
        except Exception as e:
            print(f"Error al guardar el json: {str(e)}")
            return ""
    
class RotationDialog(QDialog):
    """Diálogo para confirmar y seleccionar opciones de rotación."""
    
    def __init__(self, parent=None, title ="Rotate PDF"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(300, 150)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Etiqueta informativa
        self.info_label = QLabel("Selecciona la rotación que deseas aplicar:")
        layout.addWidget(self.info_label)
        
        # Botones de rotación
        btn_layout = QHBoxLayout()
        
        self.rotate90_btn = QPushButton("Rotate 90° ↻")
        self.rotate180_btn = QPushButton("Rotate 180° ↻↻")
        self.rotate270_btn = QPushButton("Rotate 270° ↺")
        
        btn_layout.addWidget(self.rotate90_btn)
        btn_layout.addWidget(self.rotate180_btn)
        btn_layout.addWidget(self.rotate270_btn)
        
        layout.addLayout(btn_layout)
        
        # Opción para rotar todas las páginas o solo la actual
        self.scope_layout = QHBoxLayout()
        self.current_page_btn = QPushButton("Current page")
        self.all_pages_btn = QPushButton("All pages")
        
        self.scope_layout.addWidget(self.current_page_btn)
        self.scope_layout.addWidget(self.all_pages_btn)
        
        layout.addLayout(self.scope_layout)
        
        # Botón cancelar
        self.cancel_btn = QPushButton("Cancelar")
        layout.addWidget(self.cancel_btn)
        
        self.setLayout(layout)
        
        # Conectar señales
        self.rotate90_btn.clicked.connect(lambda: self.accept_rotation(90))
        self.rotate180_btn.clicked.connect(lambda: self.accept_rotation(180))
        self.rotate270_btn.clicked.connect(lambda: self.accept_rotation(270))
        self.current_page_btn.clicked.connect(lambda: self.set_scope("current"))
        self.all_pages_btn.clicked.connect(lambda: self.set_scope("all"))
        self.cancel_btn.clicked.connect(self.reject)
        
        # Valores iniciales
        self.rotation_degrees = None
        self.rotation_scope = None
    
    def accept_rotation(self, degrees):
        """Almacena el valor de rotación seleccionado."""
        self.rotation_degrees = degrees
        if self.rotation_scope:
            self.accept()
    
    def set_scope(self, scope):
        """Almacena el alcance de la rotación."""
        self.rotation_scope = scope
        if self.rotation_degrees:
            self.accept()
    
    def get_rotation_params(self):
        """Devuelve los parámetros de rotación seleccionados."""
        return self.rotation_degrees, self.rotation_scope


class PDFRotationUIHandler(QObject):
    """Manejador de la interfaz de usuario para la rotación de PDF."""
    save_doc_signal = pyqtSignal(bool)  # Señal para comunicar clics

    def __init__(self, main_window, document_handler, secondary_pdf = None, title = "Rotate PDF"):
        super().__init__()
        """
        Inicializa el manejador de UI para rotación.
        
        Args:
            main_window: Ventana principal de la aplicación (donde añadir UI)
            document_handler: Objeto que maneja el documento PDF actual
        """
        self.main_window = main_window
        self.document_handler = document_handler
        self.secondary_pdf = secondary_pdf
        self.rotator = PDFRotator(document_handler)
        self.file_path = None
        self.original_file_path = None
        self.title = title
        self.rotate_both = False
        
        # Inicializar elementos de UI
        self.setup_ui_elements()
    
    def setup_ui_elements(self):
        """Configura los elementos de UI para la rotación."""
        # Crear acciones
        self.rotate_action = QAction(QIcon("C:/PDF_Comparator/src/ui/icons/rotate.png"), "Rotate " + self.title , self.main_window)
        self.rotate_action.setStatusTip("Rotar páginas del PDF")
        self.rotate_action.triggered.connect(self.show_rotation_dialog)
        
        # Crear acción de guardar (guardar pdf y json con las anotaciones)
        self.save_action = QAction(QIcon("C:/PDF_Comparator/src/ui/icons/save.png"), "Save " + self.title, self.main_window)
        self.save_action.setStatusTip("Guardar los cambios realizados al PDF")
        self.save_action.triggered.connect(self.save_document)
        
        # Añadir a menú (asumiendo que existe un menú 'Herramientas')
        # Si no existe, necesitarías crear el menú primero

        tools_menu = None
        for menu in self.main_window.menuBar().findChildren(QMenu):
            if menu.title() == "Rotate":
                tools_menu = menu
                break
        
        if not tools_menu:
            tools_menu = self.main_window.menuBar().addMenu("Rotate")
        
        tools_menu.addAction(self.rotate_action)
        
        # Añadir el botón de guardar al menú Archivo
        file_menu = None
        for menu in self.main_window.menuBar().findChildren(QMenu):
            if menu.title() == "File":
                file_menu = menu
                break
        
        if not file_menu:
            file_menu = self.main_window.menuBar().addMenu("File")
        
        file_menu.addAction(self.save_action)
        
        # Añadir a la barra de herramientas
        # Asumiendo que existe una barra de herramientas
        #toolbar = self.main_window.findChild(QToolBar)
        #if toolbar:
        #    toolbar.addAction(self.rotate_action)
        #else:
            # Crear una barra de herramientas si no existe
        #    toolbar = self.main_window.addToolBar("Principal")
        #    toolbar.addAction(self.rotate_action)
    
    def show_rotation_dialog(self):
        """Muestra el diálogo de rotación."""
        if not self.document_handler.document:
            QMessageBox.warning(
                self.main_window,
                "Advertencia",
                "Debes abrir un documento PDF primero."
            )
            return
        
        # Verificar si estamos en modo de rotación conjunta
        dialog_title = "Rotar ambos PDFs" if self.rotate_both else self.title
        
        dialog = RotationDialog(self.main_window, self.title)
        # Ajustar mensaje según el modo
        if self.rotate_both:
            dialog.info_label.setText("Selecciona la rotación para ambos PDFs:")
        else:
            dialog.info_label.setText(f"Selecciona la rotación para {self.title}:")

        if dialog.exec_():
            degrees, scope = dialog.get_rotation_params()
            self.apply_rotation(degrees, scope)

    def apply_rotation(self, degrees, scope):
        """
        Aplica la rotación al documento según los parámetros.
        
        Args:
            degrees: Grados de rotación (90, 180, 270)
            scope: Alcance de la rotación ('current' o 'all')
        """
        success = False
        
        #revisar si hay que rotar ambos pdf o solo 1
        if self.rotate_both:
            if scope == "current":
                # Rotar solo la página actual
                current_page = self.secondary_pdf.document_handler.current_page
                success = self.secondary_pdf.rotator.rotate_page(current_page, degrees)
                
                #guardar rotacion en diccionario para el json
                self.rotator.rotations_by_page[current_page] = degrees

            else:  # scope == "all"
                # Rotar todas las páginas
                success = self.secondary_pdf.rotator.rotate_all_pages(degrees)
                print("Success",success)
            
            if success:
                pass
            else:
                QMessageBox.critical(
                    self.main_window,
                    "Error",
                    "No se pudo aplicar la rotación al documento."
                )

        if scope == "current":
            # Rotar solo la página actual
            current_page = self.document_handler.current_page
            success = self.rotator.rotate_page(current_page, degrees)

            #guardar rotacion en diccionario para el json
            self.rotator.rotations_by_page[current_page] = degrees

        else:  # scope == "all"
            # Rotar todas las páginas
            success = self.rotator.rotate_all_pages(degrees)
            print("Success",success)
        
        if success:
            # Actualizar la visualización sin guardar
            if hasattr(self.document_handler, 'update_display'):
                self.document_handler.update_display()

            # Notificar que hay cambios sin guardar
            self.mark_document_as_modified()
            
            QMessageBox.information(
                self.main_window,
                "Rotación aplicada",
                f"La rotación de {degrees}° se aplicó correctamente.\n\n"
                "Recuerda guardar los cambios con el botón 'Guardar cambios'."
            )
            print("Rotacion realizada",degrees)
        
        else:
            QMessageBox.critical(
                self.main_window,
                "Error",
                "No se pudo aplicar la rotación al documento."
            )
    
    def set_rotate_both(self, state):
        """Actualiza el estado de rotación conjunta."""
        self.rotate_both = state

    def save_document(self):
        """Guarda el documento con los cambios aplicados."""
        if not self.document_handler.document:
            QMessageBox.warning(
                self.main_window,
                "Advertencia",
                "No hay documento abierto para guardar."
            )
            return
        
        #if not self.rotator.has_unsaved_changes:
        #    QMessageBox.information(
        #        self.main_window,
        #        "Información",
        #        "No hay cambios pendientes para guardar."
        #    )
        #    return
        
        # Preguntar si quiere sobrescribir o guardar como
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
            # Usar la ruta del archivo actual
            file_path = self.document_handler.file_path
            print("Ruta del archivo actual",file_path)
            
            if not file_path:
                QMessageBox.warning(
                    self.main_window,
                    "Advertencia",
                    "No se conoce la ruta del archivo original."
                )
                return
        
        if reply == QMessageBox.No:
            # Guardar como nuevo archivo
            file_path, _ = QFileDialog.getSaveFileName(
                self.main_window,
                "Guardar PDF como",
                "",
                "Archivos PDF (*.pdf)"
            )
            
            if not file_path:
                return  # Usuario canceló el diálogo
        
        # Guardar el documento (esto cerrará el documento si es necesario)
        
        self.save_doc_signal.emit(True) #emitir senal para actualizar circulos de cambios
        success, current_page = self.rotator.save_document(file_path)
        
        if success:
            # Importante: No intentar actualizar la visualización aquí
            # porque es responsabilidad del rotator reabrir el documento
            
            # Solo actualizar la referencia a la ruta del archivo
            self.document_handler.file_path = file_path

            # Reabrir el documento en la nueva ubicación
            self.document_handler.document = fitz.open(file_path)

            # Restaurar la página actual
            if self.document_handler.current_page >= len(self.document_handler.document):
                self.document_handler.current_page = 0
            
            # Actualizar la visualización
            if hasattr(self.document_handler, 'load_pdf'):
                self.document_handler.load_pdf(file_path, c_page = current_page)
                self.document_handler.prev_button.setEnabled(self.document_handler.current_page > 0)
            
            # Actualizar estado de la UI
            self.mark_document_as_saved()
            
            QMessageBox.information(
                self.main_window,
                "Éxito",
                "El documento se guardó correctamente."
            )
        else:
            QMessageBox.critical(
                self.main_window,
                "Error",
                "No se pudo guardar el documento."
            )
    
    def mark_document_as_modified(self, doc_modified = ""):
        """Marca el documento como modificado en la UI."""
        # Notificar a la ventana principal que el documento ha sido modificado
        if hasattr(self.main_window, 'on_document_modified'):
            self.main_window.on_document_modified(self.title)
        
        # También podrías cambiar el título de la ventana
        import os
        filename = "Sin título"
        self.main_window.setWindowTitle(f"PDF Comparator - {filename} *")
    
    def mark_document_as_saved(self):
        """Marca el documento como guardado en la UI."""
        # Actualizar el título de la ventana para quitar el asterisco

        filename = os.path.basename(self.document_handler.file_path) if self.document_handler.file_path else "Sin título"
        self.main_window.setWindowTitle(f"PDF Comparator - {filename}")
        
        # Notificar a la ventana principal si es necesario
        if hasattr(self.main_window, 'on_document_saved'):
            self.main_window.on_document_saved()
