import sys
import os
import subprocess
import re
import urllib.request
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QComboBox, QProgressBar
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QPixmap
from pytube import YouTube

class YouTubeDownloader(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('YouTube Video Downloader')
        self.setGeometry(100, 100, 600, 350)
        
        self.label = QLabel('Enter video URL:', self)
        self.label.setFont(QFont('Arial', 12))
        
        self.url_input = QLineEdit(self)
        self.url_input.setFont(QFont('Arial', 11))
        self.url_input.setPlaceholderText('Enter video URL')
        self.url_input.textChanged.connect(self.update_video_info)
        
        self.preview_label = QLabel(self)
        self.preview_label.setFixedSize(320, 180)
        self.preview_label.setAlignment(Qt.AlignCenter)
        
        self.quality_label = QLabel('Select quality:', self)
        self.quality_label.setFont(QFont('Arial', 12))
        
        self.quality_combo = QComboBox(self)
        self.quality_combo.setFont(QFont('Arial', 11))
        
        self.download_button = QPushButton('Скачать', self)
        self.download_button.setFont(QFont('Arial', 12))
        self.download_button.clicked.connect(self.start_download)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setValue(0)
        
        vbox = QVBoxLayout()
        vbox.addWidget(self.label)
        vbox.addWidget(self.url_input)
        vbox.addWidget(self.preview_label)
        vbox.addWidget(self.quality_label)
        vbox.addWidget(self.quality_combo)
        vbox.addWidget(self.download_button)
        vbox.addWidget(self.progress_bar)
        vbox.setAlignment(Qt.AlignCenter)
        
        self.setLayout(vbox)
        
    def sanitize_filename(self, filename):
        return re.sub(r'[\\/*?:"<>|]', "", filename)

    def update_video_info(self):
        url = self.url_input.text()
        if url:
            try:
                yt = YouTube(url)
                self.update_preview(yt.thumbnail_url)
                self.update_quality_options(yt)
                
                
            except Exception as e:
                print(f"Error loading video information: {e}")

    def update_preview(self, thumbnail_url):
        try:
            data = urllib.request.urlopen(thumbnail_url).read()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            self.preview_label.setPixmap(pixmap.scaled(320, 180, Qt.KeepAspectRatio))
            
            self.progress_bar.setValue(0)
        except Exception as e:
            print(f"Error loading preview: {e}")

    def update_quality_options(self, yt):
        self.quality_combo.clear()
        streams = yt.streams.filter(adaptive=True, file_extension='mp4')
        for stream in streams:
            self.quality_combo.addItem(f"{stream.resolution} - {stream.fps}fps", stream.itag)
        self.quality_combo.addItem("Download audio only (MP3)", "audio")

    def start_download(self):
        url = self.url_input.text()
        itag = self.quality_combo.currentData()
        self.download_thread = DownloadThread(url, itag)
        self.download_thread.progress.connect(self.update_progress)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def download_finished(self, success, message):
        self.progress_bar.setValue(100)
        if success:
            self.url_input.setText('')
        else:
            self.url_input.setText(f"Error: {message}")

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, url, itag):
        super().__init__()
        self.url = url
        self.itag = itag

    def run(self):
        try:
            yt = YouTube(self.url)
            if self.itag == "audio":
                audio_stream = yt.streams.filter(only_audio=True, file_extension='mp4').first()
                if audio_stream:
                    audio_file = audio_stream.download(download_path, filename='audio.mp4')
                    temp_audio_file = os.path.join(download_path, 'temp_audio.mp4')
                    final_output_file = os.path.join(download_path, sanitize_filename(yt.title) + ".mp3")
                    os.rename(audio_file, temp_audio_file)
                    command = [
                        ffmpeg_path, '-y', '-i', temp_audio_file, '-q:a', '0', '-map', 'a', final_output_file
                    ]
                    subprocess.run(command, check=True)
                    os.remove(temp_audio_file)
                    self.finished.emit(True, f"Audio '{yt.title}' successfully downloaded to {final_output_file}")
                else:
                    self.finished.emit(False, "No audio found.")
            else:
                video_stream = yt.streams.get_by_itag(self.itag)
                audio_stream = yt.streams.filter(only_audio=True, file_extension='mp4').first()
                if video_stream and audio_stream:
                    video_file = video_stream.download(download_path, filename='video.mp4')
                    audio_file = audio_stream.download(download_path, filename='audio.mp4')
                    temp_video_file = os.path.join(download_path, 'temp_video.mp4')
                    temp_audio_file = os.path.join(download_path, 'temp_audio.mp4')
                    final_output_file = os.path.join(download_path, sanitize_filename(yt.title) + ".mp4")
                    os.rename(video_file, temp_video_file)
                    os.rename(audio_file, temp_audio_file)
                    command = [
                        ffmpeg_path, '-y', '-i', temp_video_file, '-i', temp_audio_file, 
                        '-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental', final_output_file
                    ]
                    subprocess.run(command, check=True)
                    os.remove(temp_video_file)
                    os.remove(temp_audio_file)
                    self.finished.emit(True, f"Video'{yt.title}' successfully downloaded and merged into {final_output_file}")
                else:
                    self.finished.emit(False, "No video or audio found.")
        except Exception as e:
            self.finished.emit(False, f"Error: {e}")

class CFGfromTXT:
    def __init__(self, cfg_path):
        self.cfg_path = cfg_path
        self.is_ixists()
    
    def is_ixists(self):
        is_ixist = os.path.exists(self.cfg_path)
        if is_ixist:
            self.get_all_cfgs()
            return True
        else:
            print('Path not found')
            return False
    
    def get_all_cfgs(self):
        with open(self.cfg_path, 'r') as file:
            lines = file.readlines()
        self.result_dict = {}
        for item in lines:
            key, value = item.strip().split('=')
            self.result_dict[key.strip()] = value.strip()
        print(self.result_dict)
    
    def get_cfg_value(self, key):
        return self.result_dict[key]
    
def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)

if __name__ == '__main__':
    cfg = CFGfromTXT('cfg.txt')
    if cfg.is_ixists():
        download_path = cfg.get_cfg_value('dwn_path')
        ffmpeg_path = cfg.get_cfg_value('ffmpeg_path')
    else:
        download_path = '.'
        ffmpeg_path = 'ffmpeg.exe'

    app = QApplication(sys.argv)
    window = YouTubeDownloader()
    window.show()
    sys.exit(app.exec_())