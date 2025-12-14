'''
Visualizes the data written to the disc. It should emulate how the more data on the back of the disk the darker it is
https://doc.qt.io/qtforpython-6/PySide6/QtGraphs/QPieSlice.html#PySide6.QtGraphs.QPieSlice.setColor
https://lospec.com/palette-list/grayscale-16


'''
import sys

from PIL.ImageOps import grayscale
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QApplication, QGridLayout, QWidget
from PySide6.QtCharts import QChart, QChartView, QPieSeries, QPieSlice


from random import randrange
from functools import partial

class NestedDonuts(QWidget):
    def __init__(self):
        super().__init__()
        #self.setMinimumSize(800, 600)
        self.donuts = []
        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.chart = self.chart_view.chart()
        self.chart.legend().setVisible(False)
        #self.chart.setTitle("Nested donuts demo")
        self.chart.setAnimationOptions(QChart.AllAnimations)

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

    def setup_donuts(self):
        # define gray scale, darkest to lightest
        # Files, ECC, Clones, Unused
        gray_scale = ["#646464", "#7e7e7e", "#ababab", "#bdbdbd"]
        for i in range(self.donut_count):
            donut = QPieSeries()
            slccount = randrange(3, 6)
            for j in range(slccount):
                value = randrange(100, 200)

                slc = QPieSlice(str(value), value)
                slc.setColor(QColor(gray_scale[i]))
                slc.setLabelVisible(True)
                slc.setLabelColor(Qt.white)
                slc.setLabelPosition(QPieSlice.LabelInsideTangential)

                # Connection using an extra parameter for the slot
                slc.hovered[bool].connect(partial(self.explode_slice, slc=slc))

                donut.append(slc)
                size = (self.max_size - self.min_size) / self.donut_count
                donut.setHoleSize(self.min_size + i * size)
                donut.setPieSize(self.min_size + (i + 1) * size)

            self.donuts.append(donut)
            self.chart_view.chart().addSeries(donut)

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
        else:
            for donut in self.donuts:
                donut.setPieStartAngle(0)
                donut.setPieEndAngle(360)

            self.update_timer.start()

        slc.setExploded(exploded)