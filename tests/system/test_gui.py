import pytest
from PyQt5.QtWidgets import QApplication
from main import MainWindow

@pytest.mark.system
def test_main_window_load(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    # Проверяем, что кнопка анализа изначально неактивна
    assert window.btn_analyze.isEnabled() is False
    # Можно эмулировать загрузку файла, вызвав метод с тестовым путём
    # Но для этого нужно модифицировать код, чтобы можно было подменить диалог.
    # В простом варианте можно просто проверить, что окно создаётся.