import os
import traceback
from PySide6.QtCore import QRunnable, Slot, QObject, Signal, Qt
from PySide6.QtWidgets import (QWizardPage, QVBoxLayout, QLabel, QPushButton,
                               QFileDialog, QLineEdit, QProgressBar, QFormLayout)
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF


class PrintWorkerSignals(QObject):
    finished = Signal(str)
    error = Signal(object)
    progress = Signal(int)


class PrintWorker(QRunnable):
    def __init__(self, wizard, gui, config=None):
        super().__init__()
        self.wizard = wizard
        self.gui = gui
        self.signals = PrintWorkerSignals()
        self.config = config or {}

    @Slot()
    def run(self):
        """The actual PDF generation logic running in the background thread."""
        try:
            output_path = os.path.join(self.config['output_dir'], "bluray_cover.pdf")
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

        # registerField allows the wizard to remember this across pages
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

        # Input fields
        self.title_in = QLineEdit("My Awesome Collection")
        self.desc_in = QLineEdit("A collection of archival data and media.")
        self.tech_in = QLineEdit("4K UHD | HDR10 | ATMOS")
        self.meta_in = QLineEdit("Published 2024. Archival Grade.")
        self.qr_in = QLineEdit("https://example.com")

        # Register fields for the worker
        page.registerField("disc_title", self.title_in)
        page.registerField("description", self.desc_in)
        page.registerField("tech_doc", self.tech_in)
        page.registerField("metadata", self.meta_in)
        page.registerField("qr_data", self.qr_in)

        layout.addRow("Disc Title:", self.title_in)
        layout.addRow("Description:", self.desc_in)
        layout.addRow("Technical (Bottom Front):", self.tech_in)
        layout.addRow("Metadata (Bottom Back):", self.meta_in)
        layout.addRow("QR Code Link/Data:", self.qr_in)

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

        self.run_btn = QPushButton("Create PDF Now")
        self.run_btn.clicked.connect(self._trigger_generation)

        self.pbar = QProgressBar()
        self.status_lbl = QLabel("Ready to generate.")

        layout.addWidget(QLabel("Where should the PDF be saved?"))
        layout.addWidget(btn)
        layout.addWidget(path_display)
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

    def _trigger_generation(self):
        # Pull data from wizard fields
        config = {
            "cover_image": self.wizard.field("cover_image"),
            "output_dir": self.wizard.field("output_dir"),
            "disc_title": self.wizard.field("disc_title"),
            "description": self.wizard.field("description"),
            "tech_doc": self.wizard.field("tech_doc"),
            "metadata": self.wizard.field("metadata"),
            "qr_data": self.wizard.field("qr_data")
        }

        self.run_btn.setEnabled(False)
        self.pbar.setRange(0, 0)  # Indeterminate progress
        self.status_lbl.setText("Generating PDF...")

        worker = PrintWorker(self.wizard, self.gui, config)
        worker.signals.finished.connect(self._on_finished)
        worker.signals.error.connect(self._on_error)
        self.gui.threadpool.start(worker)

    def _on_finished(self, path):
        self.pbar.setRange(0, 100)
        self.pbar.setValue(100)
        self.status_lbl.setText(f"Success! Saved to: {os.path.basename(path)}")
        self.run_btn.setEnabled(True)

    def _on_error(self, err_obj):
        self.pbar.setRange(0, 100)
        self.status_lbl.setText("Error occurred.")
        self.run_btn.setEnabled(True)
        print(err_obj['msg'])

    def generate_pdf(self, output_path, data):
        output_filename = os.path.join(data["output_dir"], "bluray_insert.pdf")
        c = canvas.Canvas(output_filename, pagesize=landscape(A4))
        page_width, page_height = landscape(A4)

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
        c.setFillColorRGB(0.0, 0.2, 0.6)  # Dark Blue
        c.rect(x_start, banner_y, total_width, banner_height, stroke=0, fill=1)

        c.setFillColorRGB(1, 1, 1)  # White text
        c.setFont("Helvetica-Bold", 14)
        # Banner Text - Front
        c.drawCentredString(front_x + (panel_width / 2), banner_y + (banner_height / 2) - 1.5 * mm,
                            "COLLECTOR'S EDITION")
        # Banner Text - Back
        c.drawCentredString(x_start + (panel_width / 2), banner_y + (banner_height / 2) - 1.5 * mm, "ARCHIVAL DATA")

        # --- Setup Text Styles for Paragraphs ---
        styles = getSampleStyleSheet()

        style_desc = ParagraphStyle(
            'Description',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,  # Line spacing
            alignment=0  # Left align
        )

        style_tech = ParagraphStyle(
            'Tech',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            alignment=1,  # Center align
            textColor='black'
        )

        style_meta = ParagraphStyle(
            'Metadata',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',  # Italics
            fontSize=8,
            leading=10,
            alignment=1  # Center align
        )

        # --- Test Cases ---
        disc_title_text = data["disc_title"]
        description_text = data["description"]
        tech_doc_text = data["tech_doc"]
        metadata_text = data["metadata"]
        qr_data = data["qr_data"]

        # --- FRONT PANEL RENDERING ---
        # Disc Title
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(front_x + (panel_width / 2), y_start + cover_height - 25 * mm, disc_title_text)

        # Description Paragraph
        p_desc = Paragraph(description_text, style_desc)
        # Paragraphs need to be wrapped to a specific width/height, then drawn
        text_margin = 10 * mm
        avail_text_width = panel_width - (text_margin * 2)
        p_desc.wrapOn(c, avail_text_width, 40 * mm)
        p_desc.drawOn(c, front_x + text_margin, y_start + cover_height - 50 * mm)

        # Front Image (Preserving Aspect Ratio)
        image_filename = data["cover_image"]
        img_box_width = 100 * mm
        img_box_height = 70 * mm
        img_x = front_x + (panel_width - img_box_width) / 2
        img_y = y_start + 35 * mm  # Place it above the tech doc area

        if os.path.exists(image_filename):
            # preserveAspectRatio=True scales the image to fit the bounding box without stretching
            # anchor='c' centers it within that bounding box
            c.drawImage(image_filename, img_x, img_y, width=img_box_width, height=img_box_height,
                        preserveAspectRatio=True, anchor='c')
        else:
            c.setStrokeColorRGB(0.7, 0.7, 0.7)
            c.rect(img_x, img_y, img_box_width, img_box_height, stroke=1, fill=0)
            c.setFillColorRGB(0.5, 0.5, 0.5)
            c.setFont("Helvetica", 10)
            c.drawCentredString(img_x + (img_box_width / 2), img_y + (img_box_height / 2), "[IMAGE PLACEHOLDER]")

        # Technical Documentation
        p_tech = Paragraph(tech_doc_text, style_tech)
        p_tech.wrapOn(c, avail_text_width, 20 * mm)
        p_tech.drawOn(c, front_x + text_margin, y_start + 10 * mm)

        # --- BACK PANEL RENDERING ---
        # Disc Title (Same as front)
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(x_start + (panel_width / 2), y_start + cover_height - 25 * mm, disc_title_text)

        # High Capacity QR Code
        qr_size = 50 * mm
        qr_widget = qr.QrCodeWidget(qr_data)
        qr_widget.barLevel = 'Q'  # High error correction for density
        qr_widget.barWidth = qr_size
        qr_widget.barHeight = qr_size

        # Wrap in a Drawing and render to PDF canvas
        d = Drawing(qr_size, qr_size)
        d.add(qr_widget)
        qr_render_x = x_start + (panel_width - qr_size) / 2
        qr_render_y = y_start + 50 * mm
        renderPDF.draw(d, c, qr_render_x, qr_render_y)

        # Metadata (Italics)
        p_meta = Paragraph(metadata_text, style_meta)
        p_meta.wrapOn(c, avail_text_width, 30 * mm)
        p_meta.drawOn(c, x_start + text_margin, y_start + 15 * mm)

        # --- SPINE RENDERING ---
        c.setFont("Helvetica-Bold", 10)
        c.setFillColorRGB(0, 0, 0)
        c.saveState()
        c.translate(spine_x + (spine_width / 2), y_start + (cover_height / 2))
        c.rotate(90)
        c.drawCentredString(0, 0, disc_title_text)
        c.restoreState()

        # 4. Save
        c.showPage()
        c.save()
        print(f"Successfully created '{output_filename}'")

