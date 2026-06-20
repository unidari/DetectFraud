# -*- coding: utf-8 -*-
import os
import base64
from datetime import datetime
from jinja2 import Template
import plotly.io as pio

try:
    import kaleido
    KALEIDO_AVAILABLE = True
except ImportError:
    KALEIDO_AVAILABLE = False


class ReportGenerator:
    @staticmethod
    def generate_html(df, anomaly_scores, logic_errors_df, materiality_info,
                      graph_figure, output_html_path):
        """Генерирует HTML-отчёт со скриншотом графа (или ссылкой на интерактивный HTML)."""
        # Таблица аномалий (топ-50)
        df_report = df.copy()
        df_report['Аномальность'] = anomaly_scores
        df_report = df_report.sort_values('Аномальность', ascending=False).head(50)
        anomalies_table = df_report[['дебет', 'кредит', 'дата', 'описание', 'сумма', 'Аномальность']].to_html(index=False)

        logic_table = logic_errors_df.to_html(
            index=False) if not logic_errors_df.empty else "<p>Логических ошибок не найдено</p>"

        # Скриншот графа или ссылка
        graph_image_html = ""
        if graph_figure:
            try:
                # Пытаемся сохранить PNG через kaleido
                if KALEIDO_AVAILABLE:
                    pio.write_image(graph_figure, 'temp_graph.png', format='png', width=800, height=600)
                    with open('temp_graph.png', 'rb') as f:
                        img_data = base64.b64encode(f.read()).decode()
                    graph_image_html = f'<img src="data:image/png;base64,{img_data}" alt="Граф связей" style="max-width:100%;">'
                    os.remove('temp_graph.png')
                else:
                    # Если kaleido нет, сохраняем интерактивный HTML и даём ссылку
                    html_graph_path = 'graph_interactive.html'
                    graph_figure.write_html(html_graph_path)
                    graph_image_html = (f'<p>Интерактивный граф доступен по <a href="{html_graph_path}" target="_blank">'
                                        f'ссылке</a> (откройте в браузере).</p>')
            except Exception as e:
                graph_image_html = f"<p>Не удалось создать скриншот графа: {e}</p>"
        else:
            graph_image_html = "<p>Граф не построен.</p>"

        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Отчёт DetecredFraud</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #2c3e50; }
                h2 { color: #34495e; border-bottom: 1px solid #ccc; }
                .materiality { padding: 15px; border-radius: 8px; margin: 10px 0; }
                .green { background-color: #d4edda; color: #155724; }
                .yellow { background-color: #fff3cd; color: #856404; }
                .red { background-color: #f8d7da; color: #721c24; }
                table { border-collapse: collapse; width: 100%; margin: 10px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <h1>Отчёт DetecredFraud</h1>
            <p>Дата генерации: {{ date }}</p>

            <h2>Оценка существенности ошибок</h2>
            <div class="materiality {{ materiality_color }}">
                <strong>{{ materiality_text }}</strong><br>
                Процент ошибки: {{ percent }}%<br>
                {{ materiality_detail }}
            </div>

            <h2>Аномальные проводки (Top 50 по аномальности)</h2>
            {{ anomalies_table | safe }}

            <h2>Логические ошибки</h2>
            {{ logic_table | safe }}

            <h2>Граф связей счетов</h2>
            {{ graph_image | safe }}

            <h2>Дополнительная информация</h2>
            <p>Всего обработано проводок: {{ total_rows }}<br>
            Метод выявления аномалий: Isolation Forest<br>
            Признаки: логарифм суммы, час/день недели, круглая сумма, частота пары счетов, односторонность, логика остатков.</p>
        </body>
        </html>
        """
        template = Template(template_str)
        materiality_color = materiality_info[1] if materiality_info else "серый"
        percent = f"{materiality_info[0]:.2f}" if materiality_info and materiality_info[0] is not None else "N/A"
        materiality_text = f"Риск штрафа: {materiality_color.upper()}"
        materiality_detail = materiality_info[2] if materiality_info else "Валюта баланса не задана"

        html_content = template.render(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            materiality_color=materiality_color,
            percent=percent,
            materiality_text=materiality_text,
            materiality_detail=materiality_detail,
            anomalies_table=anomalies_table,
            logic_table=logic_table,
            graph_image=graph_image_html,
            total_rows=len(df)
        )
        with open(output_html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return output_html_path