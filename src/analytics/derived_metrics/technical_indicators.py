# src/analytics/derived_metrics/technical_indicators.py

import pandas as pd

from src.analytics.derived_metrics.market_analysis import get_price_dataframe


def add_simple_moving_average(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """Add simple moving average column."""

    df[f"sma_{window}"] = df["price"].rolling(window=window).mean()
    return df


def add_exponential_moving_average(df: pd.DataFrame, span: int) -> pd.DataFrame:
    """Add exponential moving average column."""

    df[f"ema_{span}"] = df["price"].ewm(span=span, adjust=False).mean()
    return df


def add_rsi(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """Add Relative Strength Index."""

    delta = df["price"].diff()

    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    average_gain = gains.rolling(window=window).mean()
    average_loss = losses.rolling(window=window).mean()

    relative_strength = average_gain / average_loss
    df[f"rsi_{window}"] = 100 - (100 / (1 + relative_strength))

    return df


def add_macd(
    df: pd.DataFrame,
    short_span: int = 12,
    long_span: int = 26,
    signal_span: int = 9,
) -> pd.DataFrame:
    """Add MACD, signal line, and histogram."""

    short_ema = df["price"].ewm(span=short_span, adjust=False).mean()
    long_ema = df["price"].ewm(span=long_span, adjust=False).mean()

    df["macd"] = short_ema - long_ema
    df["macd_signal"] = df["macd"].ewm(span=signal_span, adjust=False).mean()
    df["macd_histogram"] = df["macd"] - df["macd_signal"]

    return df


def add_bollinger_bands(
    df: pd.DataFrame,
    window: int = 20,
    num_std: float = 2.0,
) -> pd.DataFrame:
    """Add Bollinger Band columns."""

    rolling_mean = df["price"].rolling(window=window).mean()
    rolling_std = df["price"].rolling(window=window).std()

    df[f"bollinger_middle_{window}"] = rolling_mean
    df[f"bollinger_upper_{window}"] = rolling_mean + num_std * rolling_std
    df[f"bollinger_lower_{window}"] = rolling_mean - num_std * rolling_std

    return df


def add_volume_moving_average(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Add volume moving average."""

    df[f"volume_sma_{window}"] = df["volume"].rolling(window=window).mean()
    return df


def calculate_technical_indicators(ticker: str) -> pd.DataFrame:
    """Calculate common technical indicators from stored market data."""

    df = get_price_dataframe(ticker)

    if df.empty:
        return df

    df = add_simple_moving_average(df, 20)
    df = add_simple_moving_average(df, 50)
    df = add_simple_moving_average(df, 200)

    df = add_exponential_moving_average(df, 12)
    df = add_exponential_moving_average(df, 26)

    df = add_rsi(df, 14)
    df = add_macd(df)
    df = add_bollinger_bands(df, 20)
    df = add_volume_moving_average(df, 20)

    return df


def calculate_latest_technical_snapshot(ticker: str) -> dict:
    """Return the latest technical indicator values for a ticker."""

    df = calculate_technical_indicators(ticker)

    if df.empty:
        return {"ticker": ticker.upper().strip(), "technical_indicators": None}

    latest = df.iloc[-1]

    volume = latest.get("volume")
    volume_sma_20 = latest.get("volume_sma_20")

    volume_ratio = None

    if (
        volume is not None
        and volume_sma_20 is not None
        and pd.notna(volume)
        and pd.notna(volume_sma_20)
        and volume_sma_20 != 0
    ):
        volume_ratio = float(volume) / float(volume_sma_20)
        
    return {
        "ticker": ticker.upper().strip(),
        "date": latest["date"],
        "price": latest["price"],
        "volume": volume,
        "sma_20": latest.get("sma_20"),
        "sma_50": latest.get("sma_50"),
        "sma_200": latest.get("sma_200"),
        "ema_12": latest.get("ema_12"),
        "ema_26": latest.get("ema_26"),
        "rsi_14": latest.get("rsi_14"),
        "macd": latest.get("macd"),
        "macd_signal": latest.get("macd_signal"),
        "macd_histogram": latest.get("macd_histogram"),
        "bollinger_middle_20": latest.get("bollinger_middle_20"),
        "bollinger_upper_20": latest.get("bollinger_upper_20"),
        "bollinger_lower_20": latest.get("bollinger_lower_20"),
        "volume_sma_20": volume_sma_20,
        "volume_ratio": volume_ratio,
    }