import pytest
import pandas as pd
import numpy as np
from report_generator import ReportGenerator
from graph_builder import GraphBuilder

@pytest.mark.unit
class TestReportGenerator:
    def test_generate_html(self, tmp_path):
        df = pd.DataFrame({
            'дебет': [100, 200],
            'кредит': [50, 100],
            'сумма': [150, 300],
            'дата': pd.to_datetime(['2025-01-01', '2025-01-02']),
            'описание': ['a', 'b']
        })
        scores = np.array([0.1, 0.9])
        logic_errors = pd.DataFrame()
        mat_info = (5.0, "зеленый", "5%")
        graph = GraphBuilder.build_interactive_graph(df)
        output = tmp_path / "report.html"
        ReportGenerator.generate_html(df, scores, logic_errors, mat_info, graph, str(output))
        assert output.exists()
        content = output.read_text(encoding='utf-8')
        assert "Отчёт DetecredFraud" in content