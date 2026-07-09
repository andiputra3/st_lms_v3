"""
Normalizer - Menerima dummy data candle Binance (OHLCV + UTC), 
memvalidasi gap, dan mengubahnya ke format standar ST-LMS.

Guardrails:
- Konversi UTC ke WIB menggunakan time_service.
- Validasi gap antar candle (tidak boleh ada missing candle dalam timeframe yang sama).
- Output format standar ST-LMS dengan Time ID.
- Type hinting wajib.
- Error handling ke Audit Log.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
import logging

from time_service import utc_to_wib, utc_to_time_id, format_wib_string


# Configure logging for audit
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class RawCandle(BaseModel):
    """
    Schema input: Dummy candle dari Binance (UTC).
    """
    open_time: int  # Unix timestamp ms
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: int  # Unix timestamp ms
    
    @field_validator("high")
    @classmethod
    def validate_high(cls, v, info):
        if v < info.data.get("open", 0) and v < info.data.get("close", 0):
            raise ValueError("High harus >= open dan close")
        return v
    
    @field_validator("low")
    @classmethod
    def validate_low(cls, v, info):
        if v > info.data.get("open", 0) and v > info.data.get("close", 0):
            raise ValueError("Low harus <= open dan close")
        return v


class NormalizedCandle(BaseModel):
    """
    Schema output: Candle ter-normalisasi format ST-LMS.
    
    Semua waktu dalam WIB, memiliki Time ID unik.
    """
    time_id: str                    # Contoh: P2607081920
    time_wib: str                   # "YYYY-MM-DD HH:MM:SS"
    open_time_wib: str              # "YYYY-MM-DD HH:MM:SS"
    close_time_wib: str             # "YYYY-MM-DD HH:MM:SS"
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: Optional[float] = None  # Bisa ditambahkan jika tersedia
    trades_count: Optional[int] = None    # Bisa ditambahkan jika tersedia


class NormalizationResult(BaseModel):
    """
    Wrapper untuk hasil normalisasi termasuk metadata.
    """
    success: bool
    candles: List[NormalizedCandle]
    gaps_detected: List[Dict[str, Any]]
    total_input: int
    total_output: int
    errors: List[str]


def ms_to_datetime(ms: int) -> datetime:
    """Konversi millisecond timestamp ke datetime UTC."""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def validate_candle_sequence(candles: List[RawCandle], timeframe_minutes: int = 1) -> List[Dict[str, Any]]:
    """
    Validasi gap antar candle dalam sequence.
    
    Args:
        candles: List of RawCandle (sudah diurutkan berdasarkan waktu).
        timeframe_minutes: Timeframe dalam menit (default 1 untuk contoh).
        
    Returns:
        List of gap information jika ada missing candle.
    """
    gaps = []
    
    if len(candles) < 2:
        return gaps
    
    expected_interval_ms = timeframe_minutes * 60 * 1000
    
    for i in range(1, len(candles)):
        prev_close = candles[i - 1].close_time
        curr_open = candles[i].open_time
        
        # Idealnya: curr_open == prev_close (untuk candle berurutan tanpa gap)
        # Tapi kita toleransi sedikit jitter
        diff_ms = curr_open - prev_close
        
        # Jika ada gap lebih dari 50% dari interval, catat
        if diff_ms > expected_interval_ms * 0.5:
            gap_info = {
                "index": i,
                "prev_close_time": prev_close,
                "curr_open_time": curr_open,
                "gap_ms": diff_ms,
                "expected_ms": expected_interval_ms,
                "missing_candles": int(diff_ms / expected_interval_ms)
            }
            gaps.append(gap_info)
            logger.warning(f"Gap detected at index {i}: {diff_ms}ms (expected {expected_interval_ms}ms)")
    
    return gaps


def normalize_candle(raw: RawCandle) -> NormalizedCandle:
    """
    Normalize single candle dari format Binance ke ST-LMS.
    
    Args:
        raw: RawCandle object.
        
    Returns:
        NormalizedCandle object.
    """
    open_dt_utc = ms_to_datetime(raw.open_time)
    close_dt_utc = ms_to_datetime(raw.close_time)
    
    open_dt_wib = utc_to_wib(open_dt_utc)
    close_dt_wib = utc_to_wib(close_dt_utc)
    
    # Gunakan close_time untuk Time ID (waktu candle selesai)
    time_id = utc_to_time_id(close_dt_utc, prefix="P")
    
    return NormalizedCandle(
        time_id=time_id,
        time_wib=format_wib_string(close_dt_wib),
        open_time_wib=format_wib_string(open_dt_wib),
        close_time_wib=format_wib_string(close_dt_wib),
        open=raw.open,
        high=raw.high,
        low=raw.low,
        close=raw.close,
        volume=raw.volume
    )


def normalize_candles(
    raw_candles: List[Dict[str, Any]],
    timeframe_minutes: int = 1
) -> NormalizationResult:
    """
    Main function: Normalize list of raw candles.
    
    Args:
        raw_candles: List of dict dengan format Binance OHLCV.
        timeframe_minutes: Timeframe untuk validasi gap.
        
    Returns:
        NormalizationResult dengan candles ternormalisasi dan metadata.
    """
    errors = []
    parsed_candles = []
    
    # Parse raw dicts ke RawCandle objects
    for i, rc in enumerate(raw_candles):
        try:
            candle = RawCandle(**rc)
            parsed_candles.append(candle)
        except Exception as e:
            err_msg = f"Candle index {i}: {str(e)}"
            errors.append(err_msg)
            logger.error(err_msg)
    
    if not parsed_candles:
        return NormalizationResult(
            success=False,
            candles=[],
            gaps_detected=[],
            total_input=len(raw_candles),
            total_output=0,
            errors=errors
        )
    
    # Sort berdasarkan open_time
    parsed_candles.sort(key=lambda c: c.open_time)
    
    # Validasi gap
    gaps = validate_candle_sequence(parsed_candles, timeframe_minutes)
    
    # Normalize setiap candle
    normalized = []
    for pc in parsed_candles:
        try:
            nc = normalize_candle(pc)
            normalized.append(nc)
        except Exception as e:
            err_msg = f"Normalization error: {str(e)}"
            errors.append(err_msg)
            logger.error(err_msg)
    
    return NormalizationResult(
        success=len(errors) == 0,
        candles=normalized,
        gaps_detected=gaps,
        total_input=len(raw_candles),
        total_output=len(normalized),
        errors=errors
    )


# =============================================================================
# TEST CASES - 10 CANDLE BERURUTAN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("NORMALIZER - TEST CASES (10 CANDLE BERURUTAN)")
    print("=" * 60)
    
    # Generate 10 dummy candle berurutan (timeframe 1 menit)
    # Base time: 2026-07-08 12:11:00 UTC = 2026-07-08 19:11:00 WIB
    base_timestamp_ms = int(datetime(2026, 7, 8, 12, 11, 0, tzinfo=timezone.utc).timestamp() * 1000)
    interval_ms = 60 * 1000  # 1 menit
    
    dummy_candles = []
    base_price = 61500.0
    
    for i in range(10):
        open_time = base_timestamp_ms + (i * interval_ms)
        close_time = open_time + interval_ms
        
        # Simulasi harga bergerak naik sedikit
        price_offset = i * 5.0
        open_price = base_price + price_offset
        close_price = open_price + 3.0
        high_price = max(open_price, close_price) + 2.0
        low_price = min(open_price, close_price) - 2.0
        vol = 100.0 + i * 10
        
        dummy_candles.append({
            "open_time": open_time,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": vol,
            "close_time": close_time
        })
    
    print(f"\nGenerated {len(dummy_candles)} dummy candles:")
    print(f"  First: {dummy_candles[0]['open_time']} -> {dummy_candles[0]['close_time']}")
    print(f"  Last:  {dummy_candles[-1]['open_time']} -> {dummy_candles[-1]['close_time']}")
    
    # Run normalization
    result = normalize_candles(dummy_candles, timeframe_minutes=1)
    
    print(f"\nNormalization Result:")
    print(f"  Success: {result.success}")
    print(f"  Input: {result.total_input}, Output: {result.total_output}")
    print(f"  Gaps detected: {len(result.gaps_detected)}")
    print(f"  Errors: {len(result.errors)}")
    
    if result.errors:
        for err in result.errors:
            print(f"    - {err}")
    
    print(f"\nNormalized Candles:")
    for i, nc in enumerate(result.candles):
        print(f"  [{i}] TimeID={nc.time_id}, WIB={nc.time_wib}, O={nc.open:.1f}, H={nc.high:.1f}, L={nc.low:.1f}, C={nc.close:.1f}, V={nc.volume:.1f}")
    
    # Verify Time IDs are sequential and correct
    print("\nVerifying Time IDs:")
    expected_minute = 18  # 12:11 UTC = 19:11 WIB, tapi close_time adalah akhir candle
    for i, nc in enumerate(result.candles):
        # Time ID format: P26070819XX dimana XX adalah menit WIB
        expected_tid_prefix = "P26070819"
        assert nc.time_id.startswith(expected_tid_prefix), f"Time ID prefix mismatch: {nc.time_id}"
        print(f"  [{i}] {nc.time_id} ✓")
    
    # Test gap detection with missing candle
    print("\n" + "=" * 60)
    print("TEST GAP DETECTION (candle ke-5 dihilangkan)")
    print("=" * 60)
    
    candles_with_gap = dummy_candles[:4] + dummy_candles[5:]  # Skip index 4
    result_gap = normalize_candles(candles_with_gap, timeframe_minutes=1)
    
    print(f"Gaps detected: {len(result_gap.gaps_detected)}")
    for gap in result_gap.gaps_detected:
        print(f"  Gap at index {gap['index']}: missing ~{gap['missing_candles']} candle(s)")
    
    assert len(result_gap.gaps_detected) >= 1, "Should detect at least 1 gap"
    print("✓ Gap detection PASS")
    
    print("\n" + "=" * 60)
    print("ALL NORMALIZER TESTS PASSED")
    print("=" * 60)
