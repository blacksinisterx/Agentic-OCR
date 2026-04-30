"""
ui/main_window.py — ScribeAI PyQt6 main window (clean edition)

Sidebar: drop zone → engine selector → extract button → pipeline → quality → stats
Main:    tabbed text preview + export bar
Bottom:  status bar with session totals
"""

import os, shutil
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QTabWidget, QFileDialog,
    QMessageBox, QFrame, QSizePolicy, QScrollArea, QProgressBar,
    QComboBox, QApplication,
)
from PyQt6.QtCore  import Qt, QSize, pyqtSlot
from PyQt6.QtGui   import QPixmap, QFont, QDragEnterEvent, QDropEvent

from config import (
    APP_NAME, APP_VERSION, APP_SUBTITLE, INSTITUTION,
    WINDOW_W, WINDOW_H, STAGES, OUTPUT_DIR,
)
from agent.core import ScribeAgent
from ui.worker  import ExtractionWorker


# ══════════════════════════════════════════════════════════════
class DropZone(QLabel):
    def __init__(self, on_select, parent=None):
        super().__init__(parent)
        self._cb   = on_select
        self._path = None
        self.setObjectName("dropZone")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)
        self.setMinimumHeight(190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._placeholder()

    def _placeholder(self):
        self.setText("🖼\n\nClick or drag & drop image\nJPG · PNG · BMP · TIFF")
        self.setStyleSheet("""
            QLabel { background:#161B22; border:2px dashed #30363D;
                     border-radius:10px; color:#8B949E; font-size:13px; }
            QLabel:hover { border-color:#58A6FF; background:#1C2333; }""")

    def load(self, path):
        self._path = path
        pix = QPixmap(path)
        if not pix.isNull():
            pix = pix.scaled(QSize(255,175),
                             Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
            self.setPixmap(pix)
        else:
            self.setText(f"📄\n{Path(path).name}")
        self.setStyleSheet("""QLabel { background:#1C2333; border:2px solid #58A6FF;
                                       border-radius:10px; }""")
        self._cb(path)

    @property
    def path(self): return self._path

    def mousePressEvent(self, _):
        p, _ = QFileDialog.getOpenFileName(
            self, "Select Image",
            filter="Images (*.jpg *.jpeg *.png *.bmp *.tiff *.webp);;All (*)")
        if p: self.load(p)

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls(): e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent):
        urls = e.mimeData().urls()
        if urls:
            p = urls[0].toLocalFile()
            if os.path.isfile(p): self.load(p)


# ══════════════════════════════════════════════════════════════
class PipelineWidget(QWidget):
    IDLE = ("○","#484F58","#484F58")
    RUN  = ("◉","#58A6FF","#E6EDF3")
    DONE = ("✓","#3FB950","#8B949E")
    ERR  = ("✗","#F85149","#F85149")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []
        v = QVBoxLayout(self)
        v.setContentsMargins(0,0,0,0); v.setSpacing(3)
        hdr = QLabel("⚙  Agent Pipeline")
        hdr.setObjectName("sectionTitle"); v.addWidget(hdr)
        for ic_ch, name, desc in STAGES:
            row = QHBoxLayout(); row.setSpacing(6)
            ic  = QLabel("○")
            ic.setFixedWidth(16)
            ic.setFont(QFont("Segoe UI",10,QFont.Weight.Bold))
            ic.setStyleSheet("color:#484F58;")
            tx  = QLabel(f"{ic_ch}  {name}  —  {desc}")
            tx.setFont(QFont("Segoe UI",10)); tx.setStyleSheet("color:#484F58;")
            row.addWidget(ic); row.addWidget(tx,1)
            w = QWidget(); w.setLayout(row); v.addWidget(w)
            self._rows.append((ic, tx))

    def set_stage(self, idx):
        for i,(ic,tx) in enumerate(self._rows):
            s,sc,tc = self.DONE if i<idx else (self.RUN if i==idx else self.IDLE)
            ic.setText(s); ic.setStyleSheet(f"color:{sc};")
            tx.setStyleSheet(f"color:{tc};")

    def set_all_done(self):
        for ic,tx in self._rows:
            ic.setText("✓"); ic.setStyleSheet("color:#3FB950;")
            tx.setStyleSheet("color:#8B949E;")

    def set_error(self, idx):
        if 0<=idx<len(self._rows):
            ic,tx = self._rows[idx]
            ic.setText("✗"); ic.setStyleSheet("color:#F85149;")
            tx.setStyleSheet("color:#F85149;")

    def reset(self):
        for ic,tx in self._rows:
            ic.setText("○"); ic.setStyleSheet("color:#484F58;")
            tx.setStyleSheet("color:#484F58;")


# ══════════════════════════════════════════════════════════════
class QualityWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(8,8,8,8); v.setSpacing(2)
        self._lbl = QLabel("—")
        self._lbl.setFont(QFont("Segoe UI",26,QFont.Weight.Bold))
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl.setStyleSheet("color:#484F58;")
        self._bar = QProgressBar()
        self._bar.setRange(0,100); self._bar.setValue(0)
        self._bar.setTextVisible(False); self._bar.setFixedHeight(7)
        sub = QLabel("Extraction Quality")
        sub.setObjectName("mutedLabel")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self._lbl); v.addWidget(self._bar); v.addWidget(sub)

    def set_score(self, score):
        pct = int(score*100)
        self._lbl.setText(f"{pct}%")
        self._bar.setValue(pct)
        if pct>=75:   col,barcol="#3FB950","#3FB950"
        elif pct>=50: col,barcol="#D29922","#D29922"
        else:         col,barcol="#F85149","#F85149"
        self._lbl.setStyleSheet(f"color:{col};")
        self._bar.setStyleSheet(
            f"QProgressBar::chunk{{background:{barcol};border-radius:3px;}}")

    def reset(self):
        self._lbl.setText("—"); self._lbl.setStyleSheet("color:#484F58;")
        self._bar.setValue(0)


# ══════════════════════════════════════════════════════════════
def _sep():
    f = QFrame(); f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("border:1px solid #30363D;"); return f

def _stat(label, parent_layout):
    row = QHBoxLayout(); row.setSpacing(0)
    l = QLabel(f"{label}:"); l.setObjectName("mutedLabel"); l.setFixedWidth(88)
    v = QLabel("—"); v.setFont(QFont("Consolas",11))
    v.setStyleSheet("color:#79C0FF;")
    row.addWidget(l); row.addWidget(v)
    parent_layout.addLayout(row)
    return v


# ══════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}  v{APP_VERSION}  —  {APP_SUBTITLE}")
        self.resize(WINDOW_W, WINDOW_H)
        self.setMinimumSize(960, 640)

        self._agent  = ScribeAgent()
        self._worker = None
        self._result = None

        self._load_qss()
        self._build_ui()
        self._populate_engines()
        self._check_ollama()

    def _load_qss(self):
        qss = os.path.join(os.path.dirname(__file__), "styles", "dark.qss")
        if os.path.exists(qss):
            with open(qss, encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    # ── build UI ──────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget(); root.setObjectName("mainPanel")
        self.setCentralWidget(root)
        m = QVBoxLayout(root)
        m.setContentsMargins(0,0,0,0); m.setSpacing(0)
        m.addWidget(self._topbar())
        m.addWidget(self._body(), 1)
        m.addWidget(self._statusbar())

    def _topbar(self):
        bar = QWidget(); bar.setObjectName("topBar"); bar.setFixedHeight(50)
        h   = QHBoxLayout(bar); h.setContentsMargins(14,0,14,0)
        h.addWidget(QLabel("🔬", font=QFont("Segoe UI",17)))
        t = QLabel(f"  {APP_NAME}")
        t.setObjectName("appTitle"); h.addWidget(t)
        s = QLabel(f"  v{APP_VERSION}  ·  {INSTITUTION}  ·  {APP_SUBTITLE}")
        s.setObjectName("appSubtitle"); h.addWidget(s)
        h.addStretch(1)
        self._ollama_lbl = QLabel("⏳  Checking Ollama…")
        self._ollama_lbl.setObjectName("mutedLabel")
        h.addWidget(self._ollama_lbl)
        return bar

    def _body(self):
        body = QWidget()
        h    = QHBoxLayout(body)
        h.setContentsMargins(0,0,0,0); h.setSpacing(0)
        h.addWidget(self._sidebar(), 0)
        h.addWidget(self._main_panel(), 1)
        return body

    def _sidebar(self):
        sb = QWidget(); sb.setObjectName("sidebar"); sb.setFixedWidth(285)
        outer = QVBoxLayout(sb)
        outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")

        inner = QWidget(); inner.setStyleSheet("background:transparent;")
        v = QVBoxLayout(inner)
        v.setContentsMargins(10,10,10,10); v.setSpacing(9)

        # Drop zone
        self._drop = DropZone(self._on_image)
        v.addWidget(self._drop)

        # Engine selector — label + combo only
        lbl = QLabel("OCR Engine"); lbl.setObjectName("mutedLabel")
        v.addWidget(lbl)
        self._engine_combo = QComboBox()
        self._engine_combo.currentIndexChanged.connect(self._on_engine_change)
        v.addWidget(self._engine_combo)

        # Cleanup LLM indicator
        self._cleanup_lbl = QLabel()
        self._cleanup_lbl.setObjectName("mutedLabel")
        self._cleanup_lbl.setWordWrap(True)
        v.addWidget(self._cleanup_lbl)

        v.addWidget(_sep())

        # Extract button
        self._ext_btn = QPushButton("⚡  Extract Text")
        self._ext_btn.setObjectName("extractBtn")
        self._ext_btn.setFixedHeight(44)
        self._ext_btn.setEnabled(False)
        self._ext_btn.clicked.connect(self._start)
        v.addWidget(self._ext_btn)

        v.addWidget(_sep())

        # Pipeline
        self._pipeline = PipelineWidget(); v.addWidget(self._pipeline)

        v.addWidget(_sep())

        # Quality
        card = QWidget(); card.setObjectName("card")
        cv   = QVBoxLayout(card); cv.setContentsMargins(6,6,6,6)
        self._quality = QualityWidget(); cv.addWidget(self._quality)
        v.addWidget(card)

        v.addWidget(_sep())

        # Stats
        sc = QWidget(); sc.setObjectName("card")
        sv = QVBoxLayout(sc); sv.setContentsMargins(10,8,10,8); sv.setSpacing(5)
        QLabel("Stats").setObjectName("sectionTitle")
        hdr = QLabel("Stats"); hdr.setObjectName("sectionTitle"); sv.addWidget(hdr)
        self._s_words  = _stat("Words",     sv)
        self._s_eqs    = _stat("Equations", sv)
        self._s_heads  = _stat("Headings",  sv)
        self._s_time   = _stat("Time",      sv)
        self._s_retry  = _stat("Retries",   sv)
        self._s_engine = _stat("Engine",    sv)
        v.addWidget(sc)
        v.addStretch(1)

        scroll.setWidget(inner)
        outer.addWidget(scroll)
        return sb

    def _main_panel(self):
        p = QWidget(); p.setObjectName("mainPanel")
        v = QVBoxLayout(p)
        v.setContentsMargins(10,10,10,10); v.setSpacing(8)

        self._tabs = QTabWidget(); self._tabs.setDocumentMode(True)

        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText(
            "Select an image → choose engine → click ⚡ Extract Text\n\n"
            "Vision models (MiniCPM-V, LLaVA) work best for handwriting.\n"
            "Traditional OCR (Tesseract, EasyOCR) work best for printed text.\n"
            "A cleanup LLM will automatically fix spelling and format equations."
        )
        self._tabs.addTab(self._text_edit, "📝  Extracted Text")

        self._hist_edit = QTextEdit()
        self._hist_edit.setReadOnly(True)
        self._hist_edit.setFont(QFont("Consolas",10))
        self._tabs.addTab(self._hist_edit, "📚  History")

        v.addWidget(self._tabs, 1)

        # Export row
        row = QHBoxLayout(); row.setSpacing(7)
        self._docx_btn = QPushButton("📄  Save DOCX")
        self._docx_btn.setObjectName("docxBtn"); self._docx_btn.setFixedHeight(36)
        self._docx_btn.setEnabled(False); self._docx_btn.clicked.connect(self._save_docx)
        row.addWidget(self._docx_btn)

        self._pdf_btn = QPushButton("📑  Save PDF")
        self._pdf_btn.setObjectName("pdfBtn"); self._pdf_btn.setFixedHeight(36)
        self._pdf_btn.setEnabled(False); self._pdf_btn.clicked.connect(self._save_pdf)
        row.addWidget(self._pdf_btn)

        self._copy_btn = QPushButton("📋  Copy")
        self._copy_btn.setObjectName("copyBtn"); self._copy_btn.setFixedHeight(36)
        self._copy_btn.setEnabled(False); self._copy_btn.clicked.connect(self._copy)
        row.addWidget(self._copy_btn)

        row.addStretch(1)

        self._folder_btn = QPushButton("📂  Outputs")
        self._folder_btn.setObjectName("folderBtn"); self._folder_btn.setFixedHeight(36)
        self._folder_btn.clicked.connect(self._open_folder)
        row.addWidget(self._folder_btn)

        v.addLayout(row)
        return p

    def _statusbar(self):
        bar = QWidget(); bar.setObjectName("statusBar"); bar.setFixedHeight(28)
        h   = QHBoxLayout(bar); h.setContentsMargins(12,0,12,0)
        self._status_lbl  = QLabel("Ready"); self._status_lbl.setObjectName("mutedLabel")
        self._session_lbl = QLabel(); self._session_lbl.setObjectName("mutedLabel")
        h.addWidget(self._status_lbl); h.addStretch(1); h.addWidget(self._session_lbl)
        return bar

    # ── engine population ─────────────────────────────────────
    def _populate_engines(self):
        engines = self._agent.get_available_engines()
        self._engine_combo.blockSignals(True)
        self._engine_combo.clear()
        self._engine_map = {}   # combo index → engine key

        idx = 0
        for eng in engines:
            label = eng["label"]
            if not eng.get("available", True):
                label += "  [not installed]"
            self._engine_combo.addItem(label)
            self._engine_map[idx] = eng["key"]
            idx += 1

        self._engine_combo.blockSignals(False)
        self._on_engine_change(0)
        self._update_cleanup_label()

    def _update_cleanup_label(self):
        cn = self._agent.cleanup.model_name
        if self._agent.cleanup.available:
            self._cleanup_lbl.setText(f"✨ Cleanup: {cn}")
            self._cleanup_lbl.setStyleSheet("color:#3FB950; font-size:11px;")
        else:
            self._cleanup_lbl.setText("✨ Cleanup: heuristic only\n(pull mistral:7b for LLM cleanup)")
            self._cleanup_lbl.setStyleSheet("color:#8B949E; font-size:11px;")

    # ── Ollama check ──────────────────────────────────────────
    def _check_ollama(self):
        import threading
        def _run():
            ok, msg = self._agent.check_ready()
            from PyQt6.QtCore import QMetaObject, Q_ARG
            QMetaObject.invokeMethod(self, "_on_ollama",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(bool, ok), Q_ARG(str, msg))
        threading.Thread(target=_run, daemon=True).start()

    @pyqtSlot(bool, str)
    def _on_ollama(self, ok, msg):
        if ok:
            self._ollama_lbl.setText(f"✅  {msg}")
            self._ollama_lbl.setStyleSheet("color:#3FB950;")
        else:
            self._ollama_lbl.setText("❌  Ollama offline")
            self._ollama_lbl.setStyleSheet("color:#F85149;")
            QMessageBox.critical(self, "Ollama Not Available",
                f"{msg}\n\n1. Install from https://ollama.com/download\n"
                "2. Run: ollama serve\n3. Run: ollama pull minicpm-v")

    # ── engine change ─────────────────────────────────────────
    def _on_engine_change(self, idx):
        key = self._engine_map.get(idx, "minicpm-v")
        self._agent.set_engine(key)

    # ── image selected ────────────────────────────────────────
    def _on_image(self, path):
        self._ext_btn.setEnabled(True)
        self._pipeline.reset(); self._quality.reset()
        self._set_status(f"Ready: {Path(path).name}")

    # ── extraction ────────────────────────────────────────────
    def _start(self):
        if not self._drop.path or self._worker: return
        self._ext_btn.setEnabled(False)
        self._ext_btn.setText("⏳  Processing…")
        self._docx_btn.setEnabled(False); self._pdf_btn.setEnabled(False)
        self._copy_btn.setEnabled(False)
        self._pipeline.reset(); self._quality.reset()
        self._text_edit.clear()

        self._worker = ExtractionWorker(self._agent, self._drop.path)
        self._worker.progress.connect(self._set_status)
        self._worker.token.connect(self._append)
        self._worker.stage.connect(self._pipeline.set_stage)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_err)
        self._worker.start()

    @pyqtSlot(str)
    def _append(self, tok):
        self._text_edit.moveCursor(
            self._text_edit.textCursor().MoveOperation.End)
        self._text_edit.insertPlainText(tok)

    @pyqtSlot(dict)
    def _on_done(self, result):
        self._worker = None
        self._result = result
        self._ext_btn.setEnabled(True); self._ext_btn.setText("⚡  Extract Text")

        if not result["success"]:
            self._pipeline.set_error(1)
            self._set_status(f"❌  {result['error']}", error=True)
            QMessageBox.critical(self, "Failed", result["error"]); return

        self._pipeline.set_all_done()
        self._quality.set_score(result["quality"]["score"])

        st = result.get("stats", {})
        self._s_words.setText(str(st.get("words","—")))
        self._s_eqs.setText(str(st.get("equations","—")))
        self._s_heads.setText(str(st.get("headings","—")))
        self._s_time.setText(f"{result['processing_time']:.1f}s")
        self._s_retry.setText(str(result["retry_count"]))
        self._s_engine.setText(result.get("engine","—"))

        # ensure full text is shown (streaming may have gaps)
        cur = len(self._text_edit.toPlainText().strip())
        exp = len(result["text"].strip())
        if cur < exp - 20:
            self._text_edit.setPlainText(result["text"])
        if result.get("cached"):
            self._text_edit.append("\n\n[⚡ From session cache]")

        if result.get("docx_path"): self._docx_btn.setEnabled(True)
        if result.get("pdf_path"):  self._pdf_btn.setEnabled(True)
        self._copy_btn.setEnabled(True)

        q = result["quality"]["score"]
        self._set_status(
            f"✅  Done {result['processing_time']:.1f}s  ·  "
            f"Quality {q*100:.0f}%  ·  Cleanup: {result.get('cleanup_model','—')}")
        self._refresh_session(); self._refresh_history()

    @pyqtSlot(str)
    def _on_err(self, msg):
        self._worker = None
        self._ext_btn.setEnabled(True); self._ext_btn.setText("⚡  Extract Text")
        self._pipeline.set_error(1)
        self._set_status(f"❌  {msg}", error=True)
        QMessageBox.critical(self, "Error", msg)

    # ── export ────────────────────────────────────────────────
    def _save_docx(self):
        src = self._result and self._result.get("docx_path")
        if not src or not os.path.exists(src): return
        dst, _ = QFileDialog.getSaveFileName(self, "Save DOCX",
            Path(src).name, "Word (*.docx)")
        if dst: shutil.copy2(src, dst); QMessageBox.information(self,"Saved",dst)

    def _save_pdf(self):
        src = self._result and self._result.get("pdf_path")
        if not src or not os.path.exists(src): return
        dst, _ = QFileDialog.getSaveFileName(self, "Save PDF",
            Path(src).name, "PDF (*.pdf)")
        if dst: shutil.copy2(src, dst); QMessageBox.information(self,"Saved",dst)

    def _copy(self):
        QApplication.clipboard().setText(self._text_edit.toPlainText())
        self._set_status("📋  Copied to clipboard")

    def _open_folder(self):
        folder = os.path.abspath(OUTPUT_DIR)
        os.makedirs(folder, exist_ok=True)
        import subprocess, platform
        if platform.system()=="Windows":   os.startfile(folder)
        elif platform.system()=="Darwin":  subprocess.Popen(["open", folder])
        else:                              subprocess.Popen(["xdg-open", folder])

    # ── history ───────────────────────────────────────────────
    def _refresh_history(self):
        h = self._agent.history()
        if not h:
            self._hist_edit.setPlainText("No history yet."); return
        lines = []
        for r in h[:25]:
            lines += [
                "─"*54,
                f"📄  {r.get('image_name','?')}",
                (f"    Quality: {r.get('quality_score',0)*100:.0f}%  ·  "
                 f"Words: {r.get('word_count','?')}  ·  "
                 f"Time: {r.get('processing_time','?')}s"),
                f"    {r.get('timestamp','')[:16]}", "",
            ]
        self._hist_edit.setPlainText("\n".join(lines))

    def _refresh_session(self):
        st = self._agent.session_stats()
        p  = st.get("processed",0)
        self._session_lbl.setText(
            f"Session: {p} image{'s' if p!=1 else ''}  ·  "
            f"Avg quality {st.get('avg_quality',0)*100:.0f}%  ·  "
            f"{st.get('total_words',0):,} words  ·  "
            f"Avg {st.get('avg_time',0):.0f}s/page")

    def _set_status(self, msg, error=False):
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(
            "color:#F85149;" if error else "color:#8B949E;")
