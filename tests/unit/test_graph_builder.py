import pytest
import pandas as pd
from graph_builder import GraphBuilder

@pytest.mark.unit
class TestGraphBuilder:
    def test_build_graph_basic(self):
        df = pd.DataFrame({
            'дебет': [100, 200],
            'кредит': [50, 100],
            'сумма': [150, 300],
            'дата': pd.to_datetime(['2025-01-01', '2025-01-02']),
            'описание': ['a', 'b']
        })
        fig = GraphBuilder.build_interactive_graph(df)
        assert fig is not None
        assert hasattr(fig, 'to_html')

    def test_build_graph_empty_df(self):
        df = pd.DataFrame(columns=['дебет', 'кредит', 'сумма'])
        fig = GraphBuilder.build_interactive_graph(df)
        # Должен вернуть фигуру без ошибок, хотя граф будет пустым
        assert fig is not None