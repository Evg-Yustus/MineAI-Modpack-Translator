import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtWidgets import QApplication
    from mineai.gui_qt.widgets import ScrollSafeComboBox, ScrollSafeSpinBox
except ImportError:
    QApplication = None
    ScrollSafeComboBox = None
    ScrollSafeSpinBox = None


@unittest.skipIf(QApplication is None, "PyQt6 is not installed")
class WheelSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_combo_ignores_wheel(self):
        combo = ScrollSafeComboBox()
        event = _FakeWheelEvent()
        combo.wheelEvent(event)
        self.assertTrue(event.ignored)

    def test_spinbox_ignores_wheel(self):
        spin = ScrollSafeSpinBox()
        event = _FakeWheelEvent()
        spin.wheelEvent(event)
        self.assertTrue(event.ignored)


class _FakeWheelEvent:
    def __init__(self):
        self.ignored = False

    def ignore(self):
        self.ignored = True


if __name__ == "__main__":
    unittest.main()
