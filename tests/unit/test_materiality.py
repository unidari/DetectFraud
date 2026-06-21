import pytest
import pandas as pd
import numpy as np
from materiality import MaterialityEstimator

@pytest.mark.unit
class TestMateriality:
    def test_compute_materiality_no_balance(self):
        scores = np.array([0.96, 0.5, 0.98])
        df = pd.DataFrame({'сумма': [100, 200, 300]})
        result = MaterialityEstimator.compute_materiality(scores, df, None)
        assert result == (None, "серый", "Валюта баланса не задана")

    def test_compute_materiality_green(self):
        scores = np.array([0.96, 0.5])
        df = pd.DataFrame({'сумма': [10, 1000]})
        balance = 10000
        percent, color, detail = MaterialityEstimator.compute_materiality(scores, df, balance, threshold=0.95)
        assert percent < 5
        assert color == "зеленый"

    def test_compute_materiality_red(self):
        scores = np.array([0.96, 0.97])
        df = pd.DataFrame({'сумма': [1000, 2000]})
        balance = 10000
        percent, color, detail = MaterialityEstimator.compute_materiality(scores, df, balance, threshold=0.95)
        assert percent > 10
        assert color == "красный"