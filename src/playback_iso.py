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
from datetime import datetime, timedelta

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
            'output_path': self.gui.output_path,
            'chapters': self.chapters
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
        # create staged output directory
        output_dir = os.path.join('.',f'output_{utils.datetime_str()}')
        os.makedirs(output_dir)
        encoded = []
        for index, file in enumerate(self.gui.file_list):
            if file['default_file']:
                continue
            input_path = os.path.join(file['directory'], file['file_name'])
            input_extension = input_path.split(".")[-1]
            output_prefix = os.path.join(output_dir, str(os.path.basename(input_path).removesuffix(input_extension)))
            video_output = output_prefix + "264"
            audio_output = output_prefix + "ac3"
            # process video
            video_command = [
                ffmpeg_exe,
                '-i', input_path,
                # scale all videos to the same size and include black letter boxing and other fixes
                '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1',
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
                '-i', input_path,
                '-c:a', 'ac3',
                '-b:a', '640k',
                '-ar', '48000',
                audio_output
            ]
            self.signals.progress_text.emit(f"Encoding Audio for {input_path}")
            run_command(audio_command, self.signals.progress_text.emit)
            # output done, save parameters for Muxing
            encoded.append({'video': video_output, 'audio': audio_output})
            self.signals.progress.emit((index+1)/len(self.gui.file_list) * 100)

        # https://justdan96.github.io/tsMuxer/docs/USAGE.html
        # https://github.com/hammad93/crypto-disco/issues/31
        if len(self.playback_config['chapters']) < 2: # only one, potentially long, video file
            chapters = "--auto-chapters=1"
        else:
            # start first chapter at 0 and remove last chapter that marks the end
            formatted_chapters = self.playback_config['chapters'][:-1]
            formatted_chapters.insert(0, "00:00:00.000")
            chapters = f"--custom-chapters={';'.join(formatted_chapters)}"
        tsmuxer_config = os.path.join(output_dir, 'crypto-disco-playback.meta')
        with open(tsmuxer_config, 'w') as f:
            f.write(f'MUXOPT --no-pcr-on-video-pid --insertBlankPL --blu-ray {chapters}\n')
            f.write('V_MPEG4/ISO/AVC, ')
            for index, playback in enumerate(encoded):
                f.write(f'{"+" if index > 0 else ""}"{playback['video']}"')
            f.write(', fps=23.976\nA_AC3, ')
            for index, playback in enumerate(encoded):
                f.write(f'{"+" if index > 0 else ""}"{playback['audio']}"')
            f.write(', lang=eng')
        mux_command = [
            tsmuxer_path,
            tsmuxer_config,
            self.playback_config['output_path'],
        ]
        self.signals.progress_text.emit(f"Muxing and finalizing output for {self.playback_config['output_path']}")
        run_command(mux_command, self.signals.progress_text.emit)
        self.signals.result.emit("Done")
        return True

    def probe_files_page(self):
        page = QWizardPage()
        page.setTitle("Files Validation")
        layout = QVBoxLayout()

        label = QLabel("Probing files, please click start. All files must be validated before continuing.")
        layout.addWidget(label)

        probe_progress = QProgressBar()
        probe_progress.setRange(0, 100)
        self.probe_progress = probe_progress
        layout.addWidget(self.probe_progress)

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
        chapters = []
        def get_timedelta(time_str):
            t = datetime.strptime(time_str, "%H:%M:%S.%f")
            return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second, microseconds=t.microsecond)
        for index, file in enumerate(self.gui.file_list):
            if file['default_file']:
                continue
            path = os.path.join(file['directory'], file['file_name'])
            self.probe_progress_text.appendPlainText(f"Probing {path} . . .")
            try:
                probe = pyffmpeg.FFprobe(path)
                self.probe_progress_text.appendPlainText(f"{probe.metadata}\nDone probing {file['file_name']}")
                if len(chapters) < 1:
                    chapters.append(probe.duration)
                else:
                    duration = get_timedelta(probe.duration)
                    last_chapter = get_timedelta(chapters[-1])
                    total_duration = last_chapter + duration
                    total_seconds = int(total_duration.total_seconds())
                    # hh:mm:ss.zzz
                    chapters.append(f"{(total_seconds // 3600):02}:"
                                    f"{((total_seconds % 3600) // 60):02}:"
                                    f"{(total_seconds % 60):02}."
                                    f"{(int(total_duration.microseconds / 1000)):03}")

            except Exception as e:
                self.probe_progress_text.appendPlainText(f"Error when opening {path} with pyffmpeg.\n{e}")
                return False
            self.probe_progress.setValue(((index+1)/len(self.gui.file_list)) * 100)
        self.chapters = chapters
        self.probe_processed_text.setText("Done.")
        return True