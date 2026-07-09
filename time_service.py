"""
Time Service - Global service untuk konversi UTC ke WIB dan generate Time ID.

Format Time ID: [Prefix][YY][MM][DD][HH][mm]
Contoh: P2607081920 (Point, Tahun 2026, Bulan 07, Tgl 08, Jam 19, Menit 20 WIB)

Guardrails:
- Semua waktu WAJIB menggunakan WIB.
- Time ID unik untuk memudahkan audit dan replay.
"""

from datetime import datetime, timedelta, timezone
from typing import Literal
import pytz


# Constants
WIB_TZ = pytz.timezone("Asia/Jakarta")
UTC_TZ = pytz.UTC

# Prefix untuk Time ID
PREFIX_POINT = "P"
PREFIX_LINE = "L"
PREFIX_WAVE = "W"


def utc_to_wib(utc_dt: datetime) -> datetime:
    """
    Mengkonversi datetime UTC ke WIB.
    
    Args:
        utc_dt: datetime dalam timezone UTC (timezone-aware).
        
    Returns:
        datetime dalam timezone WIB.
        
    Raises:
        ValueError: Jika input tidak timezone-aware atau bukan UTC.
    """
    if utc_dt.tzinfo is None:
        raise ValueError("Input datetime harus timezone-aware (UTC).")
    
    # Normalize ke UTC dulu jika perlu
    utc_dt_normalized = utc_dt.astimezone(UTC_TZ)
    
    # Konversi ke WIB
    wib_dt = utc_dt_normalized.astimezone(WIB_TZ)
    
    return wib_dt


def generate_time_id(
    wib_dt: datetime,
    prefix: Literal["P", "L", "W"] = "P"
) -> str:
    """
    Generate Time ID dari datetime WIB.
    
    Format: [Prefix][YY][MM][DD][HH][mm]
    Contoh: P2607081920
    
    Args:
        wib_dt: datetime dalam timezone WIB.
        prefix: Prefix tipe objek ("P"=Point, "L"=Line, "W"=Wave).
        
    Returns:
        String Time ID.
        
    Raises:
        ValueError: Jika datetime bukan WIB atau prefix tidak valid.
    """
    if wib_dt.tzinfo is None:
        raise ValueError("Input datetime harus timezone-aware.")
    
    # Pastikan dalam WIB
    wib_normalized = wib_dt.astimezone(WIB_TZ)
    
    if prefix not in ("P", "L", "W"):
        raise ValueError(f"Prefix harus 'P', 'L', atau 'W', got: {prefix}")
    
    yy = wib_normalized.year % 100
    mm = wib_normalized.month
    dd = wib_normalized.day
    hh = wib_normalized.hour
    mi = wib_normalized.minute
    
    time_id = f"{prefix}{yy:02d}{mm:02d}{dd:02d}{hh:02d}{mi:02d}"
    
    return time_id


def utc_to_time_id(utc_dt: datetime, prefix: Literal["P", "L", "W"] = "P") -> str:
    """
    Convenience function: Langsung konversi UTC ke Time ID.
    
    Args:
        utc_dt: datetime dalam timezone UTC.
        prefix: Prefix tipe objek.
        
    Returns:
        String Time ID.
    """
    wib_dt = utc_to_wib(utc_dt)
    return generate_time_id(wib_dt, prefix)


def format_wib_string(wib_dt: datetime) -> str:
    """
    Format datetime WIB ke string standar: "YYYY-MM-DD HH:MM:SS".
    
    Args:
        wib_dt: datetime dalam timezone WIB.
        
    Returns:
        Formatted string.
    """
    wib_normalized = wib_dt.astimezone(WIB_TZ)
    return wib_normalized.strftime("%Y-%m-%d %H:%M:%S")


def get_current_time_id(prefix: Literal["P", "L", "W"] = "P") -> str:
    """
    Get current time ID based on current WIB time.
    
    Args:
        prefix: Prefix tipe objek ("P"=Point, "L"=Line, "W"=Wave).
        
    Returns:
        String Time ID untuk waktu sekarang.
    """
    now_wib = datetime.now(WIB_TZ)
    return generate_time_id(now_wib, prefix=prefix)


def add_minutes_to_time_id(time_id: str, minutes: int) -> str:
    """
    Add minutes to a given Time ID and return new Time ID.
    
    Args:
        time_id: Original Time ID (e.g., "P2607081920").
        minutes: Minutes to add (can be negative).
        
    Returns:
        New Time ID after adding minutes.
    """
    # Parse time_id: P2607081920 -> prefix=P, year=26, month=07, day=08, hour=19, min=20
    if len(time_id) < 13:
        raise ValueError(f"Invalid time_id format: {time_id}")
    
    prefix = time_id[0]
    yy = int(time_id[1:3])
    mm = int(time_id[3:5])
    dd = int(time_id[5:7])
    hh = int(time_id[7:9])
    mi = int(time_id[9:11])
    
    # Determine century for year
    year = 2000 + yy if yy < 50 else 1900 + yy
    
    # Create datetime in WIB
    dt = datetime(year, mm, dd, hh, mi, 0, tzinfo=WIB_TZ)
    
    # Add minutes
    new_dt = dt + timedelta(minutes=minutes)
    
    # Generate new time_id
    return generate_time_id(new_dt, prefix=prefix)


# =============================================================================
# TEST CASES
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("TIME SERVICE - TEST CASES")
    print("=" * 60)
    
    # Test 1: Konversi UTC ke WIB
    utc_sample = datetime(2026, 7, 8, 12, 20, 0, tzinfo=UTC_TZ)
    wib_result = utc_to_wib(utc_sample)
    print(f"\nTest 1 - UTC to WIB:")
    print(f"  Input UTC : {utc_sample}")
    print(f"  Output WIB: {wib_result}")
    assert wib_result.hour == 19, "WIB harus UTC+7"
    print("  ✓ PASS")
    
    # Test 2: Generate Time ID
    time_id = generate_time_id(wib_result, prefix="P")
    print(f"\nTest 2 - Generate Time ID:")
    print(f"  Input WIB : {wib_result}")
    print(f"  Output ID : {time_id}")
    assert time_id == "P2607081920", f"Expected P2607081920, got {time_id}"
    print("  ✓ PASS")
    
    # Test 3: Direct UTC to Time ID
    time_id_direct = utc_to_time_id(utc_sample, prefix="P")
    print(f"\nTest 3 - Direct UTC to Time ID:")
    print(f"  Input UTC : {utc_sample}")
    print(f"  Output ID : {time_id_direct}")
    assert time_id_direct == "P2607081920"
    print("  ✓ PASS")
    
    # Test 4: Format WIB String
    wib_str = format_wib_string(wib_result)
    print(f"\nTest 4 - Format WIB String:")
    print(f"  Output: {wib_str}")
    assert wib_str == "2026-07-08 19:20:00"
    print("  ✓ PASS")
    
    # Test 5: Different prefixes
    for pf in ["P", "L", "W"]:
        tid = generate_time_id(wib_result, prefix=pf)
        assert tid.startswith(pf)
    print(f"\nTest 5 - Different Prefixes: ✓ PASS")
    
    # Test 6: Error handling - naive datetime
    try:
        naive_dt = datetime(2026, 7, 8, 12, 20, 0)
        utc_to_wib(naive_dt)
        print("\nTest 6 - Naive datetime rejection: ✗ FAIL (should raise)")
    except ValueError as e:
        print(f"\nTest 6 - Naive datetime rejection: ✓ PASS ({e})")
    
    print("\n" + "=" * 60)
    print("ALL TIME SERVICE TESTS PASSED")
    print("=" * 60)


def timestamp_to_time_id(timestamp_unix: int, prefix: Literal["P", "L", "W"] = "P") -> str:
    """
    Convert Unix timestamp (seconds) to Time ID.
    
    Args:
        timestamp_unix: Unix timestamp in seconds (UTC).
        prefix: Prefix untuk Time ID.
        
    Returns:
        Time ID string.
    """
    utc_dt = datetime.fromtimestamp(timestamp_unix, tz=UTC_TZ)
    return utc_to_time_id(utc_dt, prefix=prefix)


def utc_to_wib_timestamp(timestamp_ms: int) -> int:
    """
    Convert UTC timestamp (ms) to WIB timestamp (ms).
    
    Args:
        timestamp_ms: Timestamp in milliseconds (UTC).
        
    Returns:
        Timestamp in milliseconds (WIB).
    """
    # WIB is UTC+7, so add 7 hours in milliseconds
    return timestamp_ms + (7 * 60 * 60 * 1000)
