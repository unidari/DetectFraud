# -*- coding: utf-8 -*-
import sys
import os
import traceback
import webbrowser
import tempfile
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QMessageBox, QProgressDialog, QSplitter, QDoubleSpinBox, QComboBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings

# Импорты модулей проекта
from data_loader import DataLoader
from feature_extractor import FeatureExtractor
from anomaly_detector import AnomalyDetector
from logic_validator import LogicValidator
from materiality import MaterialityEstimator
from graph_builder import GraphBuilder
from report_generator import ReportGenerator

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False
    QWebEngineView = None
    QWebEngineSettings = None

class AnalysisThread(QThread):
    """Поток для выполнения анализа без блокировки интерфейса"""
    finished = pyqtSignal(object, object, object, object, object)  # df, scores, logic_df, mat_info, graph_fig
    error = pyqtSignal(str)

    def __init__(self, filepath, balance_currency, anomaly_threshold):
        super().__init__()
        self.filepath = filepath
        self.balance_currency = balance_currency
        self.anomaly_threshold = anomaly_threshold

    def run(self):
        try:
            # 1. Загрузка данных
            df, err, _ = DataLoader.load_file(self.filepath)
            if err:
                self.error.emit(err)
                return

            # 2. Извлечение признаков и ML-анализ
            features = FeatureExtractor.extract_features(df)
            detector = AnomalyDetector(contamination='auto', random_state=42)
            anomaly_scores = detector.fit_predict(features)

            # 3. Логические ошибки (включая проверку остатков)
            logic_errors_df, _ = LogicValidator.validate(df)
            balance_errors_df = LogicValidator.validate_balance(df)
            if not balance_errors_df.empty:
                balance_rows = []
                for _, row in balance_errors_df.iterrows():
                    balance_rows.append({
                        'Индекс': '—',
                        'Дебет': '',
                        'Кредит': '',
                        'Дата': '',
                        'Описание': f"Счёт {row['Счёт']}",
                        'Ошибки': f"{row['Ошибка']} (сальдо {row['Сальдо']})"
                    })
                balance_df = pd.DataFrame(balance_rows)
                if not logic_errors_df.empty:
                    combined_errors = pd.concat([logic_errors_df, balance_df], ignore_index=True)
                else:
                    combined_errors = balance_df
            else:
                combined_errors = logic_errors_df

            # 4. Оценка существенности
            mat_info = MaterialityEstimator.compute_materiality(
                anomaly_scores, df, self.balance_currency, threshold=self.anomaly_threshold
            )

            # 5. Граф
            graph_fig = GraphBuilder.build_interactive_graph(df, weight_by='summa')

            self.finished.emit(df, anomaly_scores, combined_errors, mat_info, graph_fig)

        except Exception as e:
            self.error.emit(f"Ошибка в процессе анализа: {str(e)}\n{traceback.format_exc()}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DetectFraud — Анализ бухгалтерских проводок")
        self.setGeometry(100, 100, 1300, 850)

        # Хранимые данные
        self.current_df = None
        self.anomaly_scores = None
        self.logic_errors_df = None
        self.graph_figure = None
        self.balance_currency = None
        self.anomaly_threshold = 0.95
        self.categories = None
        self.cached_df = None
        self.cached_categories = None
        self.graph_window = None

        # Центральный виджет
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # ---------- Верхняя панель ----------
        top_panel = QHBoxLayout()
        top_panel.setSpacing(8)

        self.btn_load = QPushButton("📂 Загрузить файл")
        self.btn_load.clicked.connect(self.load_file)

        self.btn_analyze = QPushButton("▶ Запустить анализ")
        self.btn_analyze.clicked.connect(self.start_analysis)
        self.btn_analyze.setEnabled(False)

        self.btn_graph = QPushButton("📊 Граф")
        self.btn_graph.clicked.connect(self.show_graph)
        self.btn_graph.setEnabled(False)

        self.btn_export = QPushButton("📄 Экспорт")
        self.btn_export.clicked.connect(self.export_report)
        self.btn_export.setEnabled(False)

        self.threshold_label = QLabel("Порог:")
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.5, 1.0)
        self.threshold_spin.setSingleStep(0.01)
        self.threshold_spin.setValue(0.95)
        self.threshold_spin.setToolTip("Порог отсечения для ML-аномалий (чем выше, тем строже)")
        self.threshold_spin.valueChanged.connect(self.on_threshold_changed)

        self.balance_label = QLabel("Валюта баланса:")
        self.balance_edit = QLineEdit()
        self.balance_edit.setPlaceholderText("Введите сумму или загрузите из файла")
        self.balance_edit.setToolTip("Общая валюта баланса (например, итог по активу)")

        self.btn_load_balance = QPushButton("Загрузить из файла")
        self.btn_load_balance.clicked.connect(self.load_balance_from_file)

        top_panel.addWidget(self.btn_load)
        top_panel.addWidget(self.btn_analyze)
        top_panel.addWidget(self.btn_graph)
        top_panel.addWidget(self.btn_export)
        top_panel.addWidget(self.threshold_label)
        top_panel.addWidget(self.threshold_spin)
        top_panel.addWidget(self.balance_label)
        top_panel.addWidget(self.balance_edit)
        top_panel.addWidget(self.btn_load_balance)
        top_panel.addStretch()

        # ---------- Панель фильтра ----------
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Показать:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Все проводки", "Только аномалии (красные)", "Только логические ошибки (жёлтые)"])
        self.filter_combo.currentIndexChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.filter_combo)
        filter_layout.addStretch()

        # ---------- Вкладки ----------
        self.tabs = QTabWidget()
        self.table_widget = QTableWidget()
        self.logic_table_widget = QTableWidget()
        self.tabs.addTab(self.table_widget, "Проводки (с подсветкой)")
        self.tabs.addTab(self.logic_table_widget, "Логические ошибки")

        # ---------- Карточка существенности ----------
        self.materiality_card = QWidget()
        self.materiality_card.setObjectName("materialityCard")
        card_layout = QHBoxLayout(self.materiality_card)
        self.materiality_label = QLabel("Оценка существенности: не выполнена")
        self.materiality_label.setObjectName("materialityLabel")
        card_layout.addWidget(self.materiality_label)
        card_layout.addStretch()

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.tabs)
        splitter.addWidget(self.materiality_card)

        main_layout.addLayout(top_panel)
        main_layout.addLayout(filter_layout)
        main_layout.addWidget(splitter)

        self.statusBar().showMessage("Готов")
        self.apply_stylesheet()

    def apply_stylesheet(self):
        try:
            with open("style.qss", "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            pass

    # ---------- Загрузка данных (обновлена) ----------
    def load_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл с проводками",
            "",
            "Excel files (*.xlsx *.xls);;CSV files (*.csv)"
        )
        if not filepath:
            return
        self.statusBar().showMessage("Загрузка файла...")
        df, err, mapping_info = DataLoader.load_file(filepath)
        if err:
            QMessageBox.critical(self, "Ошибка", err)
            self.statusBar().showMessage("Ошибка загрузки")
            return

        # Выводим сообщение о сопоставлении колонок
        if mapping_info:
            QMessageBox.information(self, "Сопоставление колонок", mapping_info['message'])

        self.current_df = df
        self.filepath = filepath
        self.categories = None
        self.cached_df = None
        self.cached_categories = None
        self.display_table(df, None, None)
        self.btn_analyze.setEnabled(True)
        self.btn_graph.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.logic_table_widget.clear()
        self.logic_table_widget.setRowCount(1)
        self.logic_table_widget.setColumnCount(1)
        self.logic_table_widget.setHorizontalHeaderLabels(["Информация"])
        self.logic_table_widget.setItem(0, 0, QTableWidgetItem("Анализ не выполнен"))
        self.materiality_label.setText("Оценка существенности: не выполнена")
        self.materiality_card.setStyleSheet("")
        self.statusBar().showMessage(f"Загружено {len(df)} проводок")

    # Остальные методы (display_table, classify_rows, apply_filter, _render_table,
    # display_logic_errors, start_analysis, on_analysis_finished, on_analysis_error,
    # on_threshold_changed, show_graph, cleanup_temp_file, export_report,
    # load_balance_from_file) остаются без изменений.
    # Для краткости они опущены, но в реальном проекте они должны быть.

    # (Здесь должны быть все остальные методы, как в предыдущей версии main.py)
    # Для полноты я приведу их в финальном архиве, но в этом ответе для экономии места
    # я показываю только изменённые части. Полный файл будет предоставлен отдельно.

    def display_table(self, df, anomaly_scores=None, categories=None):
        if df is None:
            return
        if categories is None and anomaly_scores is not None:
            categories = self.classify_rows(df, anomaly_scores)
        self.cached_df = df
        self.cached_categories = categories
        self.cached_scores = anomaly_scores
        self.apply_filter()

    def classify_rows(self, df, anomaly_scores):
        threshold = self.threshold_spin.value()
        categories = ['green'] * len(df)
        error_indices = set()
        if self.logic_errors_df is not None and not self.logic_errors_df.empty:
            if 'Индекс' in self.logic_errors_df.columns:
                for idx in self.logic_errors_df['Индекс']:
                    if isinstance(idx, int) or (isinstance(idx, str) and idx.isdigit()):
                        error_indices.add(int(idx))
        for i in range(len(df)):
            if anomaly_scores[i] >= threshold:
                categories[i] = 'red'
            elif i in error_indices:
                categories[i] = 'yellow'
        return categories

    def apply_filter(self):
        if not hasattr(self, 'cached_df') or self.cached_df is None:
            return
        filter_idx = self.filter_combo.currentIndex()
        df = self.cached_df
        categories = self.cached_categories

        if filter_idx == 0:
            filtered_df = df
            filtered_cat = categories
        elif filter_idx == 1:
            if categories:
                mask = [c == 'red' for c in categories]
                filtered_df = df[mask]
                filtered_cat = [categories[i] for i in range(len(df)) if mask[i]]
            else:
                filtered_df = df.head(0)
                filtered_cat = []
        else:
            if categories:
                mask = [c == 'yellow' for c in categories]
                filtered_df = df[mask]
                filtered_cat = [categories[i] for i in range(len(df)) if mask[i]]
            else:
                filtered_df = df.head(0)
                filtered_cat = []
        self._render_table(filtered_df, filtered_cat)

    def _render_table(self, df, categories):
        self.table_widget.clear()
        if df is None or df.empty:
            self.table_widget.setRowCount(1)
            self.table_widget.setColumnCount(1)
            self.table_widget.setHorizontalHeaderLabels(["Информация"])
            self.table_widget.setItem(0, 0, QTableWidgetItem("Нет данных для отображения"))
            return
        self.table_widget.setRowCount(len(df))
        self.table_widget.setColumnCount(len(df.columns))
        self.table_widget.setHorizontalHeaderLabels(df.columns)

        color_map = {
            'green': QColor(42, 157, 143),
            'yellow': QColor(233, 196, 106),
            'red': QColor(231, 111, 81)
        }
        for i, row in df.iterrows():
            for j, col in enumerate(df.columns):
                val = row[col]
                item = QTableWidgetItem(str(val))
                if categories and i < len(categories):
                    cat = categories[i]
                    color = color_map.get(cat, QColor(255, 255, 255))
                    item.setBackground(QBrush(color))
                    if cat in ('red', 'yellow'):
                        item.setForeground(QBrush(QColor(0, 0, 0)))
                    else:
                        item.setForeground(QBrush(QColor(0, 0, 0)))
                self.table_widget.setItem(i, j, item)
        self.table_widget.resizeColumnsToContents()

    def display_logic_errors(self, df_errors):
        self.logic_table_widget.clear()
        if df_errors is None or df_errors.empty:
            self.logic_table_widget.setRowCount(1)
            self.logic_table_widget.setColumnCount(1)
            self.logic_table_widget.setHorizontalHeaderLabels(["Информация"])
            self.logic_table_widget.setItem(0, 0, QTableWidgetItem("Логических ошибок не найдено"))
            return
        self.logic_table_widget.setRowCount(len(df_errors))
        self.logic_table_widget.setColumnCount(len(df_errors.columns))
        self.logic_table_widget.setHorizontalHeaderLabels(df_errors.columns)
        for i, row in df_errors.iterrows():
            for j, col in enumerate(df_errors.columns):
                item = QTableWidgetItem(str(row[col]))
                self.logic_table_widget.setItem(i, j, item)
        self.logic_table_widget.resizeColumnsToContents()

    def start_analysis(self):
        if self.current_df is None:
            return
        try:
            bal_text = self.balance_edit.text().strip().replace(',', '.')
            self.balance_currency = float(bal_text) if bal_text else None
        except ValueError:
            QMessageBox.warning(self, "Предупреждение", "Валюта баланса введена неверно, будет пропущена")
            self.balance_currency = None

        self.anomaly_threshold = self.threshold_spin.value()

        self.analysis_thread = AnalysisThread(self.filepath, self.balance_currency, self.anomaly_threshold)
        self.analysis_thread.finished.connect(self.on_analysis_finished)
        self.analysis_thread.error.connect(self.on_analysis_error)

        self.btn_analyze.setEnabled(False)
        self.statusBar().showMessage("Выполняется анализ...")
        self.progress = QProgressDialog("Анализ данных...", "Отмена", 0, 0, self)
        self.progress.setWindowModality(Qt.WindowModal)
        self.analysis_thread.start()

    def on_analysis_finished(self, df, anomaly_scores, logic_errors_df, materiality_info, graph_figure):
        self.progress.close()
        self.current_df = df
        self.anomaly_scores = anomaly_scores
        self.logic_errors_df = logic_errors_df
        self.graph_figure = graph_figure

        self.categories = self.classify_rows(df, anomaly_scores)
        self.display_table(df, anomaly_scores, self.categories)
        self.display_logic_errors(logic_errors_df)

        if materiality_info:
            percent, color, detail = materiality_info
            self.materiality_label.setText(f"Оценка существенности: {detail}")
            if color == "зеленый":
                bg = "#2A9D8F"
                fg = "white"
            elif color == "желтый":
                bg = "#E9C46A"
                fg = "black"
            elif color == "красный":
                bg = "#E76F51"
                fg = "white"
            else:
                bg = "#F0F4F8"
                fg = "black"
            self.materiality_card.setStyleSheet(
                f"background-color: {bg}; color: {fg}; border-radius: 8px; padding: 8px;"
            )
        else:
            self.materiality_label.setText("Оценка существенности: валюта баланса не задана")
            self.materiality_card.setStyleSheet("background-color: #F0F4F8; color: black;")

        self.btn_analyze.setEnabled(True)
        self.btn_graph.setEnabled(True)
        self.btn_export.setEnabled(True)
        self.statusBar().showMessage("Анализ завершён")

    def on_analysis_error(self, err_msg):
        self.progress.close()
        QMessageBox.critical(self, "Ошибка анализа", err_msg)
        self.btn_analyze.setEnabled(True)
        self.statusBar().showMessage("Ошибка анализа")

    def on_threshold_changed(self, value):
        if self.current_df is not None and self.anomaly_scores is not None:
            self.categories = self.classify_rows(self.current_df, self.anomaly_scores)
            self.display_table(self.current_df, self.anomaly_scores, self.categories)
            if self.balance_currency:
                mat_info = MaterialityEstimator.compute_materiality(
                    self.anomaly_scores, self.current_df, self.balance_currency, threshold=value
                )
                if mat_info:
                    percent, color, detail = mat_info
                    self.materiality_label.setText(f"Оценка существенности: {detail}")
                    if color == "зеленый":
                        bg = "#2A9D8F"
                        fg = "white"
                    elif color == "желтый":
                        bg = "#E9C46A"
                        fg = "black"
                    elif color == "красный":
                        bg = "#E76F51"
                        fg = "white"
                    else:
                        bg = "#F0F4F8"
                        fg = "black"
                    self.materiality_card.setStyleSheet(
                        f"background-color: {bg}; color: {fg}; border-radius: 8px; padding: 8px;"
                    )

    def show_graph(self):
        if self.graph_figure is None:
            QMessageBox.information(self, "Граф", "Граф ещё не построен. Выполните анализ.")
            return
        if not WEBENGINE_AVAILABLE:
            QMessageBox.warning(self, "Граф", "QtWebEngine не установлен. Невозможно отобразить интерактивный граф.")
            return

        # Создаём временный HTML файл и сохраняем граф
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
            html_path = tmp.name

        # ВАЖНО: include_plotlyjs='cdn' заставляет подгружать скрипты из сети.
        # Если у вас нет интернета, используйте include_plotlyjs='directory' (но потребуется папка рядом)
        self.graph_figure.write_html(html_path, include_plotlyjs='cdn')

        # Создаём окно графа
        self.graph_window = QWidget()
        self.graph_window.setWindowTitle("Интерактивный граф связей")
        self.graph_window.resize(1000, 700)

        layout = QVBoxLayout()

        # Инициализируем WebView
        web_view = QWebEngineView()

        #  🔥 ВОТ ТУТ ДОБАВЛЕНО РАЗРЕШЕНИЕ ДОСТУПА (Исправляет белый экран)
        from PyQt5.QtWebEngineWidgets import QWebEngineSettings
        settings = web_view.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.ErrorPageEnabled, True)

        # Загружаем файл
        web_view.setUrl(QUrl.fromLocalFile(os.path.abspath(html_path)))
        layout.addWidget(web_view)

        self.graph_window.setLayout(layout)

        # Сохраняем путь к файлу, чтобы удалить его при закрытии
        self.graph_window.temp_file = html_path
        self.graph_window.destroyed.connect(self.cleanup_temp_file)

        self.graph_window.show()

    def cleanup_temp_file(self):
        if hasattr(self, 'graph_window') and hasattr(self.graph_window, 'temp_file'):
            try:
                os.remove(self.graph_window.temp_file)
            except Exception:
                pass

    def export_report(self):
        if self.current_df is None or self.anomaly_scores is None:
            QMessageBox.warning(self, "Экспорт", "Сначала выполните анализ.")
            return
        filepath, _ = QFileDialog.getSaveFileName(self, "Сохранить отчёт", "report.html", "HTML files (*.html)")
        if not filepath:
            return
        mat_info = None
        if self.balance_currency:
            mat_info = MaterialityEstimator.compute_materiality(
                self.anomaly_scores, self.current_df, self.balance_currency, threshold=self.anomaly_threshold
            )
        try:
            ReportGenerator.generate_html(
                self.current_df, self.anomaly_scores,
                self.logic_errors_df, mat_info,
                self.graph_figure, filepath
            )
            QMessageBox.information(self, "Экспорт", f"Отчёт сохранён в {filepath}")
            reply = QMessageBox.question(
                self, "PDF",
                "Открыть HTML в браузере для печати в PDF?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                webbrowser.open(filepath)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить отчёт: {e}")

    def load_balance_from_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл с валютой баланса",
            "",
            "Excel files (*.xlsx *.xls);;CSV files (*.csv)"
        )
        if not filepath:
            return
        try:
            if filepath.endswith(('.xlsx', '.xls')):
                df_bal = pd.read_excel(filepath)
            else:
                try:
                    df_bal = pd.read_csv(filepath, encoding='utf-8')
                except:
                    df_bal = pd.read_csv(filepath, encoding='cp1251', sep=';')

            numeric_cols = []
            for col in df_bal.columns:
                if pd.to_numeric(df_bal[col], errors='coerce').notna().sum() > 0:
                    numeric_cols.append(col)

            if not numeric_cols:
                QMessageBox.warning(self, "Ошибка", "Не удалось найти числовые столбцы в файле.")
                return

            col = numeric_cols[0]
            found = None
            for val in df_bal[col]:
                try:
                    num = float(str(val).replace(',', '.'))
                    if num > 0:
                        found = num
                        break
                except:
                    continue

            if found is not None:
                self.balance_edit.setText(str(found))
                QMessageBox.information(self, "Успех", f"Валюта баланса загружена: {found}")
                if self.current_df is not None and self.anomaly_scores is not None:
                    self.balance_currency = found
                    self.on_threshold_changed(self.threshold_spin.value())
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось найти положительное число в выбранном столбце.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить файл: {e}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()