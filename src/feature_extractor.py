# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from utils import get_account_type, is_round_sum
from sklearn.preprocessing import StandardScaler

class FeatureExtractor:
    @staticmethod
    def extract_features(df):
        # --- ПРИНУДИТЕЛЬНОЕ СОЗДАНИЕ СЛУЖЕБНЫХ КОЛОНОК (даже если есть) ---
        df['счет_дебет'] = df['дебет'].astype(str).str.split('.').str[0]
        df['счет_кредит'] = df['кредит'].astype(str).str.split('.').str[0]
        # --------------------------------------------------------------------

        df_feat = pd.DataFrame(index=df.index)

        # 1. Логарифм суммы (СОЗДАЕМ СРАЗУ В df_feat)
        summa = df['сумма'].astype(float)
        df_feat['log_sum'] = np.log1p(df['сумма'].fillna(0).clip(lower=0))

        # 2. Время
        dt = df['дата']
        df_feat['hour'] = dt.dt.hour.fillna(12).astype(int)
        df_feat['dayofweek'] = dt.dt.dayofweek.fillna(0).astype(int)

        # 3. Круглая сумма
        df_feat['round_sum'] = summa.apply(lambda x: 1 if is_round_sum(x, 1000) else 0)

        # 4. Частота пары счетов (исправленный merge)
        pair_counts = df.groupby(['счет_дебет', 'счет_кредит']).size().reset_index(name='count')
        pair_counts['freq'] = pair_counts['count'] / len(df)
        # Временно добавляем колонки в df_feat для слияния
        df_feat['счет_дебет'] = df['счет_дебет']
        df_feat['счет_кредит'] = df['счет_кредит']
        df_feat = df_feat.merge(pair_counts[['счет_дебет', 'счет_кредит', 'freq']],
                                on=['счет_дебет', 'счет_кредит'], how='left')
        df_feat['pair_frequency'] = df_feat['freq'].fillna(0)
        # Удаляем временные колонки
        df_feat.drop(['freq', 'счет_дебет', 'счет_кредит'], axis=1, inplace=True)

        # 5. Односторонность
        df_feat['is_debit_only'] = ((df['дебет'] > 0) & (df['кредит'] == 0)).astype(int)
        df_feat['is_credit_only'] = ((df['дебет'] == 0) & (df['кредит'] > 0)).astype(int)

        # 6. Логика остатков (аномальное сальдо) – векторизованный расчёт
        debit_total = df.groupby('счет_дебет')['дебет'].sum()
        credit_total = df.groupby('счет_кредит')['кредит'].sum()
        total_balance = debit_total.add(credit_total, fill_value=0)

        def get_account_type_with_fallback(acc):
            t = get_account_type(acc)
            if t is not None:
                return t
            bal = total_balance.get(acc, 0)
            return 'active' if bal >= 0 else 'passive'

        def get_debit_sign(acc):
            t = get_account_type_with_fallback(acc)
            return 1 if t == 'active' else -1

        def get_credit_sign(acc):
            t = get_account_type_with_fallback(acc)
            return -1 if t == 'active' else 1

        df['debit_sign'] = df['счет_дебет'].map(get_debit_sign).fillna(0)
        df['credit_sign'] = df['счет_кредит'].map(get_credit_sign).fillna(0)

        debit_balance = (df['дебет'] * df['debit_sign']).groupby(df['счет_дебет']).sum()
        credit_balance = (df['кредит'] * df['credit_sign']).groupby(df['счет_кредит']).sum()
        balance = debit_balance.add(credit_balance, fill_value=0)

        def is_abnormal(acc):
            bal = balance.get(acc, 0)
            t = get_account_type_with_fallback(acc)
            if t == 'active':
                return 1 if bal < 0 else 0
            else:
                return 1 if bal > 0 else 0

        df_feat['abnormal_balance_debit'] = df['счет_дебет'].map(is_abnormal).fillna(0)
        df_feat['abnormal_balance_credit'] = df['счет_кредит'].map(is_abnormal).fillna(0)

        df.drop(['debit_sign', 'credit_sign'], axis=1, inplace=True)

        # 7. Масштабирование числовых признаков
        cols_to_scale = ['log_sum', 'hour', 'dayofweek', 'pair_frequency']

        scaler = StandardScaler()
        df_feat[cols_to_scale] = scaler.fit_transform(df_feat[cols_to_scale])

        return df_feat.fillna(0)