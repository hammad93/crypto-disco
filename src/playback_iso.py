from PySide6.QtCore import QRunnable, Slot, Qt, QFileInfo
from PySide6.QtWidgets import (QWizardPage, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFileDialog, QLineEdit,
                               QDialog, QComboBox, QTableWidget, QTableWidgetItem, QMessageBox, QProgressBar,
                               QPlainTextEdit)
import traceback
import config
import utils
import pathlib
import os
import subprocess
import platform
import pyffmpeg

class PlaybackWorker(QRunnable):
    def __init__(self, wizard, gui, playback_config=False):
        super().__init__()
        self.wizard = wizard
        self.gui = gui
        self.signals = utils.WorkerSignals()
        self.playback_config = playback_config or {}

    @Slot()
    def run(self):
        try:
            self.encode_mux()
        except Exception as e:
            msg = traceback.format_exc()
            print(msg)
            self.signals.error.emit({"exception": e, "msg": msg})

    def start(self):
        playback_config = {
            'output_path': self.gui.output_path
        }
        playback_worker = PlaybackWorker(self.wizard, self.gui, playback_config)
        playback_worker.signals.progress.connect(self.mux_progress_bar.setValue)
        playback_worker.signals.progress_text.connect(self.progress_text.appendPlainText)
        playback_worker.signals.error.connect(lambda e: utils.error_popup("Error Muxing Media for Playback", e))
        playback_worker.signals.result.connect(self.mux_label.setText)
        self.gui.threadpool.start(playback_worker)

    def encode_mux(self):
        tsmuxer_path = utils.get_binary_path("tsMuxeR")
        ff = pyffmpeg.FFmpeg()
        ffmpeg_exe = ff.get_ffmpeg_bin()
        def run_command(command, callback=False):
            with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                  bufsize=1) as process:
                # Read from stdout in real-time
                if callback:
                    for line in process.stdout:
                        clean_line = line.strip()
                        print(clean_line)
                        callback(clean_line)
            return True
        encoded = []
        for file in self.gui.file_list:
            if file['default_file']:
                continue
            input_path = os.path.join(file['directory'], file['file_name'])
            input_extension = input_path.split(".")[-1]
            output_prefix = input_path.removesuffix(input_extension)
            video_output = output_prefix + "264"
            audio_output = output_prefix + "wav"
            # process video
            video_command = [
                ffmpeg_exe,
                '-i', input_path,
                '-c:v', 'libx264',
                '-profile:v', 'high',
                '-level', '4.1',
                '-pix_fmt', 'yuv420p',
                '-r', '24000/1001',
                '-fps_mode', 'cfr',
                '-b:v', '18M',
                '-maxrate', '40M',
                '-bufsize', '30M',
                '-x264-params',
                'bluray-compat=1:ref=3:bframes=2:b-adapt=0:b-pyramid=none:keyint=24:min-keyint=24:scenecut=0:open_gop=0:aud=1:nal-hrd=vbr',
                '-f', 'h264',
                video_output,
            ]
            self.signals.progress_text.emit(f"Encoding Video for {input_path}")
            run_command(video_command, self.signals.progress_text.emit)
            # process audio
            audio_command = [
                ffmpeg_exe,
                '-i', f'{output_prefix}264',
                '-c:a', 'pcm_s16le',
                '-ar', '48000',
                '-ac', '2',
                audio_output
            ]
            self.signals.progress_text.emit(f"Encoding Audio for {input_path}")
            run_command(audio_command, self.signals.progress_text.emit)
            # output done, save parameters for Muxing
            encoded.append({'video': video_output, 'audio': audio_output})

        with open('tsMuxeR.txt', 'w') as f:
            f.write('MUXOPT --blu-ray --auto-chapters=5\n')
            for playback in encoded:
                f.write(f'V_MPEG4/ISO/AVC, "{playback['video']}", fps=23.976\n')
            for playback in encoded:
                f.write(f'A_LPCM, "{playback['audio']}", lang=eng')
        mux_command = [
            tsmuxer_path,
            'tsMuxeR.txt',
            self.playback_config['output'],
        ]
        self.signals.progress_text.emit(f"Muxing and finalizing output for {self.playback_config['output']}")
        run_command(mux_command, self.signals.progress_text.emit)
        self.signals.result("Done")
        return True

    def probe_files_page(self):
        page = QWizardPage()
        page.setTitle("Files Validation")
        layout = QVBoxLayout()

        label = QLabel("Probing files, please click start. All files must be validated before continuing.")
        layout.addWidget(label)

        probe_progress = QProgressBar()
        probe_progress.setRange(0, 100)
        layout.addWidget(probe_progress)

        self.probe_processed_text = QLineEdit()
        self.probe_processed_text.setPlaceholderText("Processing . . .")
        self.probe_processed_text.setReadOnly(True)
        # prevent going to next page until probing is complete
        page.registerField("probe*", self.probe_processed_text)

        probe_progress_text = QPlainTextEdit()
        probe_progress_text.setReadOnly(True)
        self.probe_progress_text = probe_progress_text
        layout.addWidget(self.probe_progress_text)

        probe_start_button = QPushButton("Start")
        probe_start_button.clicked.connect(lambda: self.probe_files())
        layout.addWidget(probe_start_button)

        page.setLayout(layout)
        page.setFinalPage(False)
        self.probe_files_page_wizard = page
        return page

    def mux_page(self):
        page = QWizardPage()
        page.setTitle("Converting and Muxing Files to Playback .iso Image")
        layout = QVBoxLayout()

        # label instructing user whats occuring
        label = QLabel("Encoding and Muxing Files")
        layout.addWidget(label)
        # progress bar
        self.mux_progress_bar = QProgressBar()
        self.mux_progress_bar.setRange(0, 100)
        layout.addWidget(self.mux_progress_bar)
        # text box for progress updates
        self.progress_text = QPlainTextEdit()
        self.progress_text.setReadOnly(True)
        layout.addWidget(self.progress_text)
        # start button that runs the new thread
        start_button = QPushButton("Start")
        start_button.clicked.connect(lambda: self.start())
        self.start_button = start_button
        layout.addWidget(self.start_button)
        # hidden label that changes to signal everything is done
        self.mux_label = QLineEdit()
        self.mux_label.setPlaceholderText("Processing . . .")
        self.mux_label.setReadOnly(True)
        page.registerField("mux*", self.mux_label)

        page.setLayout(layout)
        page.setFinalPage(True)
        self.mux_page_wizard = page
        return page

    def probe_files(self):
        for file in self.gui.file_list:
            if file['default_file']:
                continue
            path = os.path.join(file['directory'], file['file_name'])
            self.probe_progress_text.appendPlainText(f"Probing {path} . . .")
            try:
                probe = pyffmpeg.FFprobe(path)
                self.probe_progress_text.appendPlainText(f"{probe.metadata}\nDone probing {file['file_name']}")
            except Exception as e:
                self.probe_progress_text.appendPlainText(f"Error when opening {path} with pyffmpeg.\n{e}")
                return False
        self.probe_processed_text.setText("Done.")
        return True