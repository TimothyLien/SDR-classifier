import sys
import zmq
import numpy as np
import message_pb2
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QLabel, QSlider, QFrame)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
import pyqtgraph as pg

# Configuration
ZMQ_PORT = "tcp://localhost:5555"
HISTORY_SIZE = 150         # Longer history for better view
SAMPLE_RATE = 240000       # 240 kHz (Matches C++)
FFT_SIZE = 1024            # Matches C++

# Worker Thread to receive data
class RadioWorker(QThread):
    data_received = pyqtSignal(object) 
    
    def run(self):
        context = zmq.Context()
        subscriber = context.socket(zmq.SUB)
        subscriber.connect(ZMQ_PORT)
        subscriber.setsockopt_string(zmq.SUBSCRIBE, "")

        print(f"[GUI] Listening on {ZMQ_PORT}...")
        while True:
            try:
                payload = subscriber.recv()
                msg = message_pb2.SignalResult()
                msg.ParseFromString(payload)
                self.data_received.emit(msg)
            except Exception as e:
                print(f"Error: {e}")

class FrequencyAxis(pg.AxisItem):
    def __init__(self, orientation='bottom', center_freq_hz=100.0, bandwidth_hz=240000, **kwargs):
        super().__init__(orientation, **kwargs)
        self.center_freq_hz = center_freq_hz
        self.bandwidth_hz = bandwidth_hz

    def tickStrings(self, values, scale, spacing):
        # Convert "Bin Index" (0..1024) to "Frequency (MHz)"
        strings = []
        for v in values:
            # Map bin v to frequency
            # Freq = Start_Freq + (v / Total_Bins) * Bandwidth
            start_freq = self.center_freq_hz - (self.bandwidth_hz / 2)
            freq_hz = start_freq + (v / FFT_SIZE) * self.bandwidth_hz
            
            # Formatting fixes
            if abs(freq_hz) >= 1e6:
                strings.append(f"{freq_hz/1e6:.3f} M")
            elif abs(freq_hz) >= 1e3:
                strings.append(f"{freq_hz/1e3:.1f} k")
            else:
                strings.append(f"{freq_hz:.0f} Hz")
        return strings

# Main Window
class MissionControl(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SDR Spectrum Analyzer")
        self.resize(1200, 900)
        self.setStyleSheet("background-color: #121212; color: #E0E0E0;")

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 1. HEADER (Classification)
        self.header_frame = QFrame()
        self.header_frame.setStyleSheet("background-color: #1E1E1E; border-radius: 10px;")
        header_layout = QHBoxLayout(self.header_frame)
        
        self.class_label = QLabel("WAITING...")
        self.class_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.class_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #555;")
        header_layout.addWidget(self.class_label)
        
        main_layout.addWidget(self.header_frame)

        # 2. INFO ROW (Stats)
        self.stats_label = QLabel("Power: - dB | Peak: - Hz")
        self.stats_label.setStyleSheet("font-family: monospace; font-size: 14px; color: #AAA;")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.stats_label)

        # 3. VISUALIZATION (Waterfall)
        # Custom Axis
        self.freq_axis = FrequencyAxis(orientation='bottom')
        
        # Plot Item
        self.plot_item = pg.PlotItem(axisItems={'bottom': self.freq_axis})
        self.plot_item.hideAxis('left') # Hide bin numbers on Y
        self.plot_item.setMouseEnabled(x=False, y=False)
        
        # Image Item (The Heatmap)
        self.img_item = pg.ImageItem()
        self.plot_item.addItem(self.img_item)
        
        # Graphics View container
        self.graphics_view = pg.GraphicsLayoutWidget()
        self.graphics_view.addItem(self.plot_item)
        main_layout.addWidget(self.graphics_view, stretch=1)

        # Data Buffer
        self.waterfall_buffer = np.zeros((HISTORY_SIZE, FFT_SIZE))

        # 4. CONTROLS (Gain Slider)
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("Visual Gain:"))
        
        self.gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.gain_slider.setRange(10, 100)
        self.gain_slider.setValue(60) # Default 60dB range
        self.gain_slider.valueChanged.connect(self.update_levels)
        control_layout.addWidget(self.gain_slider)
        
        main_layout.addLayout(control_layout)

        # Start Thread
        self.worker = RadioWorker()
        self.worker.data_received.connect(self.update_dashboard)
        self.worker.start()

    def update_levels(self):
        # Update the color contrast
        val = self.gain_slider.value()
        self.img_item.setLevels((0, val))

    def update_dashboard(self, msg):
        # Update Axis Context (in case center freq changes)
        self.freq_axis.center_freq_hz = msg.center_frequency

        # 1. Update Class Label
        mod_type = msg.modulation
        color = "#333"
        text_color = "#AAA"
        
        if mod_type == "BPSK": 
            color = "#004d00" # Dark Green
            text_color = "#00ff00"
        elif mod_type == "QPSK": 
            color = "#002266" # Dark Blue
            text_color = "#0088ff"
        elif mod_type == "Sine_Wave": 
            color = "#663300" # Dark Orange
            text_color = "#ffaa00"
        elif mod_type == "Noise":
            color = "#222"
            text_color = "#555"
            
        self.class_label.setText(f"{mod_type}")
        self.class_label.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {text_color}; background-color: {color}; border-radius: 10px; padding: 10px;")

        # 2. Update Stats
        # Calc real freq of peak
        freq_hz = msg.center_frequency - (SAMPLE_RATE/2) + (msg.peak_bin_index / FFT_SIZE) * SAMPLE_RATE
        self.stats_label.setText(f"Signal Strength: {msg.signal_strength:.1f} | Peak Freq: {freq_hz:.1f} Hz")

        # 3. Update Waterfall
        spectrum = np.array(msg.spectrum_data)
        if len(spectrum) == FFT_SIZE:
            # Shift Buffer
            self.waterfall_buffer = np.roll(self.waterfall_buffer, -1, axis=0)
            
            # Convert to dB for visualization (if not already dB)
            spectrum_db = 20 * np.log10(spectrum + 1e-9)
            
            # FFT Shift (Optional: puts 0Hz in center)
            # For now, we keep it 0..Fs to match C++ output
            
            self.waterfall_buffer[-1] = spectrum_db
            
            # Update Image
            # Transpose needed because PyQtGraph expects [x, y]
            self.img_item.setImage(self.waterfall_buffer.T, autoLevels=False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MissionControl()
    window.show()
    sys.exit(app.exec())