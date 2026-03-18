import os
import tempfile
import traceback
import uuid
import datetime

from PySide6.QtCore import QRunnable, Slot, QObject, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QWizardPage, QVBoxLayout, QLabel, QPushButton,
                               QFileDialog, QLineEdit, QProgressBar, QFormLayout,
                               QComboBox, QSpinBox, QTextEdit)
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


class PrintWorkerSignals(QObject):
    finished = Signal(str)
    error = Signal(object)
    progress = Signal(int)


class PrintWorker(QRunnable):
    def __init__(self, wizard, gui, config=None, spine_uuid=None):
        super().__init__()
        self.wizard = wizard
        self.gui = gui
        self.signals = PrintWorkerSignals()
        self.config = config or {}
        # Shortened UUID and Spine QR Code for lower matrix density
        self.spine_uuid_str = spine_uuid or uuid.uuid4().hex[:8]

    @Slot()
    def run(self):
        """The actual PDF generation logic running in the background thread."""
        try:
            output_path = os.path.join(self.config['output_dir'], f"bluray_cover_{self.spine_uuid_str}.pdf")
            self.generate_pdf(output_path, self.config)
            self.signals.finished.emit(output_path)
        except Exception as e:
            msg = traceback.format_exc()
            self.signals.error.emit({"exception": e, "msg": msg})

    # --- WIZARD PAGES ---

    def select_file_page(self):
        page = QWizardPage()
        page.setTitle("Select Cover Image")
        layout = QVBoxLayout()

        btn = QPushButton("Choose Image...")
        path_display = QLineEdit()
        path_display.setReadOnly(True)
        path_display.setPlaceholderText("Select high-res JPG or PNG...")

        btn.clicked.connect(lambda: self._file_dialog(path_display, "Image Files (*.jpg *.png *.jpeg)"))

        page.registerField("cover_image*", path_display)

        layout.addWidget(QLabel("Select the main artwork for the front cover:"))
        layout.addWidget(btn)
        layout.addWidget(path_display)
        page.setLayout(layout)
        return page

    def enter_details_page(self):
        page = QWizardPage()
        page.setTitle("Disc Metadata")
        layout = QFormLayout()

        self.disc_type_detail = self.gui.disc_size_combo.currentText()
        self.disc_type = "Blu-ray" if "BD" in self.disc_type_detail else "DVD"
        self.media_type = "Player Disc" if self.gui.media_playback.isChecked() else "Data"

        self.title_in = QLineEdit(f"Optical Disc")
        self.desc_in = QTextEdit()
        self.desc_in.setAcceptRichText(False)
        self.desc_in.setMinimumHeight(100)
        self.desc_in.setPlainText(f'Built to Last. This release is preserved on M-DISC™ archival media, utilizing a '
                                 f'"rock-like" recording layer to protect your data for centuries. Engineered '
                                 f'for a lifetime of 100 to 1,000+ years, it is practically impervious to '
                                 f'environmental exposure.')
        self.tech_in = QLineEdit(
            f"{self.disc_type_detail} | {self.disc_type} {self.media_type} | FOSS | {self.spine_uuid_str}")
        self.meta_in = QLineEdit(f"{self.disc_type_detail} | "
                                 f"Created {datetime.datetime.now().strftime("%b")} {datetime.datetime.now().year}.")
        self.qr_in = QLineEdit("https://github.com/hammad93/crypto-disco")

        self.font_combo = QComboBox()
        # ReportLab includes these standard fonts by default without needing to embed TTF files
        self.font_combo.addItems(
            ["Helvetica", "Helvetica-Bold", "Times-Roman", "Times-Bold", "Courier", "Courier-Bold"])
        self.font_combo.setCurrentText("Helvetica-Bold")

        self.font_path_in = QLineEdit()  # Hidden or read-only to store the custom path
        self.font_path_in.setVisible(False)

        btn_font = QPushButton("Import Custom TTF...")
        btn_font.clicked.connect(self._import_font_dialog)

        font_layout = QVBoxLayout()
        font_layout.addWidget(self.font_combo)
        font_layout.addWidget(btn_font)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(6, 48)
        self.size_spin.setValue(16)

        page.registerField("disc_title", self.title_in)
        page.registerField("description", self.desc_in, "plainText")
        page.registerField("tech_doc", self.tech_in)
        page.registerField("metadata", self.meta_in)
        page.registerField("qr_data", self.qr_in)
        page.registerField("title_font", self.font_combo, "currentText")
        page.registerField("custom_font_path", self.font_path_in)
        page.registerField("title_size", self.size_spin, "value")

        layout.addRow("", font_layout)
        layout.addRow("Disc Title:", self.title_in)
        layout.addRow("Title Font:", self.font_combo)
        layout.addRow("Title Size:", self.size_spin)
        layout.addRow("Technical:", self.tech_in)
        layout.addRow("Metadata:", self.meta_in)
        layout.addRow("QR Data:", self.qr_in)
        layout.addRow("Description:", self.desc_in)

        page.setLayout(layout)
        return page

    def select_output_page(self):
        page = QWizardPage()
        page.setTitle("Generate PDF")
        layout = QVBoxLayout()

        btn = QPushButton("Select Output Folder")
        path_display = QLineEdit()
        path_display.setReadOnly(True)
        btn.clicked.connect(lambda: self._dir_dialog(path_display))

        page.registerField("output_dir*", path_display)

        self.preview_btn = QPushButton("Preview PDF")
        self.preview_btn.clicked.connect(self._trigger_preview)

        self.run_btn = QPushButton("Create PDF Now")
        self.run_btn.clicked.connect(self._trigger_generation)

        self.pbar = QProgressBar()
        self.status_lbl = QLabel("Ready to generate.")

        layout.addWidget(QLabel("Where should the PDF be saved?"))
        layout.addWidget(btn)
        layout.addWidget(path_display)

        # --- NEW: Added preview button to layout ---
        layout.addWidget(self.preview_btn)
        layout.addWidget(self.run_btn)
        layout.addWidget(self.status_lbl)
        layout.addWidget(self.pbar)

        page.setLayout(layout)
        return page

    # --- HELPERS & GENERATION ---

    def _file_dialog(self, line_edit, filter):
        path, _ = QFileDialog.getOpenFileName(self.wizard, "Select File", "", filter)
        if path: line_edit.setText(path)

    def _dir_dialog(self, line_edit):
        path = QFileDialog.getExistingDirectory(self.wizard, "Select Folder")
        if path: line_edit.setText(path)

    def _get_current_config(self):
        """Helper to pull current fields from the wizard."""
        return {
            "cover_image": self.wizard.field("cover_image"),
            "output_dir": self.wizard.field("output_dir"),
            "disc_title": self.wizard.field("disc_title"),
            "description": self.wizard.field("description"),
            "tech_doc": self.wizard.field("tech_doc"),
            "metadata": self.wizard.field("metadata"),
            "qr_data": self.wizard.field("qr_data"),
            "title_font": self.wizard.field("title_font") or "Helvetica-Bold",
            "custom_font_path": self.wizard.field("custom_font_path"),
            "title_size": self.wizard.field("title_size") or 12
        }

    def _trigger_preview(self):
        """Generates a temporary PDF and opens it in the system viewer."""
        config = self._get_current_config()
        # Reroute output to a temporary system folder for the preview
        preview_path = os.path.join(tempfile.gettempdir(), "bluray_cover_preview.pdf")

        try:
            self.status_lbl.setText("Generating preview...")
            self.generate_pdf(preview_path, config)
            QDesktopServices.openUrl(QUrl.fromLocalFile(preview_path))
            self.status_lbl.setText("Preview opened.")
        except Exception as e:
            self.status_lbl.setText(f"Preview error: {e}")
            print(traceback.format_exc())

    def _trigger_generation(self):
        config = self._get_current_config()

        self.run_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)
        self.pbar.setRange(0, 0)
        self.status_lbl.setText("Generating PDF...")

        worker = PrintWorker(self.wizard, self.gui, config, self.spine_uuid_str)
        worker.signals.finished.connect(self._on_finished)
        worker.signals.error.connect(self._on_error)
        self.gui.threadpool.start(worker)

    def _on_finished(self, path):
        self.pbar.setRange(0, 100)
        self.pbar.setValue(100)
        self.status_lbl.setText(f"Success! Saved to: {os.path.basename(path)}")
        self.run_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)

    def _on_error(self, err_obj):
        self.pbar.setRange(0, 100)
        self.status_lbl.setText("Error occurred.")
        self.run_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)
        print(err_obj['msg'])

    def _import_font_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self.wizard, "Select TrueType Font", "", "Font Files (*.ttf)")
        if path:
            # Extract clean name from filename (e.g., "MyFont.ttf" -> "MyFont")
            font_name = os.path.splitext(os.path.basename(path))[0].replace(" ", "_")

            # Add to combo and select it
            if self.font_combo.findText(font_name) == -1:
                self.font_combo.addItem(font_name)

            self.font_combo.setCurrentText(font_name)
            self.font_path_in.setText(path)

    def generate_pdf(self, output_path, data):
        c = canvas.Canvas(output_path, pagesize=landscape(A4))
        page_width, page_height = landscape(A4)

        # Extract styling data
        title_font = data.get("title_font", "Helvetica-Bold")
        title_size = data.get("title_size", 12)
        font_path = data.get("custom_font_path", "")

        # Check if we need to register a custom font
        if font_path and os.path.exists(font_path):
            try:
                # Registering the font makes it available by its name globally in ReportLab
                pdfmetrics.registerFont(TTFont(title_font, font_path))
            except Exception as e:
                print(f"Font registration failed: {e}")
                title_font = "Helvetica-Bold"  # Fallback

        # 1. Dimensions & Centering
        cover_height = 161 * mm
        panel_width = 137 * mm
        spine_width = 12 * mm
        total_width = (panel_width * 2) + spine_width

        x_start = (page_width - total_width) / 2
        y_start = (page_height - cover_height) / 2

        spine_x = x_start + panel_width
        front_x = spine_x + spine_width

        # 2. Draw the Cutting Outline
        c.setLineWidth(1)
        c.setStrokeColorRGB(0, 0, 0)
        c.rect(x_start, y_start, total_width, cover_height)
        c.line(spine_x, y_start, spine_x, y_start + cover_height)
        c.line(front_x, y_start, front_x, y_start + cover_height)

        # 3. Top Banner (Across the whole insert)
        banner_height = 15 * mm
        banner_y = y_start + cover_height - banner_height
        c.setFillColorRGB(0, 0, 0)
        c.rect(x_start, banner_y, total_width, banner_height, stroke=0, fill=1)

        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(front_x + (panel_width / 2), banner_y + (banner_height / 2) - 1.5 * mm,
                            "M-DISC ARCHIVAL DATA")
        c.drawCentredString(x_start + (panel_width / 2), banner_y + (banner_height / 2) - 1.5 * mm, "ARCHIVAL DATA")

        # --- Setup Text Styles for Paragraphs ---
        styles = getSampleStyleSheet()

        style_desc = ParagraphStyle(
            'Description',
            parent=styles['Normal'],
            fontName='Times-Roman',
            fontSize=9,
            leading=12,
            alignment=0
        )

        style_tech = ParagraphStyle(
            'Tech',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            alignment=1,
            textColor='black'
        )

        style_meta = ParagraphStyle(
            'Metadata',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=8,
            leading=10,
            alignment=1
        )

        # --- Test Cases ---
        disc_title_text = data["disc_title"]
        description_text = data["description"]
        tech_doc_text = data["tech_doc"]
        metadata_text = data["metadata"]
        qr_data = data["qr_data"]

        text_margin = 10 * mm
        avail_text_width = panel_width - (text_margin * 2)

        # --- FRONT PANEL RENDERING ---
        # Front Image (Maximized & Preserving Aspect Ratio)
        image_filename = data.get("cover_image", "")
        img_box_width = panel_width - 10 * mm
        img_box_height = 100 * mm
        img_x = front_x + 5 * mm
        img_y = y_start + 25 * mm

        if image_filename and os.path.exists(image_filename):
            c.drawImage(image_filename, img_x, img_y, width=img_box_width, height=img_box_height,
                        preserveAspectRatio=True, anchor='c')
        else:
            c.setStrokeColorRGB(0.7, 0.7, 0.7)
            c.rect(img_x, img_y, img_box_width, img_box_height, stroke=1, fill=0)
            c.setFillColorRGB(0.5, 0.5, 0.5)
            c.setFont("Helvetica", 10)
            c.drawCentredString(img_x + (img_box_width / 2), img_y + (img_box_height / 2), "[IMAGE PLACEHOLDER]")

        # Disc Title (Applies selected font and size)
        c.setFillColorRGB(0, 0, 0)
        c.setFont(title_font, title_size)
        c.drawCentredString(front_x + (panel_width / 2), y_start + cover_height - 30 * mm, disc_title_text)

        # Technical Documentation
        p_tech = Paragraph(tech_doc_text, style_tech)
        p_tech.wrapOn(c, avail_text_width, 20 * mm)
        p_tech.drawOn(c, front_x + text_margin, y_start + 10 * mm)

        # --- BACK PANEL RENDERING ---
        # Disc Title (Applies selected font and size)
        c.setFillColorRGB(0, 0, 0)
        c.setFont(title_font, title_size)
        c.drawCentredString(x_start + (panel_width / 2), y_start + cover_height - 25 * mm, disc_title_text)

        # Description Paragraph
        p_desc = Paragraph(description_text, style_desc)
        p_desc.wrapOn(c, avail_text_width, 40 * mm)
        p_desc.drawOn(c, x_start + text_margin, y_start + 110 * mm)

        # High Capacity QR Code
        qr_size = 75 * mm
        qr_widget = qr.QrCodeWidget(qr_data)
        qr_widget.barLevel = 'Q'
        qr_widget.barWidth = qr_size
        qr_widget.barHeight = qr_size

        d = Drawing(qr_size, qr_size)
        d.add(qr_widget)
        qr_render_x = x_start + (panel_width - qr_size) / 2
        qr_render_y = y_start + 35 * mm
        renderPDF.draw(d, c, qr_render_x, qr_render_y)

        # Metadata
        p_meta = Paragraph(metadata_text, style_meta)
        p_meta.wrapOn(c, avail_text_width, 30 * mm)
        p_meta.drawOn(c, x_start + text_margin, y_start + 125 * mm)

        # --- SPINE RENDERING ---
        # Spine Title (Applies font only; size remains 10)
        c.setFont(title_font, 12)
        c.setFillColorRGB(0, 0, 0)
        c.saveState()
        c.translate(spine_x + (spine_width / 2) + 2, y_start + (cover_height / 2) + 10 * mm)
        c.rotate(90)
        c.drawCentredString(0, 0, disc_title_text)
        c.restoreState()

        spine_qr_size = 10 * mm
        spine_qr = qr.QrCodeWidget(self.spine_uuid_str)
        spine_qr.barLevel = 'L'
        spine_qr.barWidth = spine_qr_size
        spine_qr.barHeight = spine_qr_size

        # 4. WRITABLE LINES (Directly below description)
        line_y_start = y_start + 35 * mm
        c.setLineWidth(0.5)
        c.setStrokeColorRGB(0.7, 0.7, 0.7)
        for i in range(5):  # Draw 3 lines (Note: logic executes 5 lines)
            ly = line_y_start - (i * 7 * mm)
            c.line(x_start + text_margin, ly, x_start + panel_width - text_margin, ly)

        d_spine = Drawing(spine_qr_size, spine_qr_size)
        d_spine.add(spine_qr)
        spine_qr_x = spine_x + (spine_width - spine_qr_size) / 2
        spine_qr_y = y_start + 5 * mm
        renderPDF.draw(d_spine, c, spine_qr_x, spine_qr_y)

        # Upright "UUID" Label
        c.setFont("Helvetica-Bold", 5)
        c.drawCentredString(spine_x + (spine_width / 2), spine_qr_y + spine_qr_size + 1.5 * mm, "UUID")

        # 5. Save
        c.showPage()
        c.save()
        print(f"Successfully created '{output_path}'")