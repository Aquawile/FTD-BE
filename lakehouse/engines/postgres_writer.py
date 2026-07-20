"""Write pandas DataFrames to PostgreSQL tables."""

from __future__ import annotations

import logging
from typing import Sequence

import pandas as pd
import psycopg2
import psycopg2.extras

from lakehouse.config import LakehouseSettings

logger = logging.getLogger(__name__)

_BATCH_SIZE = 1000


def _connect(settings: LakehouseSettings) -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )


def _coerce_for_postgres(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            continue
        sample = df[col].dropna()
        if len(sample) > 0 and not isinstance(sample.iloc[0], str):
            continue
        df[col] = df[col].fillna("").replace("", "")
    return df


def _column_defs(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    columns = list(df.columns)
    quoted = [f'"{c}"' if c.lower() in ("timestamp", "current", "date", "user") else c for c in columns]
    return columns, quoted


def _py_type_to_pg(dtype) -> str:
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "TIMESTAMP"
    if pd.api.types.is_integer_dtype(dtype):
        return "BIGINT"
    if pd.api.types.is_float_dtype(dtype):
        return "DOUBLE PRECISION"
    if pd.api.types.is_bool_dtype(dtype):
        return "BOOLEAN"
    return "TEXT"


def _create_table_if_missing(settings: LakehouseSettings, table_name: str, df: pd.DataFrame) -> None:
    columns, quoted = _column_defs(df)
    col_defs = ", ".join(f'{q} {_py_type_to_pg(df[c].dtype)}' for q, c in zip(quoted, columns))
    ddl = f'CREATE TABLE IF NOT EXISTS {table_name} ({col_defs});'
    conn = _connect(settings)
    cur = conn.cursor()
    try:
        cur.execute(ddl)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def _df_to_values(df: pd.DataFrame):
    for row in df.itertuples(index=False, name=None):
        yield tuple(None if pd.isna(v) else v for v in row)


def write_frame(settings: LakehouseSettings, table_name: str, df: pd.DataFrame) -> None:
    if not settings.postgres_enabled:
        return
    if df.empty:
        return

    df = _coerce_for_postgres(df)
    columns, quoted = _column_defs(df)
    col_names = ", ".join(quoted)
    insert_sql = f"INSERT INTO {table_name} ({col_names}) VALUES %s"

    _create_table_if_missing(settings, table_name, df)

    conn = _connect(settings)
    cur = conn.cursor()
    try:
        psycopg2.extras.execute_values(cur, insert_sql, _df_to_values(df), page_size=_BATCH_SIZE)
        conn.commit()
        logger.info("Inserted %d rows into PostgreSQL %s", len(df), table_name)
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def truncate_table(settings: LakehouseSettings, table_name: str) -> None:
    if not settings.postgres_enabled:
        return
    conn = _connect(settings)
    cur = conn.cursor()
    try:
        cur.execute(f"TRUNCATE TABLE {table_name} CASCADE;")
        conn.commit()
        logger.info("Truncated PostgreSQL table %s", table_name)
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
