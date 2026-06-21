import pytest
import pandas as pd
from logic_validator import LogicValidator

@pytest.mark.unit
class TestLogicValidator:
    def test_validate_duplicates(self):
        df = pd.DataFrame({
            'дебет': [100, 100, 200],
            'кредит': [50, 50, 100],
            'сумма': [150, 150, 300],
            'дата': pd.to_datetime(['2025-01-01', '2025-01-01', '2025-01-02']),
            'описание': ['a', 'a', 'b']
        })
        # Добавляем служебные колонки (в реальности они создаются в загрузчике)
        df['счет_дебет'] = df['дебет'].astype(str)
        df['счет_кредит'] = df['кредит'].astype(str)

        errors_df, count = LogicValidator.validate(df)
        assert count >= 2  # первая и вторая – дубликаты
        # Проверим, что в ошибках есть упоминание дубликата
        assert 'Дублирующая' in errors_df['Ошибки'].iloc[0]

    def test_validate_zero_sum(self):
        df = pd.DataFrame({
            'дебет': [0, 100],
            'кредит': [0, 50],
            'сумма': [0, 150],
            'дата': pd.to_datetime(['2025-01-01', '2025-01-02']),
            'описание': ['a', 'b']
        })
        df['счет_дебет'] = df['дебет'].astype(str)
        df['счет_кредит'] = df['кредит'].astype(str)
        errors_df, count = LogicValidator.validate(df)
        assert count >= 1
        assert 'Дебет и кредит равны нулю' in errors_df['Ошибки'].iloc[0]

    def test_validate_balance(self):
        df = pd.DataFrame({
            'дебет': [100, 200],
            'кредит': [50, 100],
            'сумма': [150, 300],
            'дата': pd.to_datetime(['2025-01-01', '2025-01-02']),
            'описание': ['a', 'b']
        })
        df['счет_дебет'] = df['дебет'].astype(str)
        df['счет_кредит'] = df['кредит'].astype(str)
        df.loc[0, 'дебет'] = 100
        df.loc[0, 'кредит'] = 0
        df.loc[0, 'счет_дебет'] = '01'
        df.loc[0, 'счет_кредит'] = '01'
        df.loc[1, 'дебет'] = 0
        df.loc[1, 'кредит'] = 200
        df.loc[1, 'счет_дебет'] = '70'
        df.loc[1, 'счет_кредит'] = '70'

        errors_balance = LogicValidator.validate_balance(df)
        # Ожидаем одну ошибку: дебетовое сальдо на пассивном счете 70
        assert len(errors_balance) == 1
        assert errors_balance.iloc[0]['Счёт'] == '70'
        assert 'Дебетовое сальдо на пассивном счете' in errors_balance.iloc[0]['Ошибка']