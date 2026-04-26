"""K-line candlestick pattern recognition.

Implements single, dual, and triple candlestick pattern detection
for technical analysis of stock price data.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Candle:
    """Single OHLC candle data."""
    date: str
    open: float
    close: float
    high: float
    low: float
    volume: float = 0

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def upper_shadow(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_shadow(self) -> float:
        return min(self.open, self.close) - self.low

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open


# ---------------------------------------------------------------------------
# Single-Candle Patterns
# ---------------------------------------------------------------------------


def is_hammer(c: Candle) -> bool:
    """Hammer: small body at top, long lower shadow (>= 2x body), small upper shadow."""
    if c.range == 0:
        return False
    if c.lower_shadow < c.body * 2:
        return False
    if c.upper_shadow > c.body:
        return False
    return True


def is_hanging_man(c: Candle) -> bool:
    """Hanging Man: same shape as hammer but appears at top of uptrend.

    Note: We detect the shape; trend context is determined by the caller.
    """
    return is_hammer(c)


def is_inverted_hammer(c: Candle) -> bool:
    """Inverted Hammer: small body at bottom, long upper shadow (>= 2x body), small lower shadow."""
    if c.range == 0:
        return False
    if c.upper_shadow < c.body * 2:
        return False
    if c.lower_shadow > c.body:
        return False
    return True


def is_shooting_star(c: Candle) -> bool:
    """Shooting Star: same shape as inverted hammer but at top of uptrend."""
    if c.range == 0:
        return False
    if c.upper_shadow < c.body * 2:
        return False
    if c.lower_shadow > c.body:
        return False
    return True


def is_doji(c: Candle) -> bool:
    """Doji: body is very small relative to total range (<= 10% of range)."""
    if c.range == 0:
        return True  # No movement at all
    return c.body <= c.range * 0.1


def is_dragonfly_doji(c: Candle) -> bool:
    """Dragonfly Doji: doji with long lower shadow and no upper shadow."""
    if not is_doji(c):
        return False
    if c.upper_shadow > c.body:
        return False
    if c.lower_shadow < c.range * 0.3:
        return False
    return True


def is_gravestone_doji(c: Candle) -> bool:
    """Gravestone Doji: doji with long upper shadow and no lower shadow."""
    if not is_doji(c):
        return False
    if c.lower_shadow > c.body:
        return False
    if c.upper_shadow < c.range * 0.3:
        return False
    return True


def is_marubozu(c: Candle) -> Optional[str]:
    """Marubozu: no shadows (or very small), large body.

    Returns 'bullish' or 'bearish', or None if not a marubozu.
    """
    if c.body == 0:
        return None
    # Shadows should be <= 5% of body
    max_shadow = c.body * 0.05
    if c.upper_shadow > max_shadow or c.lower_shadow > max_shadow:
        return None
    # Body should be significant (>= 60% of range)
    if c.range > 0 and c.body / c.range < 0.6:
        return None
    return "bullish" if c.is_bullish else "bearish"


# ---------------------------------------------------------------------------
# Dual-Candle Patterns
# ---------------------------------------------------------------------------


def is_bullish_engulfing(prev: Candle, curr: Candle) -> bool:
    """Bullish Engulfing: previous bearish, current bullish,
    current body completely engulfs previous body.
    """
    if not prev.is_bearish:
        return False
    if not curr.is_bullish:
        return False
    # Current body engulfs previous body:
    # curr.open < prev.close (opens below prev close) AND curr.close > prev.open (closes above prev open)
    if curr.open >= prev.close or curr.close <= prev.open:
        return False
    return True


def is_bearish_engulfing(prev: Candle, curr: Candle) -> bool:
    """Bearish Engulfing: previous bullish, current bearish,
    current body completely engulfs previous body.
    """
    if not prev.is_bullish:
        return False
    if not curr.is_bearish:
        return False
    # Current body engulfs previous body:
    # curr.open > prev.close (opens above prev close) AND curr.close < prev.open (closes below prev open)
    if curr.open <= prev.close or curr.close >= prev.open:
        return False
    return True


# ---------------------------------------------------------------------------
# Triple-Candle Patterns
# ---------------------------------------------------------------------------


def is_morning_star(c1: Candle, c2: Candle, c3: Candle) -> bool:
    """Morning Star: large bearish, small star, large bullish closing above
    midpoint of first candle.
    """
    # First candle: large bearish
    if not c1.is_bearish:
        return False
    # Second candle: small body (star)
    if c2.body > c1.body * 0.5:
        return False
    # Third candle: bullish
    if not c3.is_bullish:
        return False
    # Third candle closes above midpoint of first
    midpoint = (c1.open + c1.close) / 2
    if c3.close < midpoint:
        return False
    return True


def is_evening_star(c1: Candle, c2: Candle, c3: Candle) -> bool:
    """Evening Star: large bullish, small star, large bearish closing below
    midpoint of first candle.
    """
    # First candle: large bullish
    if not c1.is_bullish:
        return False
    # Second candle: small body (star)
    if c2.body > c1.body * 0.5:
        return False
    # Third candle: bearish
    if not c3.is_bearish:
        return False
    # Third candle closes below midpoint of first
    midpoint = (c1.open + c1.close) / 2
    if c3.close > midpoint:
        return False
    return True


def is_three_white_soldiers(c1: Candle, c2: Candle, c3: Candle) -> bool:
    """Three White Soldiers: three consecutive bullish candles,
    each opening within previous body and closing higher.
    """
    if not (c1.is_bullish and c2.is_bullish and c3.is_bullish):
        return False
    # Each opens within previous body (c2.open between c1.close and c1.open)
    if not (min(c1.open, c1.close) <= c2.open <= max(c1.open, c1.close)):
        return False
    if not (min(c2.open, c2.close) <= c3.open <= max(c2.open, c2.close)):
        return False
    # Each closes higher than previous
    if c2.close <= c1.close or c3.close <= c2.close:
        return False
    return True


def is_three_black_crows(c1: Candle, c2: Candle, c3: Candle) -> bool:
    """Three Black Crows: three consecutive bearish candles,
    each opening within previous body and closing lower.
    """
    if not (c1.is_bearish and c2.is_bearish and c3.is_bearish):
        return False
    # Each opens within previous body (c2.open between c1.close and c1.open)
    if not (min(c1.open, c1.close) <= c2.open <= max(c1.open, c1.close)):
        return False
    if not (min(c2.open, c2.close) <= c3.open <= max(c2.open, c2.close)):
        return False
    # Each closes lower than previous
    if c2.close >= c1.close or c3.close >= c2.close:
        return False
    return True


# ---------------------------------------------------------------------------
# Combined Pattern Detection
# ---------------------------------------------------------------------------

# Pattern result structure
PATTERN_RESULT = {
    "name": str,       # Pattern name (Chinese)
    "name_en": str,    # Pattern name (English)
    "date": str,       # Date of the pattern (last candle)
    "type": str,       # 'bullish' or 'bearish'
    "category": str,   # 'single', 'dual', or 'triple'
}


def detect_patterns(candles: list[Candle]) -> list[dict]:
    """Scan candle data and return all recognized patterns.

    Returns a list of dicts with keys: name, name_en, date, type, category.
    """
    results: list[dict] = []

    # Single-candle patterns
    for c in candles:
        if is_hammer(c):
            results.append({
                "name": "锤子线",
                "name_en": "Hammer",
                "date": c.date,
                "type": "bullish",
                "category": "single",
            })
        if is_shooting_star(c):
            results.append({
                "name": "射击之星",
                "name_en": "Shooting Star",
                "date": c.date,
                "type": "bearish",
                "category": "single",
            })
        if is_doji(c) and not is_dragonfly_doji(c) and not is_gravestone_doji(c):
            results.append({
                "name": "十字星",
                "name_en": "Doji",
                "date": c.date,
                "type": "neutral",
                "category": "single",
            })
        if is_dragonfly_doji(c):
            results.append({
                "name": "蜻蜓十字",
                "name_en": "Dragonfly Doji",
                "date": c.date,
                "type": "bullish",
                "category": "single",
            })
        if is_gravestone_doji(c):
            results.append({
                "name": "墓碑十字",
                "name_en": "Gravestone Doji",
                "date": c.date,
                "type": "bearish",
                "category": "single",
            })
        marubozu_type = is_marubozu(c)
        if marubozu_type:
            results.append({
                "name": "光头光脚阳线" if marubozu_type == "bullish" else "光头光脚阴线",
                "name_en": f"{'Bullish' if marubozu_type == 'bullish' else 'Bearish'} Marubozu",
                "date": c.date,
                "type": marubozu_type,
                "category": "single",
            })

    # Dual-candle patterns
    for i in range(1, len(candles)):
        prev, curr = candles[i - 1], candles[i]
        if is_bullish_engulfing(prev, curr):
            results.append({
                "name": "看涨吞没",
                "name_en": "Bullish Engulfing",
                "date": curr.date,
                "type": "bullish",
                "category": "dual",
            })
        if is_bearish_engulfing(prev, curr):
            results.append({
                "name": "看跌吞没",
                "name_en": "Bearish Engulfing",
                "date": curr.date,
                "type": "bearish",
                "category": "dual",
            })

    # Triple-candle patterns
    for i in range(2, len(candles)):
        c1, c2, c3 = candles[i - 2], candles[i - 1], candles[i]
        if is_morning_star(c1, c2, c3):
            results.append({
                "name": "启明星",
                "name_en": "Morning Star",
                "date": c3.date,
                "type": "bullish",
                "category": "triple",
            })
        if is_evening_star(c1, c2, c3):
            results.append({
                "name": "黄昏星",
                "name_en": "Evening Star",
                "date": c3.date,
                "type": "bearish",
                "category": "triple",
            })
        if is_three_white_soldiers(c1, c2, c3):
            results.append({
                "name": "红三兵",
                "name_en": "Three White Soldiers",
                "date": c3.date,
                "type": "bullish",
                "category": "triple",
            })
        if is_three_black_crows(c1, c2, c3):
            results.append({
                "name": "三只乌鸦",
                "name_en": "Three Black Crows",
                "date": c3.date,
                "type": "bearish",
                "category": "triple",
            })

    return results
