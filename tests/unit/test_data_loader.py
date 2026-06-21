import pytest
import pandas as pd
import os
from data_loader import DataLoader

@pytest.mark.unit
class TestDataLoader:
    def test_load_valid_excel(self, tmp_path):
        # Создаём временный Excel с правильными колонками
        df_test = pd.DataFrame({
            'дебет': [100, 200],
            'кредит': [50, 150],
            'дата': ['2025-01-01', '2025-01-02'],
            'сумма': [150, 350],
            'описание': ['test1', 'test2']
        })
        file_path = tmp_path / "test.xlsx"
        df_test.to_excel(file_path, index=False)

        df, err, mapping = DataLoader.load_file(str(file_path))
        assert err is None
        assert df is not None
        assert 'счет_дебет' in df.columns
        assert 'счет_кредит' in df.columns
        # Вместо assert df['дебет'].dtype == float
        assert pd.api.types.is_numeric_dtype(df['дебет'])
        assert len(df) == 2

    def test_load_missing_columns(self, tmp_path):
        df_bad = pd.DataFrame({'col1': [1,2], 'col2': [3,4]})
        file_path = tmp_path / "bad.xlsx"
        df_bad.to_excel(file_path, index=False)

        df, err, mapping = DataLoader.load_file(str(file_path))
        assert df is None
        assert err is not None
        assert "Не удалось найти колонки" in err

    def test_fuzzy_matching(self, tmp_path):
        # Проверим, что синонимы работают
        df_test = pd.DataFrame({
            'debit': [100],
            'credit': [50],
            'date': ['2025-01-01'],
            'amount': [150],
            'desc': ['test']
        })
        file_path = tmp_path / "fuzzy.xlsx"
        df_test.to_excel(file_path, index=False)
        df, err, mapping = DataLoader.load_file(str(file_path))
        assert err is None
        assert 'дебет' in df.columns
        assert 'кредит' in df.columns
        assert 'дата' in df.columns
        assert 'сумма' in df.columns
        assert 'описание' in df.columns

    def test_empty_file(self, tmp_path):
        df_empty = pd.DataFrame()
        file_path = tmp_path / "empty.xlsx"
        df_empty.to_excel(file_path, index=False)
        df, err, _ = DataLoader.load_file(str(file_path))
        assert df is None
        assert "Файл пуст" in err