
import os, sys, json, re, traceback
from pathlib import Path
from urllib.request import urlopen
from io import BytesIO
from PIL import Image
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFileDialog, QSpinBox, QProgressBar, QMessageBox
)
from PySide6.QtGui import QFont, QColor, QPalette


# ----------------------------
# Worker Thread
# ----------------------------
class RegenWorker(QThread):
    log = Signal(str)
    progress = Signal(int)
    finished = Signal()

    def __init__(self, json_dir, layer_dir, out_dir, canvas_w, canvas_h):
        super().__init__()
        self.json_dir = Path(json_dir)
        self.layer_dir = Path(layer_dir)
        self.out_dir = Path(out_dir)
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h
        self._stop = False

    def stop(self):
        self._stop = True

    def _normalize(self, text: str):
        """Normalize text for matching (remove symbols, lowercase)."""
        text = re.sub(r'[#_\-\d]+$', '', str(text))  # remove rarity suffixes like #12, _12, -12
        text = re.sub(r'[^a-z0-9]', '', text.strip().lower())
        return text

    def _load_layer_image(self, trait_type, trait_value):
        """Fuzzy match against rarity-numbered and inconsistent file names."""
        ttype = self._normalize(trait_type)
        tval = self._normalize(trait_value)

        # Search folders matching trait_type
        for folder in self.layer_dir.iterdir():
            if folder.is_dir() and ttype in self._normalize(folder.name):
                for img_file in folder.iterdir():
                    if img_file.suffix.lower() in (".png", ".jpg", ".jpeg"):
                        stem_norm = self._normalize(img_file.stem)
                        if tval == stem_norm or tval in stem_norm:
                            return Image.open(img_file).convert("RGBA")

        # Global fallback search
        for img_file in self.layer_dir.rglob("*"):
            if img_file.suffix.lower() in (".png", ".jpg", ".jpeg"):
                stem_norm = self._normalize(img_file.stem)
                if tval == stem_norm or tval in stem_norm:
                    return Image.open(img_file).convert("RGBA")

        self.log.emit(f"[MISS] {trait_type}/{trait_value}")
        return None

    def run(self):
        try:
            all_files = [f for f in self.json_dir.iterdir() if f.is_file()]
            json_files = []
            for f in all_files:
                try:
                    with open(f, "r") as jf:
                        json.load(jf)
                    json_files.append(f)
                except Exception:
                    continue

            total = len(json_files)
            if not total:
                self.log.emit("[!] No valid metadata files found.")
                return

            self.out_dir.mkdir(parents=True, exist_ok=True)

            for idx, meta_path in enumerate(json_files, start=1):
                if self._stop:
                    self.log.emit("[!] Stopped by user.")
                    break

                try:
                    with open(meta_path, "r") as f:
                        meta = json.load(f)

                    attributes = meta.get("attributes", [])
                    if not attributes:
                        self.log.emit(f"[WARN] {meta_path.name}: no attributes found.")
                        continue

                    base = Image.new("RGBA", (self.canvas_w, self.canvas_h), (0, 0, 0, 0))

                    for att in attributes:
                        ttype = att.get("trait_type", "").strip()
                        tval = att.get("value", "").strip()
                        if not ttype or not tval:
                            continue
                        layer_img = self._load_layer_image(ttype, tval)
                        if layer_img is None:
                            continue
                        layer_img = layer_img.resize((self.canvas_w, self.canvas_h), Image.LANCZOS)
                        base.alpha_composite(layer_img)

                    out_path = self.out_dir / f"{meta_path.stem or meta_path.name}.png"
                    base.save(out_path)
                    self.log.emit(f"[OK] Saved {out_path.name}")

                except Exception as e:
                    self.log.emit(f"[ERR] {meta_path.name}: {e}")
                    traceback.print_exc()

                self.progress.emit(int(idx / total * 100))

            self.log.emit("[DONE] reGENERATION complete.")
        except Exception as e:
            self.log.emit(f"[FATAL] {e}")
        finally:
            self.finished.emit()


# ----------------------------
# Main GUI
# ----------------------------
class RegenApp(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.setWindowTitle("💀 reGEN 💀")
        self.setGeometry(200, 150, 720, 520)
        self._style_ui()
        self._build_ui()

    def _style_ui(self):
        self.setFont(QFont("Courier", 10, QFont.Bold))
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor("#0a0012"))
        pal.setColor(QPalette.WindowText, QColor("#00ffea"))
        pal.setColor(QPalette.Base, QColor("#0f0f0f"))
        pal.setColor(QPalette.Text, QColor("#ff55ff"))
        pal.setColor(QPalette.Button, QColor("#220033"))
        pal.setColor(QPalette.ButtonText, QColor("#faff00"))
        self.setPalette(pal)
        self.setStyleSheet("""
            QPushButton {
                background-color: #330044;
                color: #ff55ff;
                border: 2px solid #00ffea;
                border-radius: 6px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #660077;
            }
            QTextEdit {
                background-color: #000000;
                border: 1px solid #ff55ff;
                color: #00ffea;
            }
            QLabel { color: #faff00; }
            QProgressBar {
                border: 2px solid #00ffea;
                border-radius: 5px;
                text-align: center;
                color: #00ffea;
                background: #220022;
            }
            QProgressBar::chunk {
                background-color: #ff00aa;
                width: 20px;
            }
        """)

    def _build_ui(self):
        layout = QVBoxLayout()

        # Directory selectors
        self.json_btn = QPushButton("Select JSON Directory")
        self.json_label = QLabel("None selected")
        self.json_btn.clicked.connect(lambda: self._pick_folder(self.json_label))

        self.layer_btn = QPushButton("Select Layers Directory")
        self.layer_label = QLabel("None selected")
        self.layer_btn.clicked.connect(lambda: self._pick_folder(self.layer_label))

        self.out_btn = QPushButton("Select Output Directory")
        self.out_label = QLabel("None selected")
        self.out_btn.clicked.connect(lambda: self._pick_folder(self.out_label))

        # Canvas size
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Canvas Width:"))
        self.w_spin = QSpinBox(); self.w_spin.setRange(64, 8192); self.w_spin.setValue(1000)
        size_row.addWidget(self.w_spin)
        size_row.addWidget(QLabel("Canvas Height:"))
        self.h_spin = QSpinBox(); self.h_spin.setRange(64, 8192); self.h_spin.setValue(1000)
        size_row.addWidget(self.h_spin)

        # Control buttons
        ctrl_row = QHBoxLayout()
        self.start_btn = QPushButton("⚡ START reGENERATION ⚡")
        self.stop_btn = QPushButton("🛑 STOP")
        self.stop_btn.setEnabled(False)
        ctrl_row.addWidget(self.start_btn)
        ctrl_row.addWidget(self.stop_btn)
        self.start_btn.clicked.connect(self._start)
        self.stop_btn.clicked.connect(self._stop_worker)

        # Progress + Log
        self.progress = QProgressBar()
        self.log = QTextEdit(); self.log.setReadOnly(True)

        layout.addWidget(self.json_btn); layout.addWidget(self.json_label)
        layout.addWidget(self.layer_btn); layout.addWidget(self.layer_label)
        layout.addWidget(self.out_btn); layout.addWidget(self.out_label)
        layout.addLayout(size_row)
        layout.addLayout(ctrl_row)
        layout.addWidget(self.progress)
        layout.addWidget(self.log)
        self.setLayout(layout)

    def _pick_folder(self, label):
        path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if path:
            label.setText(path)

    def _append_log(self, msg):
        self.log.append(msg)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def _start(self):
        if self.worker and self.worker.isRunning():
            self._append_log("[!] A regeneration is already in progress.")
            return

        json_dir = self.json_label.text()
        layer_dir = self.layer_label.text()
        out_dir = self.out_label.text()
        if not all(os.path.isdir(p) for p in [json_dir, layer_dir, out_dir]):
            self._append_log("[ERR] Missing or invalid directory paths.")
            return

        w, h = self.w_spin.value(), self.h_spin.value()

        self.worker = RegenWorker(json_dir, layer_dir, out_dir, w, h)
        self.worker.log.connect(self._append_log)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self._on_finished)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.worker.start()

    def _stop_worker(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self._append_log("[!] Stopping thread...")

    def _on_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._append_log("[✓] Thread finished cleanly.")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "reGENERATOR is still running. Stop and exit?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.worker.stop()
                self.worker.wait(2000)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


# ----------------------------
# Entry Point
# ----------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = RegenApp()
    win.show()
    sys.exit(app.exec())
