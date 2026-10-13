import numpy as np
import pandas as pd


def min_max_normalize(
    series: pd.Series, direction: str = "positive", min_bound: float = 0.01, max_bound: float = 1.00
) -> pd.Series:
    """
    Normaliseert een pandas Series strikt naar het bereik [min_bound, max_bound].
    Dit voorkomt 0.00 waarden die absoluut fataal zijn voor geometrische aggregatie
    (als één dimensie 0.00 is, wordt de hele boom 0.00).

    Args:
        series: Pandas series met numerieke waarden.
        direction: 'positive' (hoger initieel is beter eindresultaat) of 'negative' (lager initieel is beter).
        min_bound: De strikte ondergrens (default: 0.01).
        max_bound: De strikte bovengrens (default: 1.00).
    """

    # Check for empty series
    if series.empty:
        return series

    series_min = series.min()
    series_max = series.max()

    # Voorkom default division by zero als alle waarden in de set identiek zijn
    if series_min == series_max:
        return pd.Series(max_bound, index=series.index)

    if direction == "positive":
        normalized = (series - series_min) / (series_max - series_min)
    elif direction == "negative":
        normalized = (series_max - series) / (series_max - series_min)
    else:
        raise ValueError("Direction moet 'positive' of 'negative' zijn")

    # Schaal omhoog naar [min_bound, max_bound]
    scaled = normalized * (max_bound - min_bound) + min_bound
    return scaled


def geometric_aggregation(scores: pd.Series, weights: pd.Series) -> float:
    """
    Geometrische aggregatie (product van score^gewicht).
    Compenseert niet (een lage score trekt het geheel zwaar naar beneden).

    Args:
        scores: Genormaliseerde scores (strict > 0).
        weights: Gewichten (som is idealiter 1.0).
    """
    if (scores <= 0).any():
        raise ValueError("Scores voor geometrische aggregatie moeten strict > 0 zijn tbv wiskundige continuïteit.")

    return np.prod(np.power(scores, weights))


if __name__ == "__main__":
    print("--- Test: AI Kompas Normalisatie Pipeline ---")

    # 1. Dataset met inkomens (Positive benadering)
    inkomen = pd.Series([20000, 35000, 50000, 75000, 100000], name="Gemiddeld Inkomen")
    print(f"\nRuwe Inkomens Data:\n{inkomen.tolist()}")

    ge_norm_pos = min_max_normalize(inkomen, direction="positive")
    print(f"Genormaliseerd (+):\n{ge_norm_pos.round(3).tolist()}")

    # 2. Dataset met criminaliteit (Negative benadering)
    criminaliteit = pd.Series([5, 12, 12, 45, 110], name="Diefstal Aantal")
    print(f"\nRuwe Criminaliteit Data:\n{criminaliteit.tolist()}")

    ge_norm_neg = min_max_normalize(criminaliteit, direction="negative")
    print(f"Genormaliseerd (-):\n{ge_norm_neg.round(3).tolist()}")

    # 3. Aggregatietest
    scores = pd.Series([0.01, 0.90])  # Worst case in één domein, best-case in andere
    weights = pd.Series([0.5, 0.5])

    agg = geometric_aggregation(scores, weights)
    print(f"\nGeometrische Aggregatie Test:")
    print(f"Scores {scores.tolist()} met gelijke weging -> Resultaat: {round(agg, 3)}")
    print("Opmerking: Exact 0.00 had geresulteerd in 0.0 (fataal). 0.01 laat wat ruimte over.")
    print("\n✅ Normalisatiescript Gereed.")
