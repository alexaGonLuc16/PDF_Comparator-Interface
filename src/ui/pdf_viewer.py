import fitz  # PyMuPDF
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QScrollArea, QSizePolicy, QListWidget, 
                            QListWidgetItem, QFrame, QTreeWidget,QTreeWidgetItem, QToolTip, QRubberBand, QFileDialog, QSlider, QDialog, QMessageBox, QGraphicsDropShadowEffect)
from PyQt5.QtGui import QPixmap, QImage, QKeyEvent, QColor, QBrush
from PyQt5.QtCore import Qt, QByteArray, pyqtSignal, QEvent, QPoint, QRect, QSize
from src.pdf_rotation import PDFRotationUIHandler
from PyQt5.QtGui import QColor
from math import sqrt
import inspect

class OpacityDialog(QDialog):
    """Dialogue to select the opacity of the watermark"""
    def __init__(self, parent=None):
        super(OpacityDialog, self).__init__(parent)
        self.setWindowTitle("Select Opacity")
        self.opacity_value = 30  # Default value: 30%
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Label to show the current value
        self.opacity_label = QLabel(f"Opacity: {self.opacity_value}%")
        layout.addWidget(self.opacity_label)
        
        # Slider to select the opacity
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(1)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(self.opacity_value)
        self.opacity_slider.setTickPosition(QSlider.TicksBelow)
        self.opacity_slider.setTickInterval(10)
        self.opacity_slider.valueChanged.connect(self.update_opacity_label)
        layout.addWidget(self.opacity_slider)
        
        # Predefined examples
        presets_layout = QHBoxLayout()
        presets = [(10, "Very subtle"), (30, "Subtle"), (50, "Medium"), (70, "Strong"), (90, "Very strong")]
        
        for value, name in presets:
            preset_button = QPushButton(name)
            preset_button.clicked.connect(lambda checked, v=value: self.set_preset(v))
            presets_layout.addWidget(preset_button)
        
        layout.addLayout(presets_layout)
        
        # Botones de aceptar/cancelar
        button_layout = QHBoxLayout()
        ok_button = QPushButton("Accept")
        ok_button.clicked.connect(self.accept)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def update_opacity_label(self, value):
        self.opacity_value = value
        self.opacity_label.setText(f"Opacity: {value}%")
    
    def set_preset(self, value):
        self.opacity_slider.setValue(value)
        self.update_opacity_label(value)
    
    def get_opacity(self):
        """Returns the value of opacity as a decimal (0-1)"""
        return self.opacity_value / 100.0

class ChangesListWidget(QWidget):
    change_selected = pyqtSignal(int, dict)  # # Page, change, activated
    circle_selected = pyqtSignal(int, dict, bool)  # Page, change, activated   #signal to desapear a circle
    update_annotations_sig = pyqtSignal(int, list)# Page, updated annotations  #signal to desapear a circle
    change_description_edited = pyqtSignal(int, int, str)  # Page, index, new text

    def __init__(self, parent=None):
        super(ChangesListWidget, self).__init__(parent)
        self.changes_by_page = {}
        self.setMouseTracking(True)  # Important: enable mouse tracking even without a click
        self.formatted_circles_by_page = {}
        self.changes_description = {} #list with descriptions of the changes
        self.init_ui()
        
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.changes_tree = QTreeWidget(self)
        self.changes_tree.setHeaderLabels(["Page/Difference", "State"])
        self.changes_tree.setColumnWidth(0, 150)
        self.changes_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        from PyQt5.QtWidgets import QHeaderView
        self.changes_tree.header().setStretchLastSection(False)
        self.changes_tree.header().setSectionResizeMode(0, QHeaderView.Interactive)
        self.changes_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)

        self.changes_tree.setEditTriggers(QTreeWidget.DoubleClicked | QTreeWidget.EditKeyPressed)
        self.changes_tree.itemClicked.connect(self.on_item_clicked)
        self.changes_tree.itemChanged.connect(self.on_item_edited)

        self.changes_tree.setVisible(False) 
        layout.addWidget(self.changes_tree)

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setMaximumWidth(300)

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
        """Update the complete list of changes by page"""
        if not hasattr(self, 'changes_tree') or self.changes_tree is None:
            print("Error: changes_tree not initialized")
            return

        # Save the expanded state of the elements
        expanded_states = {}
        for i in range(self.changes_tree.topLevelItemCount()):
            item = self.changes_tree.topLevelItem(i)
            data = item.data(0, 256)
            if data and "page" in data:
                expanded_states[data["page"]] = item.isExpanded()

        # Temporarily disconnect the signal to avoid activations during the update.
        try:
            self.changes_tree.itemChanged.disconnect(self.on_item_edited)
        except TypeError:
            pass  # He was no longer connected, we ignored him.

        self.changes_tree.clear()
        if not formatted_circles_by_page:
            # Reinsert the placeholder
            placeholder = QTreeWidgetItem(self.changes_tree)
            placeholder.setText(0, "No differences found.")
            placeholder.setFlags(Qt.ItemIsEnabled)
            placeholder.setFirstColumnSpanned(True)
            placeholder.setForeground(0, QBrush(QColor("gray")))
            return

        self.changes_by_page = formatted_circles_by_page

        # Create an element in the tree for each page with changes
        for page_num, changes in sorted(formatted_circles_by_page.items()):
            self.changes_description[page_num] = changes
            if changes:
                page_item = QTreeWidgetItem(self.changes_tree)
                page_item.setText(0, f"Page {page_num + 1} ({len(changes)} differences)")
                page_item.setData(0, 256, {"type": "page", "page": page_num})
                
                # Create sub-elements for each change on the page
                for i, change in enumerate(changes):
                    change_item = QTreeWidgetItem(page_item)
                    # Use custom description if it exists, otherwise use the default text.
                    display_text = change.get("description", f"Difference {i+1}")
                    change_item.setText(0, display_text)
                    change_item.setData(0, 256, {"type": "change", "page": page_num, "index": i})
                    
                    # Make the text editable
                    change_item.setFlags(change_item.flags() | Qt.ItemIsEditable)
                    
                    # Add checkbox to enable/disable
                    change_item.setCheckState(1, 2 if change.get("selected", True) else 0)
        
        # Restore the states of expansion
        for i in range(self.changes_tree.topLevelItemCount()):
            item = self.changes_tree.topLevelItem(i)
            data = item.data(0, 256)
            if data and "page" in data and data["page"] in expanded_states:
                item.setExpanded(expanded_states[data["page"]])
            else:
                item.setExpanded(True)  # Expand by default if there is no saved state
        
        # Reconnect the signal
        self.changes_tree.itemChanged.connect(self.on_item_edited)
        self.changes_tree.setVisible(True)
    
    def on_item_clicked(self, item, column):
        """Handle the click on an element of the tree"""
        data = item.data(0, 256)
        
        if not data:
            return
            
        if data["type"] == "change":
            page_num = data["page"]
            change_idx = data["index"]
            
            if page_num in self.changes_by_page and change_idx < len(self.changes_by_page[page_num]):
                change = self.changes_by_page[page_num][change_idx]
                
                #print("Selected state: ",change["selected"])

                # If the checkbox column was clicked, update the status.
                if column == 1:
                    # Click on checkbox
                    is_checked = item.checkState(1) == Qt.Checked
                    change["selected"] = is_checked
                    self.circle_selected.emit(page_num, change, is_checked)
                    self.update_annotations_sig.emit(page_num, self.formatted_circles_by_page[page_num])

                    # Safely find and update the parent node
                    for i in range(self.changes_tree.topLevelItemCount()):
                        page_item = self.changes_tree.topLevelItem(i)
                        if not page_item:
                            continue
                        page_data = page_item.data(0, 256)
                        if page_data and page_data.get("type") == "page" and page_data.get("page") == page_num:
                            self.update_page_item_color(page_item)
                            break
                else:
                    # If the name was clicked, navigate to the change.
                    self.change_selected.emit(page_num, change)
        
        # If you click on a page element, expand/collapse
        elif data["type"] == "page" and column == 0:
            item.setExpanded(not item.isExpanded())

    def on_item_edited(self, item, column):
        """Manage the text editing of an element"""
        # Only process edits in column 0 (text) and for items of type 'change'.
        if column != 0:
            return
            
        data = item.data(0, 256)
        if not data or data["type"] != "change":
            return
            
        page_num = data["page"]
        change_idx = data["index"]
        new_text = item.text(0)
        
        print(f"Edited text: Page {page_num}, Change {change_idx}, New text: {new_text}")
        
        # Update the description in the change object
        if page_num in self.changes_by_page and change_idx < len(self.changes_by_page[page_num]):
            change = self.changes_by_page[page_num][change_idx]
            change["description"] = new_text
            
            # Send a signal to notify about the change in description
            self.change_description_edited.emit(page_num, change_idx, new_text)
            
            # Also update in the formatted_circles_by_page if it exists.
            if page_num in self.formatted_circles_by_page and change_idx < len(self.formatted_circles_by_page[page_num]):
                self.formatted_circles_by_page[page_num][change_idx]["description"] = new_text
                
    
class PDFViewer(QWidget):
    circle_clicked = pyqtSignal(int, dict,bool)  # Signal to communicate clicks
    update_annotations = pyqtSignal(int, list)  # Page, changes
    restart_signal = pyqtSignal()  # Restart app

    def __init__(self, title="PDF Viewer", other_visor = None): #pass the other pdf visor
        super(PDFViewer, self).__init__()
        self.title = title
        self.document = None
        self.current_page = 0
        self.zoom_factor = 1.0
        self.clicks_enabled = False
        self.dpi = 300
        self.changes_list_widget = None  # Initialize as None

        self.original_document = None # store the original pdf
        self.showing_original = False # show the annotated pdf
        self.formatted_circles_by_page = {}
        self.init_ui()
        self.setMouseTracking(True)  # Important: enable mouse tracking even without a click
        self.page_label.setMouseTracking(True)  # Also enable it for the PDF label
        self.page_width = 0
        self.page_height = 0
        self.matrix = fitz.Matrix(1, 1)  # Scale 1:1, without transformation
        self.file_path = None
        self.highlighting = False  # Indicate if we are in underline mode
        self.highlight_start = None  # Initial coordinate of the underlining
        self.highlight_end = None  # Final coordinate of the underlining
        self.temp_highlight_annot = None  # To store the timestamp annotation
        self.highlights_by_page = {}
        self.watermarks_by_page = {} # Remove the watermarks per page: {"path","opacity"}
        self.active_circle_annot = None
        self.drag_mode = False
        self.dragging = False
        self.last_drag_pos = QPoint()
        self.page_label.mousePressEvent = self.label_mouse_press_event
        self.page_label.mouseMoveEvent = self.label_mouse_move_event
        self.other_visor = other_visor
        print("Other visor", other_visor)
    
    def init_ui(self):
        # Main Layout
        layout = QVBoxLayout(self)
        
        #Restart Button
        if self.title == "Annotated PDF":
            self.reload_button = QPushButton("Compare new schematic")
            restart_layout = QHBoxLayout()
            self.reload_button.setStyleSheet("""
                QPushButton {
                    background-color: #d9ecfa;
                    border: 1px solid #90c8f0;
                }
                QPushButton:pressed {
                    background-color: #c0e0f8;
                    border: 1px solid #70b9ec;
                }
            """)
            
            restart_layout.addWidget(self.reload_button, 1)
            invisible_label = QLabel("")
            restart_layout.addWidget(invisible_label, 3)
            layout.addLayout(restart_layout)
            
            self.reload_button.clicked.connect(self.confirm_restart)

            #create panning button 
            self.drag_button = QPushButton("Enable Pan Tool")
            panning_layout = QHBoxLayout()
            self.drag_button.setCheckable(True)
            self.drag_button.toggled.connect(self.toggle_drag_mode)
            panning_layout.addWidget(self.drag_button, 1)
            invisible_label_2 = QLabel("")
            panning_layout.addWidget(invisible_label_2, 5)
            layout.addLayout(panning_layout)  # Adjust according to your layout

        # Title
        self.title_label = QLabel(self.title)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        
        # PDF viewing area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        print("Scroll area de", self.title, "inicializado")
        
        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.page_label.setMouseTracking(True)  # Enable mouse tracking
        self.page_label.mousePressEvent = self.label_mouse_press_event  # Overwrite event
        self.page_label.installEventFilter(self)  # Install event filter
        # Install event filter in the main widget as well
        self.installEventFilter(self)

        self.scroll_area.setWidget(self.page_label)

        # Navigation controls
        nav_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(self.prev_page)
        self.prev_button.setEnabled(False)
        
        self.page_info = QLabel("Page 0 of 0")
        self.page_info.setAlignment(Qt.AlignCenter)
        
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.next_page)
        self.next_button.setEnabled(False)
        
        # Zoom controls
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
        layout.addLayout(watermark_layout)  # Add new layout
        
        # We add a list of changes only if this is the annotated PDF viewer.
        if "Annotated PDF" in self.title:
            print("Initializing change list for the Annotated PDF")
            print("------------------------------------------------------------------------------------")
            self.changes_list_widget = ChangesListWidget(self)
            self.changes_list_widget.setStyleSheet("""
                ChangesListWidget {
                    background-color: #f0f4f8; /* Interior color different from the global background */
                    border: 1px solid #dcdcdc;
                    border-radius: 10px;
                    padding: 10px;
                }
                QTreeWidget {
                    background-color: #ffffff;
                    border-radius: 6px;
                    border: 1px solid #e0e0e0;
                }           
            """
            )
            self.apply_shadow(self.changes_list_widget)
            self.changes_list_widget.change_selected.connect(self.navigate_to_change)
            self.changes_list_widget.circle_selected.connect(self.modify_annotations) #modify annotations returns a list
            self.changes_list_widget.update_annotations_sig.connect(self.send_annotations)

    def label_mouse_move_event(self, event):
        
        if self.drag_mode and self.dragging:
            delta = event.globalPos() - self.last_drag_pos
            self.last_drag_pos = event.globalPos()

            # Scroll of the active viewer
            h_scroll = self.scroll_area.horizontalScrollBar()
            v_scroll = self.scroll_area.verticalScrollBar()

            h_scroll.setValue(h_scroll.value() - delta.x())
            v_scroll.setValue(v_scroll.value() - delta.y())

            # Scroll of the synchronized viewer
            if self.other_visor and hasattr(self.other_visor, 'scroll_area') and self.title == "Annotated PDF":
                print("Setting sincronized values-------------------------")
                print("Tipo real", self.other_visor.scroll_area)
                print("Attributes",dir(self.other_visor.scroll_area))

                other_h = self.other_visor.scroll_area.horizontalScrollBar()
                other_v = self.other_visor.scroll_area.verticalScrollBar()

                other_h.setValue(other_h.value() - delta.x())
                other_v.setValue(other_v.value() - delta.y())

            return

    def toggle_drag_mode(self, checked):
        print("Drag_state",checked)
        self.drag_mode = checked
        if checked:
            self.drag_button.setText("Disable Pan Tool")
            self.highlighting = False
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.drag_mode = False
            self.drag_button.setText("Enable Pan Tool")
            self.setCursor(Qt.ArrowCursor)
    
    def confirm_restart(self):
        """Request confirmation before issuing the restart signal."""
        confirm = QMessageBox.question(
            self, 'Confirm restart',
            'Are you sure you want to restart the application?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            self.original_document.close()
            self.document.close()
            self.restart_signal.emit()

    def restart(self):
        self.restart_signal.emit() 

    def send_annotations(self, page_num, updated_annotations):
        print("Printing annotations")
        self.update_annotations.emit(page_num, updated_annotations)

    def select_watermark_image(self):
        """Open a dialog to select an image and its opacity"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select the Watermark image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All the files (*)", 
            options=options
        )
        
        if file_path:
            # Open opacity dialog
            opacity_dialog = OpacityDialog(self)
            if opacity_dialog.exec_() == QDialog.Accepted:
                opacity = opacity_dialog.get_opacity()
                self.apply_watermark_image(file_path, opacity)
                self.watermarks_by_page[self.current_page] = {"path" : file_path, "opacity": opacity}

                return True
        return False
        
    def select_watermark_for_all_pages(self):
        """Open a dialog to select an image and apply it to all pages."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select the watermark image (All the pages)", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All the files (*)", 
            options=options
        )
        
        if file_path:
            self.apply_watermark_to_all_pages(file_path)
            return True
        return False

    def apply_watermark_image(self, image_path, opacity=0.3):
        """Apply the selected image as a watermark to the current PDF with adjustable opacity."""
        if not self.document:
            print("There is no open document to apply the watermark.")
            return False
            
        try:
            # Get the current page
            page = self.document[self.current_page]
            page_rect = page.rect
            
            # Create a new image to maintain transparency
            # In recent versions of PyMuPDF we can use alpha directly.
            try:
                # Try using the direct method with parameter alpha (recent versions)
                page.insert_image(page_rect, filename=image_path, overlay=False, alpha=opacity)
            except TypeError:
                # If the version does not support alpha, we use an alternative approach.
                img = fitz.open(image_path)
                pix = img[0].get_pixmap(alpha=True)
                
                # Adjust opacity manually
                import numpy as np
                samples = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                if pix.alpha:  # If the image has an alpha channel
                    alpha_channel = samples[:, :, -1]
                    alpha_channel = (alpha_channel * opacity).astype(np.uint8)
                    samples[:, :, -1] = alpha_channel
                
                # Create a new pixmap with the modified samples
                new_pix = fitz.Pixmap(pix.colorspace, pix.width, pix.height, samples.tobytes(), alpha=pix.alpha)
                page.insert_image(page_rect, pixmap=new_pix, overlay=False)
                
                # Clean
                img.close()
            
            # Render the updated page
            self.render_current_page()
            print(f"Watermark applied since: {image_path} with opacity {opacity:.1%}")
            self.document_modified = True
            return True
        
        except Exception as e:
            print(f"Error applying the watermark: {e}")
            return False
    
    def select_watermark_for_all_pages(self):
        """Open a dialog to select an image and apply it to all pages with adjustable opacity."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image for Watermark (All Pages)", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All files (*)", 
            options=options
        )
        
        if file_path:
            # Open opacity dialog
            opacity_dialog = OpacityDialog(self)
            if opacity_dialog.exec_() == QDialog.Accepted:
                opacity = opacity_dialog.get_opacity()
                self.apply_watermark_to_all_pages(file_path, opacity)
                return True
        return False
    
    def apply_watermark_to_all_pages(self, image_path, opacity=0.3):
        """Apply the watermark to all pages of the document with adjustable opacity."""
        if not self.document:
            print("There is no open document to apply the watermark.")
            return False
            
        try:
            # Check if we can use alpha directly
            supports_alpha = True
            try:
                # Test if the version of PyMuPDF supports alpha
                page = self.document[0]
                page.insert_image(fitz.Rect(0, 0, 1, 1), filename=image_path, overlay=False, alpha=0.5)
                # If we arrive here, withstand alpha.
            except TypeError:
                supports_alpha = False
            
            # Create a pixmap once to reuse it (if necessary)
            modified_pixmap = None
            if not supports_alpha:
                img = fitz.open(image_path)
                pix = img[0].get_pixmap(alpha=True)
                
                # Adjust opacity manually
                import numpy as np
                samples = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                if pix.alpha:  # If the image has an alpha channel
                    alpha_channel = samples[:, :, -1]
                    alpha_channel = (alpha_channel * opacity).astype(np.uint8)
                    samples[:, :, -1] = alpha_channel
                
                # Create a new pixmap with the modified samples
                modified_pixmap = fitz.Pixmap(pix.colorspace, pix.width, pix.height, samples.tobytes(), alpha=pix.alpha)
                img.close()
            
            # Apply to all pages
            for page_num in range(self.document.page_count):
                page = self.document[page_num]
                page_rect = page.rect
                
                # Insert the image as a watermark
                if supports_alpha:
                    page.insert_image(page_rect, filename=image_path, overlay=False, alpha=opacity)
                else:
                    page.insert_image(page_rect, pixmap=modified_pixmap, overlay=False)
            
            # Clean if necessary
            if modified_pixmap:
                modified_pixmap = None
            
            # Render the current page
            self.render_current_page()
            print(f"Watermark applied to all pages since: {image_path} with opacity {opacity:.1%}")
            self.document_modified = True
            return True
        
        except Exception as e:
            print(f"Error applying the watermark to all pages: {e}")
            return False
    
    def eventFilter(self, obj, event):
        """Event filter to capture mouse events"""
        
        # Handle mouse movement during highlighting
        if event.type() == QEvent.MouseMove and self.highlighting and self.document:
            # If we are dragging to underline
            if hasattr(self, 'highlight_start') and self.highlight_start:
                # Convert coordinates if necessary
                if obj == self:
                    # Event from the label
                    adjusted_x = event.pos().x()
                    adjusted_y = event.pos().y()
                else:
                    # Event from the label
                    adjusted_x = event.pos().x()
                    adjusted_y = event.pos().y()
                
                # Update final position
                self.highlight_end = (adjusted_x, adjusted_y)
        
        # Manage mouse release during highlighting
        elif event.type() == QEvent.MouseButtonRelease and self.highlighting and self.document:
            if event.button() == Qt.LeftButton and hasattr(self, 'highlight_start') and self.highlight_start:
                self.highlighting = False
                
                # Convert coordinates if necessary
                if obj == self:
                    adjusted_x = event.pos().x()
                    adjusted_y = event.pos().y()
                else:
                    # Event from the label
                    adjusted_x = event.pos().x()
                    adjusted_y = event.pos().y()
                
                # Save the final position
                self.highlight_end = (adjusted_x, adjusted_y)
                
                # Apply the underline
                self.apply_highlight()
        
        # Existing code for tooltips (only for MouseMove)
        if obj == self.page_label and event.type() == QEvent.MouseMove:
            # Get the mouse position relative to the label
            mouse_pos = event.pos()

            dpi_scale = self.dpi / 72.0  # Scale by DPI (72 is the base value)
            zoom_scale = self.zoom_factor
            total_scale = dpi_scale / zoom_scale

            # Check if the document is uploaded
            if hasattr(self, 'document') and self.document:
                tooltip_text = ""
                # If we have circles on the current page, check if the cursor is over any of them.
                if hasattr(self, 'formatted_circles_by_page') and self.current_page in self.formatted_circles_by_page:
                    
                    doc_x = mouse_pos.x() * total_scale
                    doc_y = mouse_pos.y() * total_scale
                    # Check each circle on the current page
                    for i, circle in enumerate(self.formatted_circles_by_page[self.current_page]):
                        # Calculate the distance between the cursor and the center of the circle
                        distance = sqrt((doc_x - circle['x'])**2 + (doc_y - circle['y'])**2)
                        
                        # If the distance is less than or equal to the radius, the cursor is over the circle.
                        if distance <= circle['radius']:
                            tooltip_text = self.changes_list_widget.changes_description[self.current_page][i].get("description", f"Difference {i+1}")
                            break
                
                QToolTip.showText(event.globalPos(), tooltip_text, self.page_label)
                
        return super(PDFViewer, self).eventFilter(obj, event)

    def mouseMoveEvent(self, event):
        """Control the mouse movement over the PDF viewer"""
        # If we are in underline mode
        if hasattr(self, 'highlighting') and self.highlighting and self.document and hasattr(self, 'highlight_start_pixels'):
            
            # Convert coordinates for the rubber band
            label_pos = self.page_label.mapFrom(self, event.pos())
            
            # Update the rubber band for visual feedback
            if hasattr(self, 'highlight_overlay'):
                start_pos = QPoint(self.highlight_start_pixels[0], self.highlight_start_pixels[1])
                self.highlight_overlay.setGeometry(QRect(start_pos, label_pos).normalized())
            
            # Save final position in adjusted coordinates for PDF
            adjusted_x = label_pos.x() + self.scroll_area.horizontalScrollBar().value()
            adjusted_y = label_pos.y() + self.scroll_area.verticalScrollBar().value()
            
            x, y = adjusted_x, adjusted_y
            self.highlight_end_pdf = (x, y)
        
        # Existing code for tooltips
        # Only process if we have uploaded documents
        if not self.document:
            return super(PDFViewer, self).mouseMoveEvent(event)
        
        # Check if the cursor is over the PDF viewer
        if self.page_label.underMouse():
            # Convert event coordinates to coordinates relative to the QLabel
            label_pos = self.page_label.mapFrom(self, event.pos())

            # Adjust by scrolling displacement
            adjusted_x = label_pos.x()
            adjusted_y = label_pos.y()
            
            # Show a tooltip with basic information
            tooltip_text = f"Position: X={adjusted_x}, Y={adjusted_y}\nPage: {self.current_page + 1} of {self.document.page_count}"
            
            # Add information about which document is being displayed
            if hasattr(self, 'showing_original') and self.showing_original:
                tooltip_text += "\nShowing: Original PDF"
            else:
                tooltip_text += "\nShowing: Annotated PDF"
            
            # Show tooltip
            QToolTip.showText(event.globalPos(), tooltip_text, self)
        else:
            QToolTip.hideText()
        
        return super(PDFViewer, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle the mouse button release event"""
        print("mouseReleaseEvent - Button:", event.button(), "- Highlighting:", self.highlighting)
        
        if event.button() == Qt.LeftButton and self.drag_mode and self.dragging:
            self.dragging = False
            self.page_label.setCursor(Qt.OpenHandCursor)
            
        # If we were highlighting and it's the left button.
        if self.highlighting and event.button() == Qt.LeftButton and self.document:
            print("Finalizing underlining")
            self.highlighting = False
            
            # Hide the rubber band
            if hasattr(self, 'highlight_overlay'):
                self.highlight_overlay.hide()
            
            # Convert coordinates for the endpoint
            label_pos = self.page_label.mapFrom(self, event.pos())
            print("Label_pos", label_pos)
            pos = event.pos()
            print("Event Pos", pos)
            print("Debugging scroll area")
            
            print("Vertical",self.scroll_area.verticalScrollBar().value())
            print("Horizontal",self.scroll_area.horizontalScrollBar().value())
            adjusted_x = label_pos.x()
            adjusted_y = label_pos.y()

            x, y = adjusted_x, adjusted_y
            self.highlight_end_pdf = (x, y)
                        
            print("Highlight_start",self.highlight_start_pdf)
            print("Highlight_end",self.highlight_end_pdf)

            print(f"End of underline in PDF coords: {self.highlight_end_pdf}")
            
            # Apply the underline
            self.apply_highlight()
        
        super(PDFViewer, self).mouseReleaseEvent(event)
        
    def apply_highlight(self):
        if not self.document:
            print("No document uploaded.")
            return
        
        if not hasattr(self, 'highlight_start_pdf') or not hasattr(self, 'highlight_end_pdf'):
            print("There are no underlined coordinates..")
            return
        
        # Obtain information from the page and the transformation
        page = self.document[self.current_page]
        page_rect = page.rect  # Rectángulo de la página en coordenadas de PDF
        
        # Obtain the size of the current pixmap to understand the relationship between the screen and PDF.
        pixmap_width = self.page_label.pixmap().width()
        pixmap_height = self.page_label.pixmap().height()

        current_rotation = page.rotation
    
        if current_rotation == 0:
            # Obtain pixel coordinates
            x0, y0 = self.highlight_start_pdf
            x1, y1 = self.highlight_end_pdf
        elif current_rotation == 90:
            x0, y0 = self.highlight_start_pdf[1], page_rect.width - self.highlight_end_pdf[0] 
            x1, y1 = self.highlight_end_pdf[1], page_rect.width - self.highlight_start_pdf[0] 
        elif current_rotation == 180:
            x0, y0 = page_rect.width - self.highlight_end_pdf[0], page_rect.height - self.highlight_end_pdf[1]
            x1, y1 = page_rect.width - self.highlight_start_pdf[0], page_rect.height - self.highlight_start_pdf[1]
        elif current_rotation == 270:
            x0, y0 = page_rect.height - self.highlight_end_pdf[1], self.highlight_start_pdf[0]
            x1, y1 = page_rect.height - self.highlight_start_pdf[1], self.highlight_end_pdf[0]

        print("x0",x0)
        print("y0",y0)
        print("x1",x1)
        print("y1",y1)

        # Calculate the relationship between pixmap and PDF
        x_ratio = page_rect.width / pixmap_width
        y_ratio = page_rect.height / pixmap_height 
        
        # Convert from screen coordinates to PDF coordinates
        pdf_x0 = x0 * x_ratio
        pdf_y0 = y0 * y_ratio
        pdf_x1 = x1 * x_ratio
        pdf_y1 = y1 * y_ratio
        
        print("x_ratio", x_ratio)
        print("y_ratio", y_ratio)

        # Create rectangle in PDF coordinates
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
        
        print(f"Coords pantalla (ajustadas): ({x0}, {y0}) a ({x1}, {y1})")
        print(f"Coords PDF: ({pdf_x0}, {pdf_y0}) a ({pdf_x1}, {pdf_y1})")
        print(f"Rectángulo PDF: {rect}")
        
        try:
            # Apply the underline
            annot = page.add_highlight_annot(rect)
            annot.set_colors(stroke=(1, 1, 0)) 
            annot.update()
            print("Underline applied successfully")
        except Exception as e:
            print(f"Error applying underline: {e}")
        
        # Clear the variables
        if hasattr(self, 'highlight_start_pdf'):
            del self.highlight_start_pdf
        if hasattr(self, 'highlight_end_pdf'):
            del self.highlight_end_pdf
        if hasattr(self, 'highlight_start_pixels'):
            del self.highlight_start_pixels
        
        # Render the updated page
        self.render_current_page()
        self.document_modified = True

    def update_temp_highlight(self):
        """Update the temporary highlighting while the mouse is dragged"""
        if not self.document or not self.highlight_start or not self.highlight_end:
            return
        
        page = self.document[self.current_page]
        
        # Remove previous temporary annotation if it exists
        if self.temp_highlight_annot:
            try:
                # Check if the annotation is still linked to the page.
                # This will avoid the error "Annot is not bound to a page"
                if hasattr(self.temp_highlight_annot, 'parent') and self.temp_highlight_annot.parent:
                    page.delete_annot(self.temp_highlight_annot)
            except Exception as e:
                print(f"Error al eliminar anotación temporal: {e}")
            finally:
                self.temp_highlight_annot = None
        
        # Get coordinates
        x0, y0 = self.highlight_start
        x1, y1 = self.highlight_end
        
        # Make sure that the values are in order.
        x0, x1 = sorted([x0, x1])
        y0, y1 = sorted([y0, y1])
        
        # Create a rectangle for the underline
        rect = fitz.Rect(x0, y0, x1, y1 + 10.0)
        
        try:
            # Create a temporary annotation with a different style to distinguish it.
            self.temp_highlight_annot = page.add_highlight_annot(rect)
            self.temp_highlight_annot.set_colors(stroke=(0.5, 0.5, 1))  
            self.temp_highlight_annot.set_opacity(0.5)  # Semi-transparent
            self.temp_highlight_annot.update()
            
            # Render the page to show the change
            self.render_current_page()
        except Exception as e:
            print(f"Error creating temporary annotation: {e}")
            self.temp_highlight_annot = None

    def keyPressEvent(self, event):
        """Capture key press events"""
        # Detect if the Q key is pressed
        if event.key() == Qt.Key_Q and not event.isAutoRepeat():
            print("Key Q pressed - showing original PDF")
            self.show_pdf(is_original=True)
            return
        
        # Cancel underline if Escape is pressed
        if event.key() == Qt.Key_Escape and self.highlighting:
            self.highlighting = False
            self.highlight_start = None
            self.highlight_end = None
        
        # Remove temporary annotation if it exists
        if self.temp_highlight_annot:
            page = self.document[self.current_page]
            page.delete_annot(self.temp_highlight_annot)
            self.temp_highlight_annot = None
            self.render_current_page()
        
        # Let the event continue its normal processing for other keys.
        super(PDFViewer, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """Capture key release events"""
        # Detect if the Q key is released
        if event.key() == Qt.Key_Q and not event.isAutoRepeat():
            print("Key Q released - returning to annotated PDF")
            self.show_pdf(is_original=False)
            return
        
        # Let the event continue its normal processing for other keys.
        super(PDFViewer, self).keyReleaseEvent(event)

    def show_pdf(self, is_original=False):
        """Show the original or annotated PDF according to the parameter"""
        if not self.document or (is_original and not self.original_document):
            print("There are no uploaded documents to display.")
            return
            
        self.showing_original = is_original
        
        # Change the title according to the PDF that is being displayed
        if hasattr(self, 'title_label'):
            if is_original:
                self.title_label.setText("Original PDF")
            else:
                self.title_label.setText("Annotated PDF")

        # Save the current scroll position
        h_value = self.scroll_area.horizontalScrollBar().value()
        v_value = self.scroll_area.verticalScrollBar().value()
        
        # Render the corresponding page
        self.render_current_page()
        
        # Update the status of the navigation buttons
        doc_to_check = self.original_document if is_original else self.document
        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled(self.current_page < doc_to_check.page_count - 1)
        
        # Restore the scroll position
        self.scroll_area.horizontalScrollBar().setValue(h_value)
        self.scroll_area.verticalScrollBar().setValue(v_value)

    def load_pdf(self, pdf_path, original_pdf_path=None, c_page = 0):
        """Upload a PDF file to the viewer."""
        if pdf_path:
            # Close previous document if it exists
            if self.document:
                self.document.close()

            # Open new document
            self.document = fitz.open(pdf_path)
            self.current_page = c_page
            
            #Load original PDF
            if original_pdf_path:
                if self.original_document:
                    self.original_document.close()
                self.original_document = fitz.open(original_pdf_path)

            # Update interface
            self.update_page_info()
            self.render_current_page()
            
            # Enable/disable buttons
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(self.document.page_count > 1 )

    # Add a method to reload the document (useful after a rotation):
    def reload_document(self):
        """
        Reload the current document while keeping the current page. 
        Useful after making changes such as rotations.
        """
        if not self.document:
            return
        
        # Save the current page
        current_page = self.current_page
        
        # Close the document
        self.document.close()

        # Reopen the document
        self.document = fitz.open(self)

        # Make sure that the current page is valid
        self.current_page = min(current_page, len(self.document) - 1)
        
        # Update view
        self.update_display()
        
        # Update the page information if necessary
        self.update_page_info()

    def has_changes_list(self):
        """Check if this viewer has a list of changes."""
        return self.changes_list_widget is not None
    
    def navigate_to_change(self, page_num, change):
        """Navigate to a specific change when selected from the list"""

        # Remove only the previous red circle
        if self.active_circle_annot:
            try:
                page_of_annot = self.document[self.current_page]
                page_of_annot.delete_annot(self.active_circle_annot)
                page_of_annot.clean_contents()
                self.document.saveIncr()
            except Exception as e:
                print("Error deleting red circle:", e)
            self.active_circle_annot = None

        # Navigate to page if necessary
        if self.current_page != page_num:
            self.current_page = page_num
            self.update_page_info()
            self.prev_button.setEnabled(self.current_page > 0)
            self.next_button.setEnabled(self.current_page < self.document.page_count - 1)

        # Zoom and render
        self.zoom_factor = 2.0
        self.render_current_page()
        self.scroll_to_change(change)

        # Add new red circle
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
            circle_annot.set_colors(stroke=(1, 0, 0), fill=None)  # only red outline
            circle_annot.set_opacity(1.0)
            circle_annot.set_flags(0)

            self.active_circle_annot = circle_annot
            self.document.saveIncr()
            self.render_current_page()
    
    def scroll_to_change(self, change):

        dpi_scale = self.dpi / 72.0  # Scale by DPI (72 is the base value)
        zoom_scale = self.zoom_factor
        total_scale = dpi_scale / zoom_scale

        """move the view to center the selected change"""
        if not self.document:
            return
            
        # Get dimensions of the current pixmap
        if self.page_label.pixmap() is None:
            print("Error: No pixmap in page_label")
            return

        # Calculate the position of the change in the pixmap with the current zoom
        change_x = change['x']
        change_y = change['y']
        
        #Compute scroll
        scroll_x = (change_x / self.page_width)
        scroll_y = (change_y / self.page_height)

        #scroll area dimensions
        h_scroll = self.scroll_area.horizontalScrollBar().width() + self.scroll_area.horizontalScrollBar().maximum()
        v_scroll = self.scroll_area.verticalScrollBar().height() + self.scroll_area.verticalScrollBar().maximum()

        # Adjust the scroll to center the change
        h_value = max(0, int(h_scroll*scroll_x-self.width()/2))
        v_value = max(0, int(v_scroll*scroll_y-self.height()/2))

        # Limit the scroll values to the allowed maximums
        h_value = min(h_value, self.scroll_area.horizontalScrollBar().maximum())
        v_value = min(v_value, self.scroll_area.verticalScrollBar().maximum())

        # Set the scroll values
        self.scroll_area.horizontalScrollBar().setValue(h_value)
        self.scroll_area.verticalScrollBar().setValue(v_value)

    def label_mouse_press_event(self, event):
        """Manage the clicks on the PDF label"""
        pos = event.pos()
        print("Label Press event")
        print(f"Click on QLabel (without displacement)): {pos}")

        if event.button() == Qt.LeftButton and self.drag_mode:
            self.dragging = True
            self.last_drag_pos = event.globalPos()
            self.page_label.setCursor(Qt.ClosedHandCursor)

        # If it is the left button and we are in annotated PDF, start highlighting.
        if event.button() == Qt.LeftButton and not self.showing_original and self.document and not self.drag_mode:
            print("Starting underline mode")
            self.highlighting = True
            
            # Convert coordinates to PDF coordinates
            page = self.document[self.current_page]
            
            # Save the initial position in pixel coordinates for visual feedback
            self.highlight_start_pixels = (pos.x(), pos.y())
            
            # Convert to PDF coordinates
            adjusted_x = pos.x() 
            adjusted_y = pos.y() 
            
            # Save the exact position in PDF coordinates
            x, y = adjusted_x, adjusted_y
            self.highlight_start_pdf = (x, y)
            
            print(f"Start of pixel highlighting: {self.highlight_start_pixels}")
            print(f"Start of highlighting in PDF coords: {self.highlight_start_pdf}")
            
            # Start rubber band for visual feedback
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
        #enables or disables click detection on circles
        self.clicks_enabled = enabled
    
    # Update the display
    def update_display(self):
        """
        Update the PDF view after making modifications such as rotations.
        """
        if not self.document or self.current_page >= len(self.document):
            return
        
        # Get the current page
        page = self.document[self.current_page]
        
        # Render the page again
        pix = page.get_pixmap(matrix=self.matrix)
        
        # Convert to QImage and update the QLabel
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(img)
        
        # Assuming you have a QLabel called image_label
        if hasattr(self, 'image_label'):
            self.page_label.setPixmap(pixmap)
        
        # Update page information in the UI if necessary
        self.update_page_info()

    def update_page_info(self):
        """Update the information on the current page."""
        print("Executing update_page_info")
        if self.document:
            self.page_info.setText(f"Page {self.current_page + 1} of {self.document.page_count}")
            
            # Update the change log for the current page (only if it exists)
            if self.has_changes_list() and hasattr(self, 'formatted_circles_by_page'):
                if self.current_page in self.formatted_circles_by_page:
                    changes = self.formatted_circles_by_page[self.current_page]
                    self.changes_list_widget.update_changes_list(self.formatted_circles_by_page)
                else:
                    self.changes_list_widget.update_changes_list(self.formatted_circles_by_page)
    
    def render_current_page(self):
        """Render the current page of the PDF."""
        if not self.document:
            print("Error: There is no main document to render.")
            return
        
        # Determinar qué documento renderizar
        doc_to_render = self.original_document if self.showing_original else self.document
        
        # Verify that the document to be rendered exists
        if not doc_to_render:
            print("Error: No hay documento disponible para renderizar")
            return
        
        print(f"Rendering page {self.current_page} from document: {doc_to_render}")
        
        # Obtain current page
        page = doc_to_render[self.current_page]
        
        # Apply zoom
        matrix = fitz.Matrix(self.zoom_factor, self.zoom_factor)
        pix = page.get_pixmap(matrix=matrix)
        
        print(f"Pixmap created: {pix.width}x{pix.height}")
        
        # Convertir a QImage/QPixmap
        img_data = QByteArray(pix.samples)
        qimg = QImage(img_data, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        
        print(f"QPixmap creado: {pixmap.width()}x{pixmap.height()}")
        
        # Show on the label
        self.page_label.setPixmap(pixmap)
        self.page_label.resize(pixmap.size())

    def modify_annotations(self, page_num, clicked_circle, is_checked):
        print(f"modify_annotations called - Página: {page_num}, Circle: {clicked_circle}, Checked: {is_checked}")
    
        if not hasattr(self, 'formatted_circles_by_page') or page_num not in self.formatted_circles_by_page:
            print("There are no formatted circles for this page.")
            return []

        updated_annotations = []

        for circle in self.formatted_circles_by_page[page_num]:
            # Compare if the current circle is the one that was clicked.
            if (circle['x'] == clicked_circle['x'] and 
                circle['y'] == clicked_circle['y'] and 
                circle['radius'] == clicked_circle['radius']):
                
                # Modify the circle
                modified_circle = circle.copy()
                modified_circle["selected"] = is_checked
                updated_annotations.append(modified_circle)
                print(f"Circle in page {page_num} modified - Selected: {is_checked}")
            else:
                updated_annotations.append(circle)

        # Save the changes to the data structure
        self.formatted_circles_by_page[page_num] = updated_annotations
        self.changes_list_widget.formatted_circles_by_page[page_num] = updated_annotations
        
        # Update the display after modification
        self.reload_page()
        
        # Update the change log to reflect the new status
        if self.changes_list_widget:
            self.changes_list_widget.update_changes_list(self.formatted_circles_by_page)
            
        return updated_annotations

    def detect_circle_click(self, pos):
        if self.current_page not in self.formatted_circles_by_page:
            print("There are no circles on this page.")
            return None, None

        dpi_scale = self.dpi / 72.0  # Scale by DPI (72 is the base value)
        zoom_scale = self.zoom_factor
        total_scale = dpi_scale / zoom_scale

        for circle in self.formatted_circles_by_page[self.current_page]:
            scaled_x = pos.x() * total_scale
            scaled_y = pos.y() * total_scale

            scaled_radius = circle['radius']

            # Calculate real distance
            distance = sqrt((scaled_x - circle['x'])**2 + (scaled_y - circle['y'])**2)

            if distance <= scaled_radius:
                print("¡Click inside the circle!",circle)
                return self.current_page, circle
            
        print(f"Click on: {pos.x()}, {pos.y()}")
        
        print("No click was made on any circle")
        return None, None

    def set_circles(self, circles_by_page, page_width, page_height, json_loaded = False):
        self.page_width = page_width
        self.page_height = page_height

        """Set the circles detected per page."""
        self.circles_by_page = circles_by_page
        self.formatted_circles_by_page = {}

        if json_loaded: #When changes to the json are loaded
            for page, circles in circles_by_page.items():
                # First format all the circles
                formatted_circles = []
                for circle in circles:
                    formatted_circles.append({
                        "x": circle['x'],
                        "y": circle['y'],
                        "radius": circle['radius'],
                        "selected": ['selected'],
                    })
                # Filter circles using method 1 (complete containment filtering)
                filtered_circles = self.filter_contained_circles(formatted_circles)
                self.formatted_circles_by_page[page] = filtered_circles

            # Update the change log if we are on a page with changes and if the list exists.
            if self.has_changes_list() and self.current_page in self.formatted_circles_by_page:
                self.changes_list_widget.update_changes_list(self.formatted_circles_by_page)

            self.render_current_page()
            self.update_page_info()
            return self.formatted_circles_by_page
        
        else: #When making a comparison
            for page, circles in circles_by_page.items():
                # First format all the circles
                formatted_circles = []
                for circle in circles:
                    formatted_circles.append({
                        "x": circle[0],
                        "y": circle[1],
                        "radius": circle[2],
                        "selected": True,
                    })
            
                # Filter circles using method 1 (complete containment filtering)
                filtered_circles = self.filter_contained_circles(formatted_circles)
                self.formatted_circles_by_page[page] = filtered_circles
        
            # Update the change log if we are on a page with changes and if the list exists.
            if self.has_changes_list() and self.current_page in self.formatted_circles_by_page:
                self.changes_list_widget.update_changes_list(self.formatted_circles_by_page)

            self.render_current_page()
            self.update_page_info()
            return self.formatted_circles_by_page
        
    def filter_contained_circles(self, circles):
        """
        Filter the circles, discarding those that are contained within larger circles. 
        Return only the larger 'containing' circles.
        """
        if not circles:
            return []
        
        # Create a copy to avoid modifying the original list.
        result = circles.copy()
        circles_to_remove = set()
        
        # Compare each pair of circles
        for i, circle1 in enumerate(circles):
            for j, circle2 in enumerate(circles):
                if i == j:
                    continue  # Do not compare a circle to itself
                
                # Calculate the distance between the centers
                distance = sqrt((circle1['x'] - circle2['x'])**2 + (circle1['y'] - circle2['y'])**2)
                
                #Detect if one circle is inside the other.
                if distance <= abs(circle1['radius'] - circle2['radius']):
                    # Determine which is the smallest circle (content)
                    if circle1['radius'] < circle2['radius']:
                        circles_to_remove.add(i)  # Circle 1 is contained in circle 2.
                    elif circle2['radius'] < circle1['radius']:
                        circles_to_remove.add(j)  # Circle 2 is contained in Circle 1.
        
        # Create a new list without the contained circles
        filtered_result = [circle for i, circle in enumerate(result) if i not in circles_to_remove]
        
        print(f"Filtering {len(circles) - len(filtered_result)} overlaped circles.")
        return filtered_result
    
    def reload_page(self):
        """Reload the current page (useful when the notes change)."""
        self.render_current_page()

    def next_page(self):
        """Navigate to the next page."""
        if self.document and self.current_page < self.document.page_count - 1:
            self.current_page += 1
            self.render_current_page()
            self.update_page_info()
            
            # Update status of the buttons
            self.prev_button.setEnabled(True)
            self.next_button.setEnabled(self.current_page < self.document.page_count - 1)
    
    def prev_page(self):
        """Navigate to the previous page."""
        if self.document and self.current_page > 0:
            self.current_page -= 1
            self.render_current_page()
            self.update_page_info()
            
            # Update status of the buttons
            self.prev_button.setEnabled(self.current_page > 0)
            self.next_button.setEnabled(True)
    
    def zoom_in(self):
        """Increase zoom."""
        self.zoom_factor *= 1.25
        self.render_current_page()
    
    def zoom_out(self):
        """Decrease zoom."""
        if self.zoom_factor > 1.0:
            self.zoom_factor /= 1.25
            self.render_current_page()
    
    def zoom_reset(self):
        """Reset the zoom to 100%."""
        self.zoom_factor = 1.0
        self.render_current_page()

    def apply_shadow(self, widget, blur=15, x_offset=0, y_offset=2, alpha=40):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur)  # Blurring of the shadow
        shadow.setXOffset(x_offset)  # Horizontal shadow
        shadow.setYOffset(y_offset)  # Vertical shadow
        shadow.setColor(QColor(0, 0, 0, alpha))  # Black color with transparency
        widget.setGraphicsEffect(shadow)