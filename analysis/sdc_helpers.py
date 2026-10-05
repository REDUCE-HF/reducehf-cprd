import numpy as np
import pandas as pd


DISCLOSURE_THRESHOLD = 7


def apply_disclosure_control(column, threshold=DISCLOSURE_THRESHOLD):
    rounded = column.copy()
    mask = (column != 0) & (column <= threshold)
    rounded[mask] = 10
    rounded[~mask] = (rounded[~mask] / 5).round() * 5
    return rounded


def apply_sdc_to_counts(df, count_cols, threshold=DISCLOSURE_THRESHOLD):
    out = df.copy()

    for col in count_cols:
        if col in out.columns:
            out[col] = apply_disclosure_control(
                pd.to_numeric(out[col], errors="coerce"),
                threshold=threshold
            )

    return out