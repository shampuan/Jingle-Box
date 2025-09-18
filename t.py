#!/usr/bin/env python3

import sys
import os
import json
import struct
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QPushButton, QFrame,
                             QMenuBar, QAction, QFileDialog, QSizePolicy, QMenu, QMessageBox, QLabel)
from PyQt5.QtCore import Qt, QUrl, QTimer
from PyQt5.QtGui import QPainter, QColor, QIcon, QFont
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QAudioProbe, QAudioBuffer, QAudioFormat

# --- Custom VU Meter Bar Class ---
class VUMeterBar(QWidget):
    def __init__(self, bar_color=QColor("#00ff8d"), parent=None):
        super().__init__(parent)
        self._level = 0.0
        self._peak_hold_level = 0.0
        self._peak_hold_timer = QTimer(self)
        self._peak_hold_timer.setSingleShot(True)
        self._peak_hold_timer.timeout.connect(self._decay_peak_hold)
        
        self.bar_color = bar_color
        self.setFixedSize(25, 480) 
        self.setStyleSheet("background-color: black; border: none; border-radius: 3px;")

    def set_level(self, level):
        level = max(0.0, min(1.0, level))
        if self._level != level:
            self._level = level
            self.update()

            if level > self._peak_hold_level:
                self._peak_hold_level = level
                self._peak_hold_timer.start(500)
            elif not self._peak_hold_timer.isActive():
                 self._peak_hold_level = level
                 self.update()
                 self._peak_hold_timer.stop()
                 
    def _decay_peak_hold(self):
        self._peak_hold_level = max(0.0, self._peak_hold_level * 0.8)
        if self._peak_hold_level > 0.01:
            self._peak_hold_timer.start(50)
        else:
            self._peak_hold_level = 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        bar_height = int(rect.height() * self._level)
        
        painter.setBrush(QColor(self.bar_color))
        painter.setPen(Qt.NoPen)
        painter.drawRect(rect.left(), rect.bottom() - bar_height, rect.width(), bar_height)

        if self._peak_hold_level > 0.0:
            peak_pixel_height = 2
            peak_y_pos = int(rect.height() * (1 - self._peak_hold_level))
            
            painter.setBrush(QColor(255, 255, 0, 200))
            painter.drawRect(rect.left(), peak_y_pos, rect.width(), peak_pixel_height)

        super().paintEvent(event)
# --- VU Meter Sınıfı Sonu ---

# Ana pencereyi oluşturacak QMainWindow sınıfı
class JingleBox(QMainWindow):
    def __init__(self):
        super().__init__()
        self.button_states = {}
        self.button_map = {}
        self.last_clicked_button = None
        self.media_player = QMediaPlayer()
        self.active_button = None
        self.icon_path = None
        self.left_vu_meter = None
        self.right_vu_meter = None
        
        # Dil ayarları ve sözlük
        self.current_lang = 'tr'
        self.translations = {
            'tr': {
                'menu_file': 'Dosya',
                'menu_open': 'Aç',
                'menu_save': 'Kaydet',
                'menu_help': 'Yardım',
                'menu_about': 'Hakkında',
                'button_empty': 'Boş',
                'button_stop': 'DUR',
                'button_save_palette': 'Bu Paleti Kaydet',
                'button_open_palette': 'Kayıttan Palet Aç',
                'context_assign': 'Ses Ata',
                'context_delete': 'Sil',
                'dialog_select_file': 'Ses Dosyası Seç',
                'dialog_file_filter_audio': 'Ses Dosyaları (*.mp3 *.wav *.ogg);;Tüm Dosyalar (*)',
                'dialog_save_palette': 'Paleti Kaydet',
                'dialog_load_palette': 'Palet Yükle',
                'message_no_sound': 'Bu butona atanmış bir ses dosyası yok.',
                'message_playing': 'Ses çalınıyor',
                'message_stopped': 'Ses durduruldu.',
                'message_assigned': 'Ses atandı.',
                'message_deleted': 'Ses silindi.',
                'message_saved_success': 'Palet başarıyla kaydedildi.',
                'message_save_error': 'Palet kaydedilirken bir hata oluştu.',
                'message_loaded_success': 'Palet başarıyla yüklendi.',
                'message_load_error': 'Palet yüklenirken bir hata oluştu.',
                'message_invalid_data': 'Hatalı veri',
                'about_title': 'Jingle Box Hakkında',
                'about_version': 'Versiyon',
                'about_license': 'Lisans',
                'about_lang': 'Programlama dili',
                'about_gui': 'GUI',
                'about_developer': 'Geliştirici',
                'about_program_desc': 'Bu program, radyo çalışmaları ya da çeşitli okul, tiyatro gibi etkinliklerde ses efektleri çalmaya yarar.',
                'about_no_warranty': 'Bu program hiçbir garanti getirmiyor.'
            },
            'en': {
                'menu_file': 'File',
                'menu_open': 'Open',
                'menu_save': 'Save',
                'menu_help': 'Help',
                'menu_about': 'About',
                'button_empty': 'Empty',
                'button_stop': 'STOP',
                'button_save_palette': 'Save This Palette',
                'button_open_palette': 'Open Palette from File',
                'context_assign': 'Assign Sound',
                'context_delete': 'Delete',
                'dialog_select_file': 'Select Sound File',
                'dialog_file_filter_audio': 'Audio Files (*.mp3 *.wav *.ogg);;All Files (*)',
                'dialog_save_palette': 'Save Palette',
                'dialog_load_palette': 'Load Palette',
                'message_no_sound': 'No sound file is assigned to this button.',
                'message_playing': 'Playing sound',
                'message_stopped': 'Sound stopped.',
                'message_assigned': 'Sound assigned.',
                'message_deleted': 'Sound deleted.',
                'message_saved_success': 'Palette successfully saved.',
                'message_save_error': 'An error occurred while saving the palette.',
                'message_loaded_success': 'Palette successfully loaded.',
                'message_load_error': 'An error occurred while loading the palette.',
                'message_invalid_data': 'Invalid data',
                'about_title': 'About Jingle Box',
                'about_version': 'Version',
                'about_license': 'License',
                'about_lang': 'Programming language',
                'about_gui': 'GUI',
                'about_developer': 'Developer',
                'about_program_desc': 'This program is for playing sound effects for radio shows or various school and theater events.',
                'about_no_warranty': 'This program comes with no warranty.'
            }
        }
        
        # VU Metre için QAudioProbe
        self.audio_probe = QAudioProbe(self)
        self.audio_probe.setSource(self.media_player)
        self.audio_probe.audioBufferProbed.connect(self._process_audio_buffer)

        self.initUI()
        
    def initUI(self):
        # Program adı ve diğer başlık olayları işte
        self.setWindowTitle("Jingle Box")
        self.setFixedSize(800, 600)

        self.find_and_set_icon()

        self.create_menu()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_vbox = QVBoxLayout(central_widget)
        main_vbox.setContentsMargins(10, 10, 10, 10)
        main_vbox.setSpacing(10)

        top_hbox = QHBoxLayout()
        top_hbox.setSpacing(10)

        self.create_button_grid(top_hbox)
        self.create_vu_meter_area(top_hbox)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)

        settings_hbox = self.create_settings_buttons()

        main_vbox.addLayout(top_hbox)
        main_vbox.addWidget(separator)
        main_vbox.addLayout(settings_hbox)
        
        self.update_language()
        
        self.show()

    def update_language(self):
        lang = self.translations[self.current_lang]
        
        # Menüleri güncelle
        self.file_menu.setTitle(lang['menu_file'])
        self.open_action.setText(lang['menu_open'])
        self.save_action.setText(lang['menu_save'])
        self.help_menu.setTitle(lang['menu_help'])
        self.about_action.setText(lang['menu_about'])

        # Butonları güncelle
        self.save_button.setText(lang['button_save_palette'])
        self.open_button.setText(lang['button_open_palette'])
        self.about_button.setText(lang['menu_about'])

        # Jingle butonlarının metinlerini güncelle
        for button in self.button_states:
            if self.button_states[button]["file_path"] is None:
                if button.text() != 'DUR' and button.text() != 'STOP':
                    button.setText(lang['button_empty'])
            
    def toggle_language(self):
        self.current_lang = 'en' if self.current_lang == 'tr' else 'tr'
        self.update_language()
        print(f"Dil {self.current_lang} olarak değiştirildi.")

    def find_and_set_icon(self):
        icon_name = "jinglebox.png"
        icon_path = None

        current_dir = os.getcwd()
        if os.path.exists(os.path.join(current_dir, icon_name)):
            icon_path = os.path.join(current_dir, icon_name)
        
        if not icon_path:
            install_path = "/usr/share/Jingle Box"
            if os.path.exists(os.path.join(install_path, icon_name)):
                icon_path = os.path.join(install_path, icon_name)
        
        if not icon_path:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            if os.path.exists(os.path.join(script_dir, icon_name)):
                icon_path = os.path.join(script_dir, icon_name)
        
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
            self.icon_path = icon_path
            print(f"İkon yüklendi: {icon_path}")
        else:
            print(f"İkon dosyası bulunamadı: {icon_name}")
            self.icon_path = None

    def create_menu(self):
        menubar = self.menuBar()
        
        self.file_menu = menubar.addMenu("Dosya")
        
        self.open_action = QAction("Aç", self)
        self.open_action.triggered.connect(self.load_palette)
        self.file_menu.addAction(self.open_action)
        
        self.save_action = QAction("Kaydet", self)
        self.save_action.triggered.connect(self.save_palette)
        self.file_menu.addAction(self.save_action)
        
        self.help_menu = menubar.addMenu("Yardım")
        self.about_action = QAction("Hakkında", self)
        self.about_action.triggered.connect(self.show_about_dialog)
        self.help_menu.addAction(self.about_action)

    def create_button_grid(self, parent_layout):
        grid = QGridLayout()
        grid.setSpacing(10)

        # Orijinal renkler
        original_colors = [
            "#ff5c5c", # Kırmızımsı
            "#ff8c5c", # Turuncu
            "#ffbc5c", # Sarımsı turuncu
            "#ffff5c", # Sarı
            "#bfff5c", # Hafif yeşilimsi sarı
            "#8cff5c", # Daha yeşil
            "#5cffbc", # Mavimsi yeşil
        ]
        
        # Renklerin doygunluğunu azaltarak yeni bir palet oluştur
        desaturated_colors = []
        for hex_color in original_colors:
            q_color = QColor(hex_color)
            hsv_color = q_color.toHsv()
            hsv_color.setHsv(hsv_color.hue(), 150, hsv_color.value())
            desaturated_colors.append(hsv_color.name())

        # Kullanıcının yeni taleplerine göre renk paletini düzenle
        vu_meter_color = "#5fa686"
        
        button_colors = [
            desaturated_colors[0], # 1. sıra (kırmızımsı)
            vu_meter_color,        # 2. sıra (yeni yeşil renk)
            vu_meter_color,        # 3. sıra (yeni yeşil renk)
            vu_meter_color,        # 4. sıra (yeni yeşil renk)
            vu_meter_color,        # 5. sıra (yeni yeşil renk)
            vu_meter_color,        # 6. sıra (yeni yeşil renk)
            desaturated_colors[2], # 7. sıra (sarımsı turuncu)
        ]

        for i in range(7):
            for j in range(5):
                button = QPushButton("Boş")
                button.setFixedSize(120, 60)
                
                self.button_states[button] = {"file_path": None}
                self.button_map[(i, j)] = button
                
                if i == 6 and j == 4:
                    button.setText("DUR")
                    button.clicked.connect(self.stop_playback)
                    button.setStyleSheet("""
                        QPushButton {
                            background-color: #e03c3c;
                            color: #ffffff;
                            border: 1px solid #902c2c;
                            border-radius: 4px;
                        }
                        QPushButton:hover {
                            background-color: #b82b2b;
                        }
                        QPushButton:pressed {
                            background-color: #8c2020;
                        }
                    """)
                else:
                    color = button_colors[i]
                    button.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {color};
                            color: #000000;
                            border: 1px solid {color};
                            border-radius: 4px;
                        }}
                        QPushButton:hover {{
                            background-color: {QColor(color).darker(120).name()};
                        }}
                        QPushButton:pressed {{
                            background-color: {QColor(color).darker(150).name()};
                        }}
                    """)
                    button.clicked.connect(self.play_sound)
                    button.setContextMenuPolicy(Qt.CustomContextMenu)
                    button.customContextMenuRequested.connect(self.show_context_menu)
                
                grid.addWidget(button, i, j)
        
        parent_layout.addLayout(grid)

    def create_vu_meter_area(self, parent_layout):
        vu_meter_container = QWidget()
        vu_meter_container.setFixedSize(60, 480)
        vu_meter_container.setStyleSheet("background-color: black; border-radius: 5px;")
        
        vu_layout = QHBoxLayout(vu_meter_container)
        vu_layout.setContentsMargins(5, 5, 5, 5)
        vu_layout.setSpacing(5)

        self.left_vu_meter = VUMeterBar()
        self.right_vu_meter = VUMeterBar()

        vu_layout.addWidget(self.left_vu_meter)
        vu_layout.addWidget(self.right_vu_meter)

        parent_layout.addWidget(vu_meter_container)
    
    def create_settings_buttons(self):
        settings_hbox = QHBoxLayout()
        settings_hbox.setSpacing(10)
        
        self.save_button = QPushButton("Bu Paleti Kaydet")
        self.save_button.clicked.connect(self.save_palette)

        self.open_button = QPushButton("Kayıttan Palet Aç")
        self.open_button.clicked.connect(self.load_palette)

        self.lang_button = QPushButton("Language")
        self.lang_button.clicked.connect(self.toggle_language)
        
        self.about_button = QPushButton("Hakkında")
        self.about_button.clicked.connect(self.show_about_dialog)
        
        settings_hbox.addWidget(self.save_button)
        settings_hbox.addWidget(self.open_button)
        settings_hbox.addWidget(self.lang_button)
        settings_hbox.addWidget(self.about_button)
        
        return settings_hbox

    def show_context_menu(self, pos):
        lang = self.translations[self.current_lang]
        menu = QMenu(self)
        assign_action = menu.addAction(lang['context_assign'])
        delete_action = menu.addAction(lang['context_delete'])
        
        self.last_clicked_button = self.sender()

        action = menu.exec_(self.last_clicked_button.mapToGlobal(pos))
        
        if action == assign_action:
            self.on_assign_sound_clicked()
        elif action == delete_action:
            self.on_delete_sound_clicked()

    def play_sound(self):
        lang = self.translations[self.current_lang]
        button = self.sender()
        
        file_path = self.button_states[button]["file_path"]
        
        if file_path:
            self.media_player.stop()
            
            media_content = QMediaContent(QUrl.fromLocalFile(file_path))
            self.media_player.setMedia(media_content)
            
            self.media_player.setVolume(25) 
            
            self.media_player.play()
            
            self.active_button = button
            print(f"{lang['message_playing']}: {file_path}")
        else:
            print(lang['message_no_sound'])

    def stop_playback(self):
        lang = self.translations[self.current_lang]
        self.media_player.stop()
        self.active_button = None
        self.left_vu_meter.set_level(0.0)
        self.right_vu_meter.set_level(0.0)
        print(lang['message_stopped'])

    def on_assign_sound_clicked(self):
        lang = self.translations[self.current_lang]
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            lang['dialog_select_file'], 
            "", 
            lang['dialog_file_filter_audio']
        )
        
        if file_path:
            self.button_states[self.last_clicked_button]["file_path"] = file_path
            
            file_name = os.path.basename(file_path)
            file_name_without_extension = os.path.splitext(file_name)[0]

            if len(file_name_without_extension) > 14:
                display_name = file_name_without_extension[:11] + "..."
            else:
                display_name = file_name_without_extension
            
            self.last_clicked_button.setText(display_name)
            print(f"{lang['message_assigned']}: {file_path}")

    def on_delete_sound_clicked(self):
        lang = self.translations[self.current_lang]
        if self.last_clicked_button:
            if self.last_clicked_button == self.active_button:
                self.stop_playback()

            self.button_states[self.last_clicked_button]["file_path"] = None
            self.last_clicked_button.setText(lang['button_empty'])
            print(lang['message_deleted'])

    def save_palette(self):
        lang = self.translations[self.current_lang]
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            lang['dialog_save_palette'], 
            "", 
            "JSON Dosyaları (*.json);;Tüm Dosyalar (*)"
        )

        if file_path:
            if not file_path.endswith('.json'):
                file_path += '.json'

            palette_data = {}
            for pos, button in self.button_map.items():
                if button in self.button_states and self.button_states[button]["file_path"]:
                    palette_data[f"{pos[0]},{pos[1]}"] = self.button_states[button]["file_path"]

            try:
                with open(file_path, 'w') as f:
                    json.dump(palette_data, f, indent=4)
                print(f"{lang['message_saved_success']}: {file_path}")
            except Exception as e:
                print(f"{lang['message_save_error']}: {e}")

    def load_palette(self):
        lang = self.translations[self.current_lang]
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            lang['dialog_load_palette'], 
            "", 
            "JSON Dosyaları (*.json);;Tüm Dosyalar (*)"
        )

        if file_path:
            try:
                with open(file_path, 'r') as f:
                    palette_data = json.load(f)
                
                for pos, button in self.button_map.items():
                    if pos != (6, 4):
                        self.button_states[button]["file_path"] = None
                        button.setText(lang['button_empty'])
                
                self.stop_playback()

                for pos_str, file_path in palette_data.items():
                    try:
                        row, col = map(int, pos_str.split(','))
                        button = self.button_map.get((row, col))
                        if button:
                            self.button_states[button]["file_path"] = file_path
                            file_name = os.path.basename(file_path)
                            file_name_without_extension = os.path.splitext(file_name)[0]
                            if len(file_name_without_extension) > 14:
                                display_name = file_name_without_extension[:11] + "..."
                            else:
                                display_name = file_name_without_extension
                            button.setText(display_name)
                    except (ValueError, IndexError):
                        print(f"{lang['message_invalid_data']}: {pos_str}")
                
                print(f"{lang['message_loaded_success']}: {file_path}")
            except Exception as e:
                print(f"{lang['message_load_error']}: {e}")

    def show_about_dialog(self):
        lang = self.translations[self.current_lang]
        about_text = f"""
<center>
<img src="{self.icon_path}" width="64" height="64">
</center>
<h1 align="center">Jingle Box</h1>
<br>
{lang['about_version']}: 1.0.1<br>
{lang['about_license']}: GNU GPLv3<br>
{lang['about_lang']}: Python 3<br>
{lang['about_gui']}: Qt5<br>
{lang['about_developer']}: Aydın Serhat KILIÇOĞLU<br>
Github: <a href="http://www.github.com/shampuan">www.github.com/shampuan</a><br>

<p>{lang['about_program_desc']}</p>

<p>{lang['about_no_warranty']}</p>
"""
        
        about_box = QMessageBox(self)
        about_box.setWindowTitle(lang['about_title'])
        about_box.setWindowIcon(self.windowIcon())
        about_box.setTextFormat(Qt.RichText)
        about_box.setText(about_text)
        about_box.setStandardButtons(QMessageBox.Ok)
        about_box.exec_()

    # --- VU Metre için ses verilerini işleme metodu (linamp.py'den alınmıştır) ---
    def _process_audio_buffer(self, buffer: QAudioBuffer):
        """VU metre için ses verilerini işle"""
        if self.media_player.state() != QMediaPlayer.PlayingState:
            self.left_vu_meter.set_level(0.0)
            self.right_vu_meter.set_level(0.0)
            return

        fmt = buffer.format()
        
        # Desteklenen formatları kontrol et
        if fmt.sampleType() == QAudioFormat.Float:
            data = buffer.constData().asarray(buffer.byteCount())
            num_samples = len(data) // (fmt.sampleSize() // 8)
            max_amplitude = 1.0
            
            try:
                if fmt.sampleSize() == 32:
                    samples = struct.unpack(f'<{num_samples}f', data)
                else:  # 64-bit float
                    samples = struct.unpack(f'<{num_samples}d', data)
            except struct.error:
                return
            
        elif fmt.sampleType() == QAudioFormat.SignedInt:
            data = buffer.constData().asarray(buffer.byteCount())
            bytes_per_sample = fmt.sampleSize() // 8
            num_samples = len(data) // bytes_per_sample
            
            if fmt.sampleSize() == 8:
                fmt_str = 'b'
                max_amplitude = 127
            elif fmt.sampleSize() == 16:
                fmt_str = 'h'
                max_amplitude = 32767
            elif fmt.sampleSize() == 32:
                fmt_str = 'i'
                max_amplitude = 2147483647
            else:
                return
            
            try:
                samples = struct.unpack(f'<{num_samples}{fmt_str}', data)
            except struct.error:
                return
            
        elif fmt.sampleType() == QAudioFormat.UnSignedInt:
            data = buffer.constData().asarray(buffer.byteCount())
            bytes_per_sample = fmt.sampleSize() // 8
            num_samples = len(data) // bytes_per_sample
            
            if fmt.sampleSize() == 8:
                fmt_str = 'B'
                max_amplitude = 255
            elif fmt.sampleSize() == 16:
                fmt_str = 'H'
                max_amplitude = 65535
            elif fmt.sampleSize() == 32:
                fmt_str = 'I'
                max_amplitude = 4294967295
            else:
                return
            
            try:
                samples = struct.unpack(f'<{num_samples}{fmt_str}', data)
            except struct.error:
                return
        else:
            return

        # Kanal sayısına göre örnekleri işle
        num_channels = fmt.channelCount()
        
        if num_channels >= 2:
            left_peak = 0
            right_peak = 0
            for i in range(0, num_samples, num_channels):
                # Sol kanal
                left_sample = samples[i]
                # Sağ kanal
                right_sample = samples[i+1]
                
                if fmt.sampleType() == QAudioFormat.UnSignedInt:
                    left_value = left_sample - (max_amplitude // 2)
                    right_value = right_sample - (max_amplitude // 2)
                    left_peak = max(left_peak, abs(left_value))
                    right_peak = max(right_peak, abs(right_value))
                else:
                    left_peak = max(left_peak, abs(left_sample))
                    right_peak = max(right_peak, abs(right_sample))
            
            norm_left_peak = left_peak / (max_amplitude if fmt.sampleType() != QAudioFormat.Float else 1.0)
            norm_right_peak = right_peak / (max_amplitude if fmt.sampleType() != QAudioFormat.Float else 1.0)
            
            self.left_vu_meter.set_level(norm_left_peak)
            self.right_vu_meter.set_level(norm_right_peak)

        else: # Mono veya bilinmeyen kanal sayısı
            peak = 0
            for sample in samples:
                if fmt.sampleType() == QAudioFormat.UnSignedInt:
                    value = sample - (max_amplitude // 2)
                    peak = max(peak, abs(value))
                else:
                    peak = max(peak, abs(sample))

            norm_peak = peak / (max_amplitude if fmt.sampleType() != QAudioFormat.Float else 1.0)
            
            self.left_vu_meter.set_level(norm_peak)
            self.right_vu_meter.set_level(norm_peak)
    # --- Metot Sonu ---


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = JingleBox()
    sys.exit(app.exec_())
