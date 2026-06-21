# -*- coding: utf-8 -*-
import pandas as pd
from utils import get_account_type


class LogicValidator:
    @staticmethod
    def validate(df):
        """Возвращает DataFrame с логическими ошибками и их количество."""
        # Гарантируем наличие служебных колонок (на случай, если их нет)
        if 'счет_дебет' not in df.columns:
            df['счет_дебет'] = df['дебет'].astype(str).str.split('.').str[0]
        if 'счет_кредит' not in df.columns:
            df['счет_кредит'] = df['кредит'].astype(str).str.split('.').str[0]

        # --- Проверка на дублирующие проводки ---
        # Создаём временную колонку с датой без времени (по дням)
        df['date_day'] = df['дата'].dt.date
        duplicates_mask = df.duplicated(
            subset=['дебет', 'кредит', 'сумма', 'date_day'],
            keep=False
        )

        # --- Базовые логические маски (остальные проверки) ---
        mask_sum = df['сумма'] <= 0
        mask_date = pd.isna(df['дата'])
        mask_desc = df['описание'].isna() | (df['описание'].astype(str).str.strip() == '')
        mask_zero = (df['дебет'] == 0) & (df['кредит'] == 0)
        mask_same = (df['счет_дебет'] == df['счет_кредит']) & (df['дебет'] > 0) & (df['кредит'] > 0)
        mask_one_side = ((df['дебет'] > 0) & (df['кредит'] == 0)) | ((df['дебет'] == 0) & (df['кредит'] > 0))

        # Объединяем все маски (включая дубликаты)
        any_error = mask_sum | mask_date | mask_desc | mask_zero | mask_same | mask_one_side | duplicates_mask

        error_indices = any_error[any_error].index

        errors = []
        for idx in error_indices:
            row = df.loc[idx]
            err_desc = []
            if mask_sum[idx]:
                err_desc.append("Сумма <= 0")
            if mask_date[idx]:
                err_desc.append("Некорректная дата")
            if mask_desc[idx]:
                err_desc.append("Отсутствует описание")
            if mask_zero[idx]:
                err_desc.append("Дебет и кредит равны нулю")
            if mask_same[idx]:
                err_desc.append("Дебетовый и кредитовый счета совпадают")
            if mask_one_side[idx]:
                err_desc.append("Односторонняя проводка (только дебет или только кредит)")
            if duplicates_mask[idx]:
                err_desc.append("Дублирующая проводка (одинаковые дебет, кредит, сумма, дата)")

            errors.append({
                'Индекс': idx,
                'Дебет': row['дебет'],
                'Кредит': row['кредит'],
                'Дата': row['дата'],
                'Описание': row['описание'][:50],
                'Ошибки': '; '.join(err_desc)
            })

        if errors:
            return pd.DataFrame(errors), len(errors)
        else:
            return pd.DataFrame(), 0

    @staticmethod
    def validate_balance(df):
        """Возвращает DataFrame с ошибками по остаткам на счетах (векторизованный расчёт)."""
        # Гарантируем наличие служебных колонок
        if 'счет_дебет' not in df.columns:
            df['счет_дебет'] = df['дебет'].astype(str).str.split('.').str[0]
        if 'счет_кредит' not in df.columns:
            df['счет_кредит'] = df['кредит'].astype(str).str.split('.').str[0]

        # Определяем знаки для дебета и кредита в зависимости от типа счета
        def get_debit_sign(acc):
            t = get_account_type(acc)
            if t == 'active':
                return 1
            elif t == 'passive':
                return -1
            else:
                return 0

        def get_credit_sign(acc):
            t = get_account_type(acc)
            if t == 'active':
                return -1
            elif t == 'passive':
                return 1
            else:
                return 0

        # Временные колонки для знаков
        df['debit_sign'] = df['счет_дебет'].map(get_debit_sign).fillna(0)
        df['credit_sign'] = df['счет_кредит'].map(get_credit_sign).fillna(0)

        # Группируем взвешенные суммы по счетам
        debit_balance = (df['дебет'] * df['debit_sign']).groupby(df['счет_дебет']).sum()
        credit_balance = (df['кредит'] * df['credit_sign']).groupby(df['счет_кредит']).sum()
        balance = debit_balance.add(credit_balance, fill_value=0)

        errors = []
        for acc, bal in balance.items():
            typ = get_account_type(acc)
            if typ == 'active' and bal < 0:
                errors.append({
                    'Индекс': '—',
                    'Счёт': acc,
                    'Сальдо': bal,
                    'Тип': 'active',
                    'Ошибка': 'Кредитовое сальдо на активном счете'
                })
            elif typ == 'passive' and bal > 0:
                errors.append({
                    'Индекс': '—',
                    'Счёт': acc,
                    'Сальдо': bal,
                    'Тип': 'passive',
                    'Ошибка': 'Дебетовое сальдо на пассивном счете'
                })
        # Удаляем временные колонки
        df.drop(['debit_sign', 'credit_sign'], axis=1, inplace=True)
        return pd.DataFrame(errors)