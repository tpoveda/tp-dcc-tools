from __future__ import annotations

from overrides import override

from tp.common.qt import api as qt


class SkeletorView(qt.FramelessWindow):
    def __init__(self, parent: qt.QWidget | None = None):
        super().__init__(parent=parent)

    @override
    def setup_ui(self):
        super().setup_ui()
