"""
ui/worker.py
QThread worker that runs the ScribeAgent pipeline off the main thread.
Emits Qt signals so the UI updates safely without blocking.
"""

from PyQt6.QtCore import QThread, pyqtSignal


class ExtractionWorker(QThread):
    """
    Runs ScribeAgent.run() in a background thread.

    Signals:
        progress(str)    — stage status text
        token(str)       — single streamed token from LLaVA
        stage(int)       — current pipeline stage index 0-5
        finished(dict)   — complete result dict from ScribeAgent.run()
        error(str)       — error message string
    """
    progress = pyqtSignal(str)
    token    = pyqtSignal(str)
    stage    = pyqtSignal(int)
    finished = pyqtSignal(dict)
    error    = pyqtSignal(str)

    def __init__(self, agent, image_path: str, parent=None):
        super().__init__(parent)
        self.agent      = agent
        self.image_path = image_path

    def run(self):
        try:
            result = self.agent.run(
                self.image_path,
                progress_cb = lambda msg: self.progress.emit(msg),
                token_cb    = lambda tok: self.token.emit(tok),
                stage_cb    = lambda n:   self.stage.emit(n),
            )
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))
