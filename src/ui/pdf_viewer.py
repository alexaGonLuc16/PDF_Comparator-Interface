import fitz  # PyMuPDF
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QScrollArea, QSizePolicy, QListWidget, 
                            QListWidgetItem, QFrame, QTreeWidget,QTreeWidgetItem, QToolTip, QRubberBand, QFileDialog, QSlider, QDialog, QMessageBox)
from PyQt5.QtGui import QPixmap, QImage, QKeyEvent, QColor, QBrush
from PyQt5.QtCore import Qt, QByteArray, pyqtSignal, QEvent, QPoint, QRect, QSize
from src.pdf_rotation import PDFRotationUIHandler
from math import sqrt

class OpacityDialog(QDialog):
    """Diálogo para seleccionar la opacidad de la marca de agua"""
    def __init__(self, parent=None):
        super(OpacityDialog, self).__init__(parent)
        self.setWindowTitle("Seleccionar Opacidad")
        self.opacity_value = 30  # Valor predeterminado: 30%
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Etiqueta para mostrar el valor actual
        self.opacity_label = QLabel(f"Opacidad: {self.opacity_value}%")
        layout.addWidget(self.opacity_label)
        
        # Slider para seleccionar la opacidad
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(1)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(self.opacity_value)
        self.opacity_slider.setTickPosition(QSlider.TicksBelow)
        self.opacity_slider.setTickInterval(10)
        self.opacity_slider.valueChanged.connect(self.update_opacity_label)
        layout.addWidget(self.opacity_slider)
        
        # Ejemplos predefinidos
        presets_layout = QHBoxLayout()
        presets = [(10, "Muy sutil"), (30, "Sutil"), (50, "Media"), (70, "Fuerte"), (90, "Muy fuerte")]
        
        for value, name in presets:
            preset_button = QPushButton(name)
            preset_button.clicked.connect(lambda checked, v=value: self.set_preset(v))
            presets_layout.addWidget(preset_button)
        
        layout.addLayout(presets_layout)
        
        # Botones de aceptar/cancelar
        button_layout = QHBoxLayout()
        ok_button = QPushButton("Aceptar")
        ok_button.clicked.connect(self.accept)
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def update_opacity_label(self, value):
        self.opacity_value = value
        self.opacity_label.setText(f"Opacidad: {value}%")
    
    def set_preset(self, value):
        self.opacity_slider.setValue(value)
        self.update_opacity_label(value)
    
    def get_opacity(self):
        """Devuelve el valor de opacidad como decimal (0-1)"""
        return self.opacity_value / 100.0

class ChangesListWidget(QWidget):
    change_selected = pyqtSignal(int, dict)  # Página, cambio, activado
    circle_selected = pyqtSignal(int, dict, bool)  # Página, cambio, activado   #signal to desapear a circle
    update_annotations_sig = pyqtSignal(int, list)# Página, updated annotations  #signal to desapear a circle
    change_description_edited = pyqtSignal(int, int, str)  # Página, índice, nuevo texto

    def __init__(self, parent=None):
        super(ChangesListWidget, self).__init__(parent)
        self.changes_by_page = {}
        self.setMouseTracking(True)  # Importante: habilita el seguimiento del mouse incluso sin clic
        self.formatted_circles_by_page = {}
        self.changes_description = {} #lsta con descripciones de los cambios
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Árbol para mostrar cambios de forma jerárquica
        self.changes_tree = QTreeWidget(self)
        self.changes_tree.setHeaderLabels(["Page/Difference", "State"])
        self.changes_tree.setColumnWidth(0, 150)
        self.changes_tree.itemClicked.connect(self.on_item_clicked)
        
        # Habilitar edición de elementos
        self.changes_tree.setEditTriggers(QTreeWidget.DoubleClicked | QTreeWidget.EditKeyPressed)
        self.changes_tree.itemChanged.connect(self.on_item_edited)

        #layout.addWidget(title_label)
        layout.addWidget(self.changes_tree)

    def update_page_item_color(self, page_item):
        total = page_item.childCount()
        if total == 0:
            return

        checked = sum(
            1 for i in range(total) if page_item.child(i).checkState(1) == Qt.Checked
        )

        if checked == total:
            # Todos seleccionados → negro
            page_item.setForeground(0, QBrush(QColor("black")))
        elif checked == 0:
            # Ninguno seleccionado → rojo
            page_item.setForeground(0, QBrush(QColor(220, 0, 0)))  # rojo fuerte
        else:
            # Algunos seleccionados → gris claro
            page_item.setForeground(0, QBrush(QColor(150, 150, 150)))  # gris claro

    def update_changes_list(self, formatted_circles_by_page):
        """Actualiza la lista completa de cambios por página"""
        if not hasattr(self, 'changes_tree') or self.changes_tree is None:
            print("Error: changes_tree no está inicializado")
            return

        # Guardar el estado expandido de los elementos
        expanded_states = {}
        for i in range(self.changes_tree.topLevelItemCount()):
            item = self.changes_tree.topLevelItem(i)
            data = item.data(0, 256)
            if data and "page" in data:
                expanded_states[data["page"]] = item.isExpanded()

        # Desconectar temporalmente la señal para evitar activaciones durante la actualización
        self.changes_tree.itemChanged.disconnect(self.on_item_edited)

        self.changes_tree.clear()
        self.changes_by_page = formatted_circles_by_page

        # Crear un elemento en el árbol para cada página con cambios
        for page_num, changes in sorted(formatted_circles_by_page.items()):
            self.changes_description[page_num] = changes
            if changes:
                page_item = QTreeWidgetItem(self.changes_tree)
                page_item.setText(0, f"Page {page_num + 1} ({len(changes)} differences)")
                page_item.setData(0, 256, {"type": "page", "page": page_num})
                
                # Crear sub-elementos para cada cambio en la página
                for i, change in enumerate(changes):
                    change_item = QTreeWidgetItem(page_item)
                    # Usar descripción personalizada si existe, de lo contrario usar el texto predeterminado
                    display_text = change.get("description", f"Difference {i+1}")
                    change_item.setText(0, display_text)
                    change_item.setData(0, 256, {"type": "change", "page": page_num, "index": i})
                    
                    # Hacer que el texto sea editable
                    change_item.setFlags(change_item.flags() | Qt.ItemIsEditable)
                    
                    # Agregar checkbox para activar/desactivar
                    change_item.setCheckState(1, 2 if change.get("selected", True) else 0)
        
        # Restaurar los estados de expansión
        for i in range(self.changes_tree.topLevelItemCount()):
            item = self.changes_tree.topLevelItem(i)
            data = item.data(0, 256)
            if data and "page" in data and data["page"] in expanded_states:
                item.setExpanded(expanded_states[data["page"]])
            else:
                item.setExpanded(True)  # Por defecto expandir si no hay estado guardado
        
        # Reconectar la señal
        self.changes_tree.itemChanged.connect(self.on_item_edited)
    
    def on_item_clicked(self, item, column):
        """Maneja el clic en un elemento del árbol"""
        data = item.data(0, 256)
        
        if not data:
            return
            
        if data["type"] == "change":
            page_num = data["page"]
            change_idx = data["index"]
            
            if page_num in self.changes_by_page and change_idx < len(self.changes_by_page[page_num]):
                change = self.changes_by_page[page_num][change_idx]
                
                print("Selected state: ",change["selected"])

                # Si se hizo clic en la columna del checkbox, actualizar el estado
                if column == 1:
                    # Click en checkbox
                    is_checked = item.checkState(1) == Qt.Checked
                    change["selected"] = is_checked
                    print("click en checkbox")
                    self.circle_selected.emit(page_num, change, is_checked)
                    self.update_annotations_sig.emit(page_num, self.formatted_circles_by_page[page_num])

                    # Buscar y actualizar el nodo padre de forma segura
                    for i in range(self.changes_tree.topLevelItemCount()):
                        page_item = self.changes_tree.topLevelItem(i)
                        if not page_item:
                            continue
                        page_data = page_item.data(0, 256)
                        if page_data and page_data.get("type") == "page" and page_data.get("page") == page_num:
                            self.update_page_item_color(page_item)
                            break
                else:
                    # Si se hizo clic en el nombre, navegar al cambio
                    self.change_selected.emit(page_num, change)
        
        # Si se hace clic en un elemento de página, expandir/contraer
        elif data["type"] == "page" and column == 0:
            item.setExpanded(not item.isExpanded())

    def on_item_edited(self, item, column):
        """Maneja la edición de texto de un elemento"""
        # Solo procesar ediciones en la columna 0 (texto) y para elementos de tipo "change"
        if column != 0:
            return
            
        data = item.data(0, 256)
        if not data or data["type"] != "change":
            return
            
        page_num = data["page"]
        change_idx = data["index"]
        new_text = item.text(0)
        
        print(f"Texto editado: Página {page_num}, Cambio {change_idx}, Nuevo texto: {new_text}")
        
        # Actualizar la descripción en el objeto de cambio
        if page_num in self.changes_by_page and change_idx < len(self.changes_by_page[page_num]):
            change = self.changes_by_page[page_num][change_idx]
            change["description"] = new_text
            
            # Emitir señal para notificar sobre el cambio de descripción
            self.change_description_edited.emit(page_num, change_idx, new_text)
            
            # También actualizar en el formatted_circles_by_page si existe
            if page_num in self.formatted_circles_by_page and change_idx < len(self.formatted_circles_by_page[page_num]):
                self.formatted_circles_by_page[page_num][change_idx]["description"] = new_text
                
class PDFViewer(QWidget):
    circle_clicked = pyqtSignal(int, dict,bool)  # Señal para comunicar clics
    update_annotations = pyqtSignal(int, list)  # Página, cambios
    restart_signal = pyqtSignal()  # Restart app

    def __init__(self, title="PDF Viewer"):
        super(PDFViewer, self).__init__()
        self.title = title
        self.document = None
        self.current_page = 0
        self.zoom_factor = 1.0
        self.clicks_enabled = False
        self.dpi = 300
        self.changes_list_widget = None  # Inicializar a None
        self.original_document = None # para almacenal el pdf original
        self.showing_original = False # para mostrar el pdf anotado
        self.formatted_circles_by_page = {}
        self.init_ui()
        self.setMouseTracking(True)  # Importante: habilita el seguimiento del mouse incluso sin clic
        self.page_label.setMouseTracking(True)  # También habilítalo para el label del PDF
        self.page_width = 0
        self.page_height = 0
        self.matrix = fitz.Matrix(1, 1)  # Escala 1:1, sin transformación
        self.file_path = None
        self.highlighting = False  # Indica si estamos en modo subrayado
        self.highlight_start = None  # Coordenada inicial del subrayado
        self.highlight_end = None  # Coordenada final del subrayado
        self.temp_highlight_annot = None  # Para almacenar la anotación temporal
        self.highlights_by_page = {}
        self.watermarks_by_page = {} #Alacenar las marcas de agua por pagina : {"path","opacity"}
        self.active_circle_annot = None
    
    def init_ui(self):
        # Layout principal
        layout = QVBoxLayout(self)
        
        #Boton de reinicio
        if self.title == "Annotated PDF":
            self.reload_button = QPushButton("Compare/Load new schematic")
            restart_layout = QHBoxLayout()
            
            print("Button created------------------------------")
            restart_layout.addWidget(self.reload_button, 1)
            invisible_label = QLabel("")
            restart_layout.addWidget(invisible_label, 5)
            layout.addLayout(restart_layout)
            
            self.reload_button.clicked.connect(self.confirm_restart)

        # Título
        self.title_label = QLabel(self.title)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        
        # Área de visualización del PDF
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        
        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.page_label.setMouseTracking(True)  # Habilitar seguimiento del mouse
        self.page_label.mousePressEvent = self.label_mouse_press_event  # Sobrescribir evento
        self.page_label.installEventFilter(self)  # Instalar filtro de eventos
        # Instalar filtro de eventos en el widget principal también
        self.installEventFilter(self)

        self.scroll_area.setWidget(self.page_label)

        # Controles de navegación
        nav_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(self.prev_page)
        self.prev_button.setEnabled(False)
        
        self.page_info = QLabel("Page 0 of 0")
        self.page_info.setAlignment(Qt.AlignCenter)
        
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.next_page)
        self.next_button.setEnabled(False)
        
        # Controles de zoom
        self.zoom_out_button = QPushButton("Zoom -")
        self.zoom_out_button.clicked.connect(self.zoom_out)
        
        self.zoom_in_button = QPushButton("Zoom +")
        self.zoom_in_button.clicked.connect(self.zoom_in)
        
        self.zoom_reset_button = QPushButton("100%")
        self.zoom_reset_button.clicked.connect(self.zoom_reset)
        
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.page_info)
        nav_layout.addWidget(self.next_button)
        nav_layout.addWidget(self.zoom_out_button)
        nav_layout.addWidget(self.zoom_reset_button)
        nav_layout.addWidget(self.zoom_in_button)
        
        watermark_layout = QHBoxLayout()

        self.watermark_button = QPushButton("Watermark(current page)")
        self.watermark_button.clicked.connect(self.select_watermark_image)

        self.watermark_all_button = QPushButton("Watermark(all pages)")
        self.watermark_all_button.clicked.connect(self.select_watermark_for_all_pages)


        watermark_layout.addWidget(self.watermark_button)
        watermark_layout.addWidget(self.watermark_all_button)

        layout.addWidget(self.title_label)
        layout.addWidget(self.scroll_area, 1)
        layout.addLayout(nav_layout)
        layout.addLayout(watermark_layout)  # Añadir el nuevo layout
        
        # Agregamos una lista de cambios solo si este es el visor de PDF anotado
        if "Annotated PDF" in self.title:
            print("Inicializando lista de cambios para el PDF Anotado")
            print("------------------------------------------------------------------------------------")
            self.changes_list_widget = ChangesListWidget(self)
            self.changes_list_widget.change_selected.connect(self.navigate_to_change)
            self.changes_list_widget.circle_selected.connect(self.modify_annotations) #modify annotations returns a list
            self.changes_list_widget.update_annotations_sig.connect(self.send_annotations)

    def confirm_restart(self):
        """Pide confirmación antes de emitir la señal de reinicio"""
        confirm = QMessageBox.question(
            self, 'Confirmar reinicio',
            '¿Estás seguro que quieres reiniciar la aplicación?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            self.restart_signal.emit()

    def restart(self):
        self.restart_signal.emit() 

    def send_annotations(self, page_num, updated_annotations):
        print("Printing annotations")
        self.update_annotations.emit(page_num, updated_annotations)

    def select_watermark_image(self):
        """Abre un diálogo para seleccionar una imagen y su opacidad"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Imagen para Marca de Agua", "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif);;Todos los archivos (*)", 
            options=options
        )
        
        if file_path:
            # Abrir diálogo de opacidad
            opacity_dialog = OpacityDialog(self)
            if opacity_dialog.exec_() == QDialog.Accepted:
                opacity = opacity_dialog.get_opacity()
                self.apply_watermark_image(file_path, opacity)
                self.watermarks_by_page[self.current_page] = {"path" : file_path, "opacity": opacity}

                return True
        return False
        
    def select_watermark_for_all_pages(self):
        """Abre un diálogo para seleccionar una imagen y aplicarla a todas las páginas"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Imagen para Marca de Agua (Todas las Páginas)", "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif);;Todos los archivos (*)", 
            options=options
        )
        
        if file_path:
            self.apply_watermark_to_all_pages(file_path)
            return True
        return False

    def apply_watermark_image(self, image_path, opacity=0.3):
        """Aplica la imagen seleccionada como marca de agua al PDF actual con opacidad ajustable"""
        if not self.document:
            print("No hay documento abierto para aplicar la marca de agua")
            return False
            
        try:
            # Obtener la página actual
            page = self.document[self.current_page]
            page_rect = page.rect
            
            # Crear una nueva imagen para mantener la transparencia
            # En versiones recientes de PyMuPDF podemos usar alpha directamente
            try:
                # Intenta usar el método directo con parámetro alpha (versiones recientes)
                page.insert_image(page_rect, filename=image_path, overlay=False, alpha=opacity)
            except TypeError:
                # Si la versión no soporta alpha, usamos un enfoque alternativo
                img = fitz.open(image_path)
                pix = img[0].get_pixmap(alpha=True)
                
                # Ajustar opacidad manualmente
                import numpy as np
                samples = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                if pix.alpha:  # Si la imagen tiene canal alfa
                    alpha_channel = samples[:, :, -1]
                    alpha_channel = (alpha_channel * opacity).astype(np.uint8)
                    samples[:, :, -1] = alpha_channel
                
                # Crear un nuevo pixmap con los samples modificados
                new_pix = fitz.Pixmap(pix.colorspace, pix.width, pix.height, samples.tobytes(), alpha=pix.alpha)
                page.insert_image(page_rect, pixmap=new_pix, overlay=False)
                
                # Limpiar
                img.close()
            
            # Renderizar la página actualizada
            self.render_current_page()
            print(f"Marca de agua aplicada desde: {image_path} con opacidad {opacity:.1%}")
            self.document_modified = True
            return True
        
        except Exception as e:
            print(f"Error al aplicar la marca de agua: {e}")
            return False
    
    def select_watermark_for_all_pages(self):
        """Abre un diálogo para seleccionar una imagen y aplicarla a todas las páginas con opacidad ajustable"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Imagen para Marca de Agua (Todas las Páginas)", "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif);;Todos los archivos (*)", 
            options=options
        )
        
        if file_path:
            # Abrir diálogo de opacidad
            opacity_dialog = OpacityDialog(self)
            if opacity_dialog.exec_() == QDialog.Accepted:
                opacity = opacity_dialog.get_opacity()
                self.apply_watermark_to_all_pages(file_path, opacity)
                return True
        return False
    
    def apply_watermark_to_all_pages(self, image_path, opacity=0.3):
        """Aplica la marca de agua a todas las páginas del documento con opacidad ajustable"""
        if not self.document:
            print("No hay documento abierto para aplicar la marca de agua")
            return False
            
        try:
            # Verificar si podemos usar alpha directamente
            supports_alpha = True
            try:
                # Prueba si la versión de PyMuPDF soporta alpha
                page = self.document[0]
                page.insert_image(fitz.Rect(0, 0, 1, 1), filename=image_path, overlay=False, alpha=0.5)
                # Si llegamos aquí, soporta alpha
            except TypeError:
                supports_alpha = False
            
            # Crear pixmap una sola vez para reutilizarlo (si es necesario)
            modified_pixmap = None
            if not supports_alpha:
                img = fitz.open(image_path)
                pix = img[0].get_pixmap(alpha=True)
                
                # Ajustar opacidad manualmente
                import numpy as np
                samples = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                if pix.alpha:  # Si la imagen tiene canal alfa
                    alpha_channel = samples[:, :, -1]
                    alpha_channel = (alpha_channel * opacity).astype(np.uint8)
                    samples[:, :, -1] = alpha_channel
                
                # Crear un nuevo pixmap con los samples modificados
                modified_pixmap = fitz.Pixmap(pix.colorspace, pix.width, pix.height, samples.tobytes(), alpha=pix.alpha)
                img.close()
            
            # Aplicar a todas las páginas
            for page_num in range(self.document.page_count):
                page = self.document[page_num]
                page_rect = page.rect
                
                # Insertar la imagen como marca de agua
                if supports_alpha:
                    page.insert_image(page_rect, filename=image_path, overlay=False, alpha=opacity)
                else:
                    page.insert_image(page_rect, pixmap=modified_pixmap, overlay=False)
            
            # Limpiar si fue necesario
            if modified_pixmap:
                modified_pixmap = None
            
            # Renderizar la página actual
            self.render_current_page()
            print(f"Marca de agua aplicada a todas las páginas desde: {image_path} con opacidad {opacity:.1%}")
            self.document_modified = True
            return True
        
        except Exception as e:
            print(f"Error al aplicar la marca de agua a todas las páginas: {e}")
            return False
    
    def eventFilter(self, obj, event):
        """Filtro de eventos para capturar eventos del mouse"""
        
        # Manejar movimiento de mouse durante subrayado
        if event.type() == QEvent.MouseMove and self.highlighting and self.document:
            # Si estamos arrastrando para subrayar
            if hasattr(self, 'highlight_start') and self.highlight_start:
                # Convertir coordenadas si es necesario
                if obj == self:
                    # Evento desde el label
                    adjusted_x = event.pos().x()
                    adjusted_y = event.pos().y()
                else:
                    # Evento desde el label
                    adjusted_x = event.pos().x()
                    adjusted_y = event.pos().y()
                
                # Actualizar posición final
                self.highlight_end = (adjusted_x, adjusted_y)
        
        # Manejar liberación de mouse durante subrayado
        elif event.type() == QEvent.MouseButtonRelease and self.highlighting and self.document:
            if event.button() == Qt.LeftButton and hasattr(self, 'highlight_start') and self.highlight_start:
                self.highlighting = False
                
                # Convertir coordenadas si es necesario
                if obj == self:
                    adjusted_x = event.pos().x()
                    adjusted_y = event.pos().y()
                else:
                    # Evento desde el label
                    adjusted_x = event.pos().x()
                    adjusted_y = event.pos().y()
                
                # Guardar la posición final
                self.highlight_end = (adjusted_x, adjusted_y)
                
                # Aplicar el subrayado
                self.apply_highlight()
        
        # Código existente para tooltips (solo para MouseMove)
        if obj == self.page_label and event.type() == QEvent.MouseMove:
            # Obtener posición del mouse relativa al label
            mouse_pos = event.pos()

            dpi_scale = self.dpi / 72.0  # Escala por DPI (72 es el valor base)
            zoom_scale = self.zoom_factor
            total_scale = dpi_scale / zoom_scale

            # Verificar si el documento está cargado
            if hasattr(self, 'document') and self.document:
                tooltip_text = ""
                # Si tenemos círculos en la página actual, verificar si el cursor está sobre alguno
                if hasattr(self, 'formatted_circles_by_page') and self.current_page in self.formatted_circles_by_page:
                    
                    doc_x = mouse_pos.x() * total_scale
                    doc_y = mouse_pos.y() * total_scale
                    # Verificar cada círculo en la página actual
                    for i, circle in enumerate(self.formatted_circles_by_page[self.current_page]):
                        # Calcular distancia entre el cursor y el centro del círculo
                        distance = sqrt((doc_x - circle['x'])**2 + (doc_y - circle['y'])**2)
                        
                        # Si la distancia es menor o igual al radio, el cursor está sobre el círculo
                        if distance <= circle['radius']:
                            tooltip_text = self.changes_list_widget.changes_description[self.current_page][i].get("description", f"Difference {i+1}")
                            break
                
                QToolTip.showText(event.globalPos(), tooltip_text, self.page_label)
                
        return super(PDFViewer, self).eventFilter(obj, event)

    def mouseMoveEvent(self, event):
        """Maneja el movimiento del mouse sobre el visor de PDF"""
        # Si estamos en modo subrayado
        if hasattr(self, 'highlighting') and self.highlighting and self.document and hasattr(self, 'highlight_start_pixels'):
            
            # Convertir coordenadas para el rubber band
            label_pos = self.page_label.mapFrom(self, event.pos())
            
            # Actualizar el rubber band para feedback visual
            if hasattr(self, 'highlight_overlay'):
                start_pos = QPoint(self.highlight_start_pixels[0], self.highlight_start_pixels[1])
                self.highlight_overlay.setGeometry(QRect(start_pos, label_pos).normalized())
            
            # Guardar posición final en coordenadas ajustadas para PDF
            adjusted_x = label_pos.x() + self.scroll_area.horizontalScrollBar().value()
            adjusted_y = label_pos.y() + self.scroll_area.verticalScrollBar().value()
            
            x, y = adjusted_x, adjusted_y
            self.highlight_end_pdf = (x, y)
        
        # Código existente para tooltips
        # Solo procesar si tenemos documentos cargados
        if not self.document:
            return super(PDFViewer, self).mouseMoveEvent(event)
        
        # Comprobar si el cursor está sobre el visor de PDF
        if self.page_label.underMouse():
            # Convertir coordenadas del evento a coordenadas relativas al QLabel
            label_pos = self.page_label.mapFrom(self, event.pos())

            # Ajustar por desplazamiento del ScrollArea
            adjusted_x = label_pos.x()
            adjusted_y = label_pos.y()
            
            # Mostrar un tooltip con información básica
            tooltip_text = f"Posición: X={adjusted_x}, Y={adjusted_y}\nPage: {self.current_page + 1} of {self.document.page_count}"
            
            # Añadir información sobre qué documento se está mostrando
            if hasattr(self, 'showing_original') and self.showing_original:
                tooltip_text += "\nMostrando: PDF Original"
            else:
                tooltip_text += "\nMostrando: PDF Anotado"
            
            # Mostrar el tooltip
            QToolTip.showText(event.globalPos(), tooltip_text, self)
        else:
            QToolTip.hideText()
        
        return super(PDFViewer, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Maneja el evento de soltar el botón del mouse"""
        print("mouseReleaseEvent - Botón:", event.button(), "- Highlighting:", self.highlighting)
        
        # Si estábamos subrayando y es botón izquierdo
        if self.highlighting and event.button() == Qt.LeftButton and self.document:
            print("Finalizando subrayado")
            self.highlighting = False
            
            # Ocultar el rubber band
            if hasattr(self, 'highlight_overlay'):
                self.highlight_overlay.hide()
            
            # Convertir coordenadas para el punto final
            label_pos = self.page_label.mapFrom(self, event.pos())
            print("Label_pos", label_pos)
            pos = event.pos()
            print("Event Pos", pos)
            print("Debugging scroll area")
            
            print("Vertical",self.scroll_area.verticalScrollBar().value())
            print("Horizontal",self.scroll_area.horizontalScrollBar().value())
            adjusted_x = label_pos.x() #+ self.scroll_area.horizontalScrollBar().value()
            adjusted_y = label_pos.y() #+ self.scroll_area.verticalScrollBar().value()

            x, y = adjusted_x, adjusted_y
            self.highlight_end_pdf = (x, y)
                        
            print("Highlight_start",self.highlight_start_pdf)
            print("Highlight_end",self.highlight_end_pdf)

            print(f"Final de subrayado en coords PDF: {self.highlight_end_pdf}")
            
            # Aplicar el subrayado
            self.apply_highlight()
        
        super(PDFViewer, self).mouseReleaseEvent(event)
        
    def apply_highlight(self):
        if not self.document:
            print("No hay documento cargado.")
            return
        
        if not hasattr(self, 'highlight_start_pdf') or not hasattr(self, 'highlight_end_pdf'):
            print("No hay coordenadas de subrayado.")
            return
        
        # Obtener información de la página y la transformación
        page = self.document[self.current_page]
        page_rect = page.rect  # Rectángulo de la página en coordenadas de PDF
        
        # Obtener el tamaño del pixmap actual para comprender la relación entre pantalla y PDF
        pixmap_width = self.page_label.pixmap().width()
        pixmap_height = self.page_label.pixmap().height()

        current_rotation = page.rotation
        
        #width difference
        #diff = pixmap_width / page_rect.height
        #pixmap_width = pixmap_width / diff        

        if current_rotation == 0:
            # Obtener coordenadas en píxeles
            x0, y0 = self.highlight_start_pdf
            x1, y1 = self.highlight_end_pdf
        elif current_rotation == 90:
            x0, y0 = self.highlight_start_pdf[1], page_rect.width - self.highlight_end_pdf[0] #arreglar esta coordenada x
            x1, y1 = self.highlight_end_pdf[1], page_rect.width - self.highlight_start_pdf[0] 
        elif current_rotation == 180:
            x0, y0 = page_rect.width - self.highlight_end_pdf[0], page_rect.height - self.highlight_end_pdf[1]
            x1, y1 = page_rect.width - self.highlight_start_pdf[0], page_rect.height - self.highlight_start_pdf[1]
        elif current_rotation == 270:
            x0, y0 = page_rect.height - self.highlight_end_pdf[1], self.highlight_start_pdf[0] #arreglar esta coordenada x
            x1, y1 = page_rect.height - self.highlight_start_pdf[1], self.highlight_end_pdf[0]

        print("x0",x0)
        print("y0",y0)
        print("x1",x1)
        print("y1",y1)

        # Calcular relación entre pixmap y PDF
        x_ratio = page_rect.width / pixmap_width
        y_ratio = page_rect.height / pixmap_height 
        
        # Convertir de coordenadas de pantalla a coordenadas de PDF
        pdf_x0 = x0 * x_ratio
        pdf_y0 = y0 * y_ratio
        pdf_x1 = x1 * x_ratio
        pdf_y1 = y1 * y_ratio
        
        print("x_ratio", x_ratio)
        print("y_ratio", y_ratio)

        # Crear rectángulo en coordenadas de PDF
        rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)

        new_highlight = {}
        #define dictionary
        new_highlight['x0'] = rect[0]   
        new_highlight['y0'] = rect[1]  
        new_highlight['x1'] = rect[2]  
        new_highlight['y1'] = rect[3]
        
        if self.current_page in self.highlights_by_page:  

            self.highlights_by_page[self.current_page].append(new_highlight)
            print("Anotation added: ",self.highlights_by_page[self.current_page][-1])
        else:
            self.highlights_by_page[self.current_page] = [new_highlight]
            print("Anotation added: ",self.highlights_by_page[self.current_page])
        
        #print(f"Ventana maximizada: {is_maximized}, Offset aplicado: {offset_x}")
        print(f"Coords pantalla (ajustadas): ({x0}, {y0}) a ({x1}, {y1})")
        print(f"Coords PDF: ({pdf_x0}, {pdf_y0}) a ({pdf_x1}, {pdf_y1})")
        print(f"Rectángulo PDF: {rect}")
        
        try:
            # Aplicar el subrayado
            annot = page.add_highlight_annot(rect)
            annot.set_colors(stroke=(1, 1, 0))  # Color amarillo
            annot.update()
            print("Subrayado aplicado con éxito")
        except Exception as e:
            print(f"Error al aplicar subrayado: {e}")
        
        # Limpiar las variables
        if hasattr(self, 'highlight_start_pdf'):
            del self.highlight_start_pdf
        if hasattr(self, 'highlight_end_pdf'):
            del self.highlight_end_pdf
        if hasattr(self, 'highlight_start_pixels'):
            del self.highlight_start_pixels
        
        # Renderizar la página actualizada
        self.render_current_page()
        self.document_modified = True

    def update_temp_highlight(self):
        """Actualiza el subrayado temporal mientras se arrastra el mouse"""
        if not self.document or not self.highlight_start or not self.highlight_end:
            return
        
        page = self.document[self.current_page]
        
        # Eliminar anotación temporal anterior si existe
        if self.temp_highlight_annot:
            try:
                # Verificar si la anotación todavía está vinculada a la página
                # Esto evitará el error "Annot is not bound to a page"
                if hasattr(self.temp_highlight_annot, 'parent') and self.temp_highlight_annot.parent:
                    page.delete_annot(self.temp_highlight_annot)
            except Exception as e:
                print(f"Error al eliminar anotación temporal: {e}")
            finally:
                self.temp_highlight_annot = None
        
        # Obtener coordenadas
        x0, y0 = self.highlight_start
        x1, y1 = self.highlight_end
        
        # Asegurarse que los valores están en orden
        x0, x1 = sorted([x0, x1])
        y0, y1 = sorted([y0, y1])
        
        # Crear rectángulo para el subrayado
        rect = fitz.Rect(x0, y0, x1, y1 + 10.0)
        
        try:
            # Crear anotación temporal con un estilo diferente para distinguirla
            self.temp_highlight_annot = page.add_highlight_annot(rect)
            self.temp_highlight_annot.set_colors(stroke=(0.5, 0.5, 1))  # Color azul claro
            self.temp_highlight_annot.set_opacity(0.5)  # Semi-transparente
            self.temp_highlight_annot.update()
            
            # Renderizar la página para mostrar el cambio
            self.render_current_page()
        except Exception as e:
            print(f"Error al crear anotación temporal: {e}")
            self.temp_highlight_annot = None

    def keyPressEvent(self, event):
        """Captura eventos de tecla presionada"""
        # Detectar si se presiona la tecla Q
        if event.key() == Qt.Key_Q and not event.isAutoRepeat():
            print("Tecla Q presionada - mostrando PDF original")
            self.show_pdf(is_original=True)
            return
        
        # Cancelar subrayado si se presiona Escape
        if event.key() == Qt.Key_Escape and self.highlighting:
            self.highlighting = False
            self.highlight_start = None
            self.highlight_end = None
        
        # Eliminar anotación temporal si existe
        if self.temp_highlight_annot:
            page = self.document[self.current_page]
            page.delete_annot(self.temp_highlight_annot)
            self.temp_highlight_annot = None
            self.render_current_page()
        
        # Dejar que el evento siga su procesamiento normal para otras teclas
        super(PDFViewer, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """Captura eventos de tecla liberada"""
        # Detectar si se suelta la tecla Q
        if event.key() == Qt.Key_Q and not event.isAutoRepeat():
            print("Tecla Q liberada - volviendo a PDF anotado")
            self.show_pdf(is_original=False)
            return
        
        # Dejar que el evento siga su procesamiento normal para otras teclas
        super(PDFViewer, self).keyReleaseEvent(event)

    def show_pdf(self, is_original=False):
        """Muestra el PDF original o anotado según el parámetro"""
        if not self.document or (is_original and not self.original_document):
            print("No hay documentos cargados para mostrar")
            return
            
        self.showing_original = is_original
        
        # Cambiar el título según el PDF que se está mostrando
        if hasattr(self, 'title_label'):
            if is_original:
                self.title_label.setText("Original PDF")
            else:
                self.title_label.setText("Annotated PDF")

        # Guardar la posición actual del scroll
        h_value = self.scroll_area.horizontalScrollBar().value()
        v_value = self.scroll_area.verticalScrollBar().value()
        
        # Renderizar la página correspondiente
        self.render_current_page()
        
        # Actualizar estado de los botones de navegación
        doc_to_check = self.original_document if is_original else self.document
        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled(self.current_page < doc_to_check.page_count - 1)
        
        # Restaurar la posición del scroll
        self.scroll_area.horizontalScrollBar().setValue(h_value)
        self.scroll_area.verticalScrollBar().setValue(v_value)

    def load_pdf(self, pdf_path, original_pdf_path=None, c_page = 0):
        """Carga un archivo PDF en el visor."""
        if pdf_path:
            # Cerrar documento previo si existe
            if self.document:
                self.document.close()

            # Abrir nuevo documento
            self.document = fitz.open(pdf_path)
            self.current_page = c_page
            
            #Cargar PDF original
            if original_pdf_path:
                if self.original_document:
                    self.original_document.close()
                self.original_document = fitz.open(original_pdf_path)

            # Actualizar interfaz
            self.update_page_info()
            self.render_current_page()
            
            # Habilitar/deshabilitar botones
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(self.document.page_count > 1 )

    #Añade un método para recargar el documento (útil después de una rotación):
    def reload_document(self):
        """
        Recarga el documento actual manteniendo la página actual.
        Útil después de realizar modificaciones como rotaciones.
        """
        print("Entrando a reload document")
        if not self.document:
            return
        
        # Guardar la página actual
        current_page = self.current_page
        
        # Cerrar el documento
        self.document.close()

        # Reabrir el documento
        self.document = fitz.open(self)

        # Asegurarse de que la página actual sea válida
        self.current_page = min(current_page, len(self.document) - 1)
        
        # Actualizar la visualización
        self.update_display()
        
        # Actualizar información de la página si es necesario
        self.update_page_info()

    def has_changes_list(self):
        """Verifica si este visor tiene lista de cambios"""
        return self.changes_list_widget is not None
    
    def navigate_to_change(self, page_num, change):
        """Navega a un cambio específico cuando se selecciona de la lista"""
        #print("change:", change, "--------------------->navigating to change")

        # Eliminar solo el círculo rojo anterior
        if self.active_circle_annot:
            try:
                page_of_annot = self.document[self.current_page]
                page_of_annot.delete_annot(self.active_circle_annot)
                page_of_annot.clean_contents()
                self.document.saveIncr()
            except Exception as e:
                print("Error deleting red circle:", e)
            self.active_circle_annot = None

        # Navegar a página si es necesario
        if self.current_page != page_num:
            self.current_page = page_num
            self.update_page_info()
            self.prev_button.setEnabled(self.current_page > 0)
            self.next_button.setEnabled(self.current_page < self.document.page_count - 1)

        # Zoom y render
        self.zoom_factor = 2.0
        self.render_current_page()
        self.scroll_to_change(change)

        # Agregar nuevo círculo rojo
        if self.document:
            page = self.document.load_page(page_num)
            scale_factor = 72 / self.dpi
            x_pdf = change['x'] * scale_factor
            y_pdf = change['y'] * scale_factor
            radius_pdf = change.get('radius', 20) * scale_factor

            circle_annot = page.add_circle_annot(
                (x_pdf - radius_pdf, y_pdf - radius_pdf, x_pdf + radius_pdf, y_pdf + radius_pdf)
            )
            circle_annot.set_border(width=2)
            circle_annot.set_colors(stroke=(1, 0, 0), fill=None)  # solo contorno rojo
            circle_annot.set_opacity(1.0)
            circle_annot.set_flags(0)

            self.active_circle_annot = circle_annot
            self.document.saveIncr()
            self.render_current_page()
    
    def scroll_to_change(self, change):

        dpi_scale = self.dpi / 72.0  # Escala por DPI (72 es el valor base)
        zoom_scale = self.zoom_factor
        total_scale = dpi_scale / zoom_scale

        """Desplaza la vista para centrar el cambio seleccionado"""
        if not self.document:
            return
            
        # Obtener dimensiones del pixmap actual
        if self.page_label.pixmap() is None:
            print("Error: No hay pixmap en page_label")
            return

        # Calcular la posición del cambio en el pixmap con el zoom actual
        change_x = change['x']
        change_y = change['y']
        
        #calcular scroll
        scroll_x = (change_x / self.page_width)
        scroll_y = (change_y / self.page_height)

        #scroll area dimensions
        h_scroll = self.scroll_area.horizontalScrollBar().width() + self.scroll_area.horizontalScrollBar().maximum()
        v_scroll = self.scroll_area.verticalScrollBar().height() + self.scroll_area.verticalScrollBar().maximum()

        # Ajustar el scroll para centrar el cambio
        h_value = max(0, int(h_scroll*scroll_x-self.width()/2))
        v_value = max(0, int(v_scroll*scroll_y-self.height()/2))

        # Limitar los valores de scroll a los máximos permitidos
        h_value = min(h_value, self.scroll_area.horizontalScrollBar().maximum())
        v_value = min(v_value, self.scroll_area.verticalScrollBar().maximum())

        # Establecer los valores de scroll
        self.scroll_area.horizontalScrollBar().setValue(h_value)
        self.scroll_area.verticalScrollBar().setValue(v_value)
    
    def label_mouse_press_event(self, event):
        """Maneja los clics en el label del PDF"""
        pos = event.pos()
        print("Label Press event")
        print(f"Click en QLabel (sin desplazamiento): {pos}")

        # Si es botón izquierdo y estamos en PDF anotado, iniciar subrayado
        if event.button() == Qt.LeftButton and not self.showing_original and self.document:
            print("Iniciando modo subrayado")
            self.highlighting = True
            
            # Convertir coordenadas a coordenadas del PDF
            page = self.document[self.current_page]
            
            # Guardar la posición inicial en coordenadas de píxeles para el visual feedback
            self.highlight_start_pixels = (pos.x(), pos.y())
            
            # Convertir a coordenadas del PDF
            # Nota: necesitamos ajustar por el desplazamiento del scroll
            adjusted_x = pos.x() #+ self.scroll_area.horizontalScrollBar().value()
            adjusted_y = pos.y() #+ self.scroll_area.verticalScrollBar().value()
            
            # Guardar la posición exacta en coordenadas de PDF
            x, y = adjusted_x, adjusted_y
            self.highlight_start_pdf = (x, y)
            
            print(f"Inicio de subrayado en píxeles: {self.highlight_start_pixels}")
            print(f"Inicio de subrayado en coords PDF: {self.highlight_start_pdf}")
            
            # Iniciar rubber band para feedback visual
            if not hasattr(self, 'highlight_overlay'):
                self.highlight_overlay = QRubberBand(QRubberBand.Rectangle, self.page_label)
            
            self.highlight_overlay.setGeometry(QRect(pos, QSize()))
            self.highlight_overlay.show()

        page_num, clicked_circle = self.detect_circle_click(pos)
        if clicked_circle:
            if clicked_circle["selected"]:
                new_state = False
            else:
                new_state = True
            print("Clicked circle:", clicked_circle,"------------------new state", new_state)
            self.circle_clicked.emit(page_num, clicked_circle, new_state)

    def set_clicks_enabled(self, enabled):
        #habilita o desabilita la deteccion de clicks en circulos
        self.clicks_enabled = enabled
    
    # Actualizar la visualización 
    # después de una rotación:

    def update_display(self):
        """
        Actualiza la visualización del PDF después de realizar modificaciones como rotaciones.
        """
        if not self.document or self.current_page >= len(self.document):
            return
        
        # Obtener la página actual
        page = self.document[self.current_page]
        
        # Renderizar la página nuevamente
        pix = page.get_pixmap(matrix=self.matrix)
        
        # Convertir a QImage y actualizar el QLabel
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(img)
        
        # Asumiendo que tienes un QLabel llamado image_label
        if hasattr(self, 'image_label'):
            self.page_label.setPixmap(pixmap)
        
        # Actualizar información de la página en la UI si es necesario
        self.update_page_info()

    def update_page_info(self):
        """Actualiza la información de página actual."""
        print("Ejecutando update_page_info")
        if self.document:
            self.page_info.setText(f"Page {self.current_page + 1} of {self.document.page_count}")
            
            # Actualizar la lista de cambios para la página actual (solo si existe)
            if self.has_changes_list() and hasattr(self, 'formatted_circles_by_page'):
                if self.current_page in self.formatted_circles_by_page:
                    changes = self.formatted_circles_by_page[self.current_page]
                    self.changes_list_widget.update_changes_list(self.formatted_circles_by_page)
                else:
                    self.changes_list_widget.update_changes_list(self.formatted_circles_by_page)
    
    def render_current_page(self):
        """Renderiza la página actual del PDF."""
        if not self.document:
            print("Error: No hay documento principal para renderizar")
            return
        
        # Determinar qué documento renderizar
        doc_to_render = self.original_document if self.showing_original else self.document
        
        # Verificar que el documento a renderizar existe
        if not doc_to_render:
            print("Error: No hay documento disponible para renderizar")
            return
        
        print(f"Renderizando página {self.current_page} de documento: {doc_to_render}")
        
        # Obtener página actual
        page = doc_to_render[self.current_page]
        
        # Aplicar zoom
        matrix = fitz.Matrix(self.zoom_factor, self.zoom_factor)
        pix = page.get_pixmap(matrix=matrix)
        
        print(f"Pixmap creado: {pix.width}x{pix.height}")
        
        # Convertir a QImage/QPixmap
        img_data = QByteArray(pix.samples)
        qimg = QImage(img_data, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        
        print(f"QPixmap creado: {pixmap.width()}x{pixmap.height()}")
        
        # Mostrar en el label
        self.page_label.setPixmap(pixmap)
        self.page_label.resize(pixmap.size())

    def modify_annotations(self, page_num, clicked_circle, is_checked):
        print(f"modify_annotations llamado - Página: {page_num}, Círculo: {clicked_circle}, Checked: {is_checked}")
    
        if not hasattr(self, 'formatted_circles_by_page') or page_num not in self.formatted_circles_by_page:
            print("No hay círculos formateados para esta página")
            return []

        updated_annotations = []

        for circle in self.formatted_circles_by_page[page_num]:
            # Comparar si el círculo actual es el que fue clicado
            # Es mejor comparar coordenadas específicas en lugar del objeto completo
            if (circle['x'] == clicked_circle['x'] and 
                circle['y'] == clicked_circle['y'] and 
                circle['radius'] == clicked_circle['radius']):
                
                # Modificar el círculo
                modified_circle = circle.copy()
                modified_circle["selected"] = is_checked
                updated_annotations.append(modified_circle)
                print(f"Círculo en página {page_num} modificado - Selected: {is_checked}")
            else:
                updated_annotations.append(circle)

        # Guardar los cambios en la estructura de datos
        self.formatted_circles_by_page[page_num] = updated_annotations
        self.changes_list_widget.formatted_circles_by_page[page_num] = updated_annotations
        
        # Actualizar la visualización después de la modificación
        self.reload_page()
        
        # Actualizar la lista de cambios para reflejar el nuevo estado
        if self.changes_list_widget:
            self.changes_list_widget.update_changes_list(self.formatted_circles_by_page)
            
        return updated_annotations

    def detect_circle_click(self, pos):
        if self.current_page not in self.formatted_circles_by_page:
            print("No hay círculos en esta página.")
            return None, None

        dpi_scale = self.dpi / 72.0  # Escala por DPI (72 es el valor base)
        zoom_scale = self.zoom_factor
        total_scale = dpi_scale / zoom_scale

        for circle in self.formatted_circles_by_page[self.current_page]:
            scaled_x = pos.x() * total_scale
            scaled_y = pos.y() * total_scale
            #print("circulo en x", circle['x']," - circulo en y", circle['y'])
            #print("Scaled x", scaled_x," - Scaled y", scaled_y)

            scaled_radius = circle['radius']

            # Calcular distancia real
            distance = sqrt((scaled_x - circle['x'])**2 + (scaled_y - circle['y'])**2)

            if distance <= scaled_radius:
                print("¡Click dentro del círculo!",circle)
                return self.current_page, circle
            
        print(f"Click en: {pos.x()}, {pos.y()}")
        
        print("No se hizo clic en ningún círculo.")
        return None, None

    def set_circles(self, circles_by_page, page_width, page_height, json_loaded = False):
        self.page_width = page_width
        self.page_height = page_height

        """Establece los círculos detectados por página."""
        self.circles_by_page = circles_by_page
        self.formatted_circles_by_page = {}

        if json_loaded: #cuando se cargan cambios del json
            for page, circles in circles_by_page.items():
                # Primero formatear todos los círculos
                formatted_circles = []
                for circle in circles:
                    formatted_circles.append({
                        "x": circle['x'],
                        "y": circle['y'],
                        "radius": circle['radius'],
                        "selected": ['selected'],
                    })
                # Filtrar círculos usando el método 1 (filtrado por contenimiento completo)
                filtered_circles = self.filter_contained_circles(formatted_circles)
                self.formatted_circles_by_page[page] = filtered_circles

            # Actualizar la lista de cambios si estamos en una página con cambios y si existe la lista
            if self.has_changes_list() and self.current_page in self.formatted_circles_by_page:
                self.changes_list_widget.update_changes_list(self.formatted_circles_by_page)

            self.render_current_page()
            self.update_page_info()
            return self.formatted_circles_by_page
        
        else: #cuando se hace una comparacion
            for page, circles in circles_by_page.items():
                # Primero formatear todos los círculos
                formatted_circles = []
                for circle in circles:
                    formatted_circles.append({
                        "x": circle[0],
                        "y": circle[1],
                        "radius": circle[2],
                        "selected": True,
                    })
            
                # Filtrar círculos usando el método 1 (filtrado por contenimiento completo)
                filtered_circles = self.filter_contained_circles(formatted_circles)
                self.formatted_circles_by_page[page] = filtered_circles
        
            # Actualizar la lista de cambios si estamos en una página con cambios y si existe la lista
            if self.has_changes_list() and self.current_page in self.formatted_circles_by_page:
                print("Atributo formatted_circles_by_page antes de update_changes_list",self.formatted_circles_by_page)
                self.changes_list_widget.update_changes_list(self.formatted_circles_by_page)
                print("Atributo formatted_circles_by_page despues de update_changes_list",self.formatted_circles_by_page)

            self.render_current_page()
            self.update_page_info()
            return self.formatted_circles_by_page
        
    def filter_contained_circles(self, circles):
        """
        Filtra los círculos, descartando aquellos que están contenidos en otros círculos más grandes.
        Devuelve solo los círculos "contenedores" más grandes.
        """
        if not circles:
            return []
        
        # Crear una copia para no modificar la lista original
        result = circles.copy()
        circles_to_remove = set()
        
        # Comparar cada par de círculos
        for i, circle1 in enumerate(circles):
            for j, circle2 in enumerate(circles):
                if i == j:
                    continue  # No comparar un círculo consigo mismo
                
                # Calcular la distancia entre los centros
                distance = sqrt((circle1['x'] - circle2['x'])**2 + (circle1['y'] - circle2['y'])**2)
                
                # Si la distancia es menor que la diferencia de radios, un círculo está dentro del otro
                if distance <= abs(circle1['radius'] - circle2['radius']):
                    # Determinar cuál es el círculo más pequeño (contenido)
                    if circle1['radius'] < circle2['radius']:
                        circles_to_remove.add(i)  # El círculo 1 está contenido en el 2
                    elif circle2['radius'] < circle1['radius']:
                        circles_to_remove.add(j)  # El círculo 2 está contenido en el 1
        
        # Crear una nueva lista sin los círculos contenidos
        filtered_result = [circle for i, circle in enumerate(result) if i not in circles_to_remove]
        
        print(f"Se filtraron {len(circles) - len(filtered_result)} círculos contenidos.")
        return filtered_result
    
    def reload_page(self):
        """Recarga la página actual (útil cuando cambian las anotaciones)."""
        self.render_current_page()

    def next_page(self):
        """Navega a la siguiente página."""
        if self.document and self.current_page < self.document.page_count - 1:
            self.current_page += 1
            self.render_current_page()
            self.update_page_info()
            
            # Actualizar estado de los botones
            self.prev_button.setEnabled(True)
            print("Prev button setted true")
            print("Current page:", self.current_page)
            self.next_button.setEnabled(self.current_page < self.document.page_count - 1)
    
    def prev_page(self):
        """Navega a la página anterior."""
        if self.document and self.current_page > 0:
            self.current_page -= 1
            self.render_current_page()
            self.update_page_info()
            
            # Actualizar estado de los botones
            self.prev_button.setEnabled(self.current_page > 0)
            self.next_button.setEnabled(True)
    
    def zoom_in(self):
        """Aumenta el zoom."""
        self.zoom_factor *= 1.25
        self.render_current_page()
    
    def zoom_out(self):
        """Reduce el zoom."""
        if self.zoom_factor > 1.0:
            self.zoom_factor /= 1.25
            self.render_current_page()
    
    def zoom_reset(self):
        """Restablece el zoom al 100%."""
        self.zoom_factor = 1.0
        self.render_current_page()