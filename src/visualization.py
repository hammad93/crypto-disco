'''
Visualizes the data written to the disc. It should emulate how the more data on the back of the disk the darker it is
https://doc.qt.io/qtforpython-6/examples/example_charts_nesteddonuts.html#example-charts-nesteddonuts
https://doc.qt.io/qtforpython-6/PySide6/QtGraphs/QPieSlice.html#PySide6.QtGraphs.QPieSlice.setColor
https://lospec.com/palette-list/grayscale-16


'''
import os
from PySide6.QtCore import Qt, QTimer, Slot, QPointF
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QGridLayout, QWidget, QGraphicsTextItem
from PySide6.QtCharts import QChart, QChartView, QPieSeries, QPieSlice

import ecc
import utils
import config

from random import randrange
from functools import partial

class NestedDonuts(QWidget):
    def __init__(self, file_list, disc_type):
        super().__init__()
        self.file_list = file_list
        self.disc_type = disc_type
        #self.setMinimumSize(800, 600)
        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.chart = self.chart_view.chart()
        self.chart.setBackgroundBrush(QColor(0,0,0,0))
        self.chart.legend().setVisible(False)
        self.chart.setAnimationOptions(QChart.AllAnimations)
        self.colors = config.donut_chart["slices_colors"]

        self.min_size = 0.1
        self.max_size = 0.9
        self.donut_count = 3

        self.setup_donuts()

        # create main layout
        self.main_layout = QGridLayout(self)
        self.main_layout.addWidget(self.chart_view, 1, 1)
        self.setLayout(self.main_layout)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_rotation)
        self.update_timer.start(1250)

    def reset(self):
        self.chart_view.chart().removeAllSeries()
        self.setup_donuts()

    def update_all(self, file_list, disc_type):
        self.file_list = file_list
        self.disc_type = disc_type
        self.reset()

    def update_files(self, file_list):
        self.file_list = file_list
        self.reset()

    def update_disc_type(self, disc_type):
        self.disc_type = disc_type
        self.reset()

    def setup_slice(self, donut, slc, index, color="NA"):
        if color == "NA":
            # calculate color based on other params
            color = self.colors[index]
        slc.setColor(QColor(color))
        slc.setLabelVisible(True)
        slc.setLabelColor(Qt.white)
        slc.setLabelPosition(QPieSlice.LabelInsideTangential)
        # Connection using an extra parameter for the slot
        slc.hovered[bool].connect(partial(self.explode_slice, slc=slc))
        donut.append(slc)
        size = (self.max_size - self.min_size) / self.donut_count
        donut.setHoleSize(self.min_size + index * size)
        donut.setPieSize(self.min_size + (index + 1) * size)
        return donut, slc

    def setup_donuts(self):
        self.donuts = []
        # define gray scale, darkest to lightest
        # Files, ECC, Clones, Unused
        total_bytes = 0

        # setup inner most donut (files)
        donut_index = 0
        files_donut = QPieSeries()
        for i in range(len(self.file_list)):
            file = self.file_list[i]
            total_bytes += file["file_size"]
            files_slc = QPieSlice(str(i), 1)
            files_slc.metadata_text = f"[{i}] {file["file_name"]} ({utils.total_size_str(file['file_size'])})"
            files_donut, files_slc = self.setup_slice(files_donut, files_slc, donut_index)
        self.donuts.append(files_donut)
        self.chart_view.chart().addSeries(files_donut)

        # setup ECC donuts
        donut_index = 1
        ecc_donut = QPieSeries()
        for i in range(len(self.file_list)):
            file = self.file_list[i]
            if file["ecc_checked"]:
                ecc_estimate = ecc.estimate_total_size(os.path.join(file["directory"], file["file_name"]))
                total_bytes += ecc_estimate
                ecc_slc = QPieSlice(str(i), ecc_estimate)
                ecc_slc.metadata_text = f"ECC for [{i}] {file['file_name']} ({utils.total_size_str(ecc_estimate)})"
                ecc_donut, ecc_slc = self.setup_slice(ecc_donut, ecc_slc, donut_index)
        self.donuts.append(ecc_donut)
        self.chart_view.chart().addSeries(ecc_donut)

        # setup totals donuts
        donut_index = 2
        totals_donut = QPieSeries()
        used_slc = QPieSlice(utils.total_size_str(total_bytes), total_bytes)
        used_slc.metadata_text = f"Used Space: {utils.total_size_str(total_bytes)}"
        totals_donut, used_slc = self.setup_slice(totals_donut, used_slc, donut_index)
        remaining_space = utils.disc_type_bytes(self.disc_type) - total_bytes
        remaining_slc = QPieSlice(utils.total_size_str(remaining_space), remaining_space)
        remaining_slc.metadata_text = f"Remaining Space: {utils.total_size_str(remaining_space)}"
        totals_donut, remaining_slc = self.setup_slice(totals_donut, remaining_slc, donut_index,
                                                       config.donut_chart["remaining_color"])
        self.donuts.append(totals_donut)
        self.chart_view.chart().addSeries(totals_donut)

    @Slot()
    def update_rotation(self):
        for donut in self.donuts:
            phase_shift = randrange(-50, 100)
            donut.setPieStartAngle(donut.pieStartAngle() + phase_shift)
            donut.setPieEndAngle(donut.pieEndAngle() + phase_shift)

    def explode_slice(self, exploded, slc):
        if exploded:
            self.update_timer.stop()
            slice_startangle = slc.startAngle()
            slice_endangle = slc.startAngle() + slc.angleSpan()

            donut = slc.series()
            idx = self.donuts.index(donut)
            for i in range(idx + 1, len(self.donuts)):
                self.donuts[i].setPieStartAngle(slice_endangle)
                self.donuts[i].setPieEndAngle(360 + slice_startangle)
            # Create or update the metadata text item
            if not hasattr(self, 'metadata_text_item'):
                self.metadata_text_item = QGraphicsTextItem()
                self.chart_view.scene().addItem(self.metadata_text_item)
            # Update the text with placeholder metadata
            self.metadata_text_item.setPlainText(slc.metadata_text)
            self.metadata_text_item.setPos(QPointF(0, self.chart_view.height() - 25))
        else:
            for donut in self.donuts:
                donut.setPieStartAngle(0)
                donut.setPieEndAngle(360)

            self.update_timer.start()
            # hide metadata text
            self.metadata_text_item.setPlainText("")
            if hasattr(self, 'metadata_text_item'):
                self.metadata_text_item.setPlainText("")
        slc.setExploded(exploded)
