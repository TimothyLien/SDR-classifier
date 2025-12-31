import sys
import time
import zmq
import numpy as np
import message_pb2
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import QThread, pyqtSignal, Qt
import pyqtgraph as pg

# Configuration
ZMQ_PORT = "tcp://localhost:5555"
HISTORY_SIZE = 100 # Number of rows in the waterfall
FFT_SIZE = 1024

class RadioWorker(QThread):
    # Signals to send data to the GUI
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

class MissionControl(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SDR AI Classification Engine")
        self.resize(1000, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        self.class_label = QLabel("WAITING FOR SIGNAL...")
        self.class_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.class_label.setStyleSheet("font-size: 40px; font-weight: bold; color: gray; background-color: #222; padding: 20px;")
        layout.addWidget(self.class_label)

        self.stats_label = QLabel("Power: 0 | Peak Bin: 0 | Freq: 0.0 MHz")
        self.stats_label.setStyleSheet("font-size: 16px; color: white;")
        layout.addWidget(self.stats_label)

        self.waterfall_view = pg.ImageView()
        self.waterfall_view.ui.histogram.hide()
        self.waterfall_view.ui.roiBtn.hide()
        self.waterfall_view.ui.menuBtn.hide()
        self.waterfall_view.view.setAspectLocked(False)
        layout.addWidget(self.waterfall_view)
        
        self.waterfall_buffer = np.zeros((HISTORY_SIZE, 1024)) 

        self.worker = RadioWorker()
        self.worker.data_received.connect(self.update_dashboard)
        self.worker.start()

    def update_dashboard(self, msg):
        mod_type = msg.modulation
        color = "#555"
        if mod_type == "BPSK": color = "#00cc00"
        if mod_type == "QPSK": color = "#0088ff"
        if mod_type == "FM":   color = "#ffaa00"
        if mod_type == "Noise": color = "#444"
        
        self.class_label.setText(f"DETECTED: {mod_type}")
        self.class_label.setStyleSheet(f"font-size: 40px; font-weight: bold; color: white; background-color: {color}; padding: 20px; border-radius: 10px;")

        self.stats_label.setText(f"Power: {msg.signal_strength:.1f} | Peak Bin: {msg.peak_bin_index}")


        spectrum = np.array(msg.spectrum_data)

        if len(spectrum) == 1024:

            self.waterfall_buffer = np.roll(self.waterfall_buffer, -1, axis=0)
            
            spectrum_db = 20 * np.log10(spectrum + 1e-9)

            self.waterfall_buffer[-1] = spectrum_db
            
            self.waterfall_view.setImage(self.waterfall_buffer.T, autoLevels=False, levels=(0, 60))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MissionControl()
    window.show()
    sys.exit(app.exec())