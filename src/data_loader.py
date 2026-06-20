# -*- coding: utf-8 -*-
import os
import pandas as pd
from collections import Counter

try:
    from fuzzywuzzy import fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    print("fuzzywuzzy не установлена. Будет использован встроенный difflib.")

class DataLoader:
    SYNONYMS = {
        'дебет': [
            'дебет', 'debit', 'дт', 'dt', 'дебет сч', 'дебетовый', 'дебет счета', 'дебет счёт',
            'дебетовое сальдо', 'дебетовый счет', 'dt_acc', 'debit_account', 'дебет_счета', 'счет_дебет'
        ],
        'кредит': [
            'кредит', 'credit', 'кт', 'ct', 'кредит сч', 'кредитовый', 'кредит счета', 'кредит счёт',
            'кредитовое сальдо', 'кредитовый счет', 'ct_acc', 'credit_account', 'кредит_счета', 'счет_кредит'
        ],
        'сумма': [
            'сумма', 'sum', 'amount', 'всего', 'итого', 'общая сумма', 'сумма операции', 'сумма проводки',
            'transaction_sum', 'total', 'value', 'total_amount', 'сумма_операции', 'сумма_проводки', 'сумма_документа'
        ],
        'дата': [
            'дата', 'date', 'день', 'период', 'дата операции', 'дата проводки',
            'trans_date', 'doc_date', 'posting_date', 'op_date', 'date_operation', 'дата_операции', 'дата_документа'
        ],
        'описание': [
            'описание', 'description', 'назначение', 'назначение платежа', 'комментарий', 'пояснение',
            'текст', 'примечание', 'comment', 'note', 'remark', 'posting_text', 'purpose', 'details', 'основание'
        ]
    }

    @staticmethod
    def _best_column(candidates, df, expected_type='numeric'):
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        best_col = None
        best_score = -1
        for col in candidates:
            series = df[col]
            non_null = series.notna().sum()
            if expected_type == 'numeric':
                numeric_series = pd.to_numeric(series, errors='coerce')
                numeric_count = numeric_series.notna().sum()
                score = non_null * 0.5 + numeric_count * 0.5
            else:
                non_empty = series.astype(str).str.strip().ne('').sum()
                score = non_empty
            if score > best_score:
                best_score = score
                best_col = col
        return best_col

    @staticmethod
    def _fuzzy_match_score(col_name, synonyms):
        if FUZZY_AVAILABLE:
            return max(fuzz.token_set_ratio(col_name, syn) for syn in synonyms)
        else:
            import difflib
            return max(difflib.SequenceMatcher(None, col_name, syn).ratio() * 100 for syn in synonyms)

    @staticmethod
    def load_file(filepath):
        ext = os.path.splitext(filepath)[1].lower()
        try:
            if ext in ['.xlsx', '.xls']:
                df = pd.read_excel(filepath, dtype=str)
            elif ext == '.csv':
                try:
                    df = pd.read_csv(filepath, encoding='utf-8', dtype=str)
                except:
                    df = pd.read_csv(filepath, encoding='cp1251', dtype=str, sep=';')
            else:
                return None, "Неподдерживаемый формат файла.", None

            if df.empty:
                return None, "Файл пуст.", None

            df = df.copy()

            orig_columns = df.columns.tolist()
            clean_columns = [col.lower().strip() for col in orig_columns]
            clean_to_orig = {clean: orig for clean, orig in zip(clean_columns, orig_columns)}

            candidates = {std: [] for std in DataLoader.SYNONYMS.keys()}
            threshold = 70

            for col, clean_col in zip(orig_columns, clean_columns):
                for std, synonyms in DataLoader.SYNONYMS.items():
                    if clean_col in synonyms or any(syn in clean_col for syn in synonyms):
                        candidates[std].append(col)
                    else:
                        score = DataLoader._fuzzy_match_score(clean_col, synonyms)
                        if score >= threshold:
                            candidates[std].append(col)

            mapping = {}
            mapping_details = {}
            for std, cols in candidates.items():
                if not cols:
                    continue
                expected = 'numeric' if std in ('дебет', 'кредит', 'сумма') else 'text'
                best = DataLoader._best_column(cols, df, expected_type=expected)
                if best:
                    mapping[std] = best
                    mapping_details[std] = best

            required = ['дебет', 'кредит', 'дата']
            missing = [col for col in required if col not in mapping]
            if missing:
                return None, f"Не удалось найти колонки для: {', '.join(missing)}. " \
                             f"Проверьте названия столбцов (допустимы синонимы: дебет, кредит, дата).", None

            rename_dict = {orig: std for std, orig in mapping.items()}
            df.rename(columns=rename_dict, inplace=True)

            # --- Преобразование данных ---
            if 'сумма' not in df.columns:
                df['сумма'] = df[['дебет', 'кредит']].max(axis=1)
                df.loc[df['сумма'] == 0, 'сумма'] = df['дебет'] + df['кредит']
            else:
                df['сумма'] = pd.to_numeric(df['сумма'], errors='coerce').fillna(0)

            for col in ['дебет', 'кредит']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            df['дата'] = pd.to_datetime(df['дата'], errors='coerce')

            if 'описание' in df.columns:
                df['описание'] = df['описание'].astype(str).fillna('')
            else:
                df['описание'] = ''

            # --- СОЗДАНИЕ СЛУЖЕБНЫХ КОЛОНОК (ГАРАНТИРОВАННО) ---
            df['счет_дебет'] = df['дебет'].astype(str).str.split('.').str[0]
            df['счет_кредит'] = df['кредит'].astype(str).str.split('.').str[0]

            info_lines = []
            for std, orig in mapping.items():
                info_lines.append(f"  • {std} → '{orig}'")
            mapping_info = {
                'mapping': mapping,
                'message': "Сопоставление колонок выполнено:\n" + "\n".join(info_lines)
            }

            return df, None, mapping_info

        except Exception as e:
            return None, f"Ошибка при загрузке: {str(e)}", None