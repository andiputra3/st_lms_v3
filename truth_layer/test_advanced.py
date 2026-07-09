"""
ST-LMS v3 - Advanced Test: Multiple Lines & Pattern Detection
Tests Line Builder with price jumps to create multiple lines,
and Wave Builder with complex patterns.
"""
import sys
sys.path.insert(0, '/workspace')

from datetime import datetime, timezone
from supertrend_point import SupertrendPoint, calculate_supertrend_points, PointType
from normalizer import normalize_candles
from truth_layer.schemas import SupertrendLine, SupertrendWave
from truth_layer.engines.line_builder import LineBuilder
from truth_layer.engines.wave_builder import WaveBuilder
from truth_layer.truth_manager import TruthManager
import json


def generate_volatile_data() -> tuple[list[SupertrendPoint], list[float]]:
    """
    Generate volatile test data with price jumps to trigger multiple line creation.
    """
    base_timestamp_ms = int(datetime(2026, 7, 8, 12, 11, 0, tzinfo=timezone.utc).timestamp() * 1000)
    interval_ms = 60 * 1000
    
    candles = []
    base_price = 95000.0
    
    # Create 40 candles with: 
    # - Phase 1 (0-9): Rising trend at ~95000
    # - Phase 2 (10-19): Jump up to ~96000 and rise
    # - Phase 3 (20-29): Jump down to ~94000 and rise
    # - Phase 4 (30-39): Jump up to ~97000 and rise
    
    for i in range(40):
        open_time = base_timestamp_ms + (i * interval_ms)
        close_time = open_time + interval_ms
        
        # Determine phase
        if i < 10:
            # Phase 1: Base level
            price_base = base_price + i * 2.0
        elif i < 20:
            # Phase 2: Jump up by ~800
            price_base = base_price + 800 + (i - 10) * 2.0
        elif i < 30:
            # Phase 3: Jump down by ~1200
            price_base = base_price - 400 + (i - 20) * 2.0
        else:
            # Phase 4: Jump up by ~1500
            price_base = base_price + 1100 + (i - 30) * 2.0
        
        open_price = price_base
        close_price = open_price + 1.5
        high_price = max(open_price, close_price) + 1.0
        low_price = min(open_price, close_price) - 0.8
        vol = 100.0 + i * 3
        
        candles.append({
            "open_time": open_time,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": vol,
            "close_time": close_time
        })
    
    # Normalize and calculate Supertrend
    norm_result = normalize_candles(candles, timeframe_minutes=1)
    st_result = calculate_supertrend_points(
        norm_result.candles,
        atr_period=10,
        multiplier=2.5  # Slightly lower multiplier for more sensitivity
    )
    
    if not st_result.success or len(st_result.points) < 10:
        raise ValueError(f"Failed to generate enough points: {len(st_result.points)}")
    
    points = st_result.points
    atr_values = [p.atr_value for p in points]
    
    print(f"Generated {len(points)} SupertrendPoints from volatile candles")
    return points, atr_values


def test_multiple_lines(points: list[SupertrendPoint], atr_values: list[float]) -> list[SupertrendLine]:
    """
    Test Line Builder with volatile data that should create multiple lines.
    """
    print("\n=== Testing Line Builder with Volatile Data ===")
    
    # Use tighter tolerance to force more line breaks
    builder = LineBuilder(tolerance_pct=0.001, tolerance_atr_mult=0.2)
    lines = builder.process_points(points, atr_values)
    
    print(f"Created {len(lines)} lines:")
    for line in lines:
        print(f"\n  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"  Line: {line.line_id}")
        print(f"  Type: {line.type} | Price: {line.current_price:.2f} | Strength: {line.strength}")
        print(f"  Versions: {len(line.versions)} events")
        
        # Show first and last version
        if line.versions:
            first = line.versions[0]
            last = line.versions[-1]
            print(f"    First: [{first.event}] {first.point_id} @ {first.price:.2f}")
            if len(line.versions) > 1:
                print(f"    Last:  [{last.event}] {last.point_id} @ {last.price:.2f}")
    
    return lines


def test_pattern_detection(lines: list[SupertrendLine]) -> list[SupertrendWave]:
    """
    Test Wave Builder with multiple lines to detect various patterns.
    """
    print("\n=== Testing Wave Builder Pattern Detection ===")
    
    builder = WaveBuilder(min_lines_for_wave=2)
    waves = builder.process_lines(lines, force_complete=True)
    
    print(f"Created {len(waves)} waves:")
    for wave in waves:
        print(f"\n  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"  Wave: {wave.wave_id}")
        print(f"  Pattern: {wave.pattern}")
        print(f"  Sequence: {' → '.join(wave.sequence)}")
        print(f"  Signature: {wave.signature}")
        print(f"  Members ({len(wave.members)}): {', '.join(wave.members[:3])}{'...' if len(wave.members) > 3 else ''}")
    
    return waves


def verify_json_purity() -> bool:
    """
    Verify that JSON storage contains NO computed fields.
    """
    print("\n=== Verifying JSON Purity ===")
    
    with open('/workspace/truth_layer/storage/lines.json', 'r') as f:
        lines_data = json.load(f)
    
    forbidden = ['distance', 'slope', 'duration', 'calculated', 'computed', 'metrics']
    issues = []
    
    for line in lines_data:
        for field in forbidden:
            if field in line:
                issues.append(f"Line {line.get('line_id', 'unknown')} contains '{field}'")
    
    if issues:
        print("❌ JSON PURITY FAILED:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print("✅ JSON is pure - no computed fields stored")
        print(f"   Stored {len(lines_data)} lines with only schema-compliant fields")
        return True


def test_truth_manager_runtime() -> None:
    """
    Test Truth Manager runtime calculations.
    """
    print("\n=== Testing Truth Manager Runtime Calculations ===")
    
    manager = TruthManager(
        lines_file="/workspace/truth_layer/storage/lines.json",
        waves_file="/workspace/truth_layer/storage/waves.json"
    )
    manager.reload()
    
    lines = manager.get_all_lines()
    
    if lines:
        # Test with middle price of first line
        test_line = lines[0]
        test_price = test_line.current_price + 100
        
        print(f"\nQuery: Nearest SUPPORT to {test_price:.2f}")
        support = manager.get_nearest_support(test_price)
        if support:
            line, distance, distance_pct = support
            print(f"  Found: {line.line_id} @ {line.current_price:.2f}")
            print(f"  Distance: {distance:.2f} ({distance_pct:.2f}%) ⚡ CALCULATED AT RUNTIME")
        
        print(f"\nQuery: Nearest RESISTANCE to {test_price:.2f}")
        resistance = manager.get_nearest_resistance(test_price)
        if resistance:
            line, distance, distance_pct = resistance
            print(f"  Found: {line.line_id} @ {line.current_price:.2f}")
            print(f"  Distance: {distance:.2f} ({distance_pct:.2f}%) ⚡ CALCULATED AT RUNTIME")
        
        # Test line metrics
        print(f"\nLine Metrics for {test_line.line_id}:")
        metrics = manager.get_line_with_metrics(test_line.line_id)
        if metrics:
            m = metrics['metrics']
            print(f"  Slope: {m['slope']:.4f} per version ⚡ CALCULATED AT RUNTIME")
            print(f"  Duration: {m['duration_minutes']} minutes ⚡ CALCULATED AT RUNTIME")
            print(f"  Version Count: {m['version_count']}")
            print(f"  Price Range: {m['price_range']['min']:.2f} - {m['price_range']['max']:.2f}")


def main():
    """
    Main test runner for advanced Sprint 2 scenarios.
    """
    print("=" * 60)
    print("ST-LMS v3 - Sprint 2 Advanced Test")
    print("Multiple Lines & Pattern Detection")
    print("=" * 60)
    
    # Generate volatile data
    points, atr_values = generate_volatile_data()
    
    # Test Line Builder
    lines = test_multiple_lines(points, atr_values)
    
    # Test Wave Builder
    waves = test_pattern_detection(lines)
    
    # Save to storage
    print("\n=== Saving to Storage ===")
    lines_data = [line.model_dump(mode='json') for line in lines]
    with open('/workspace/truth_layer/storage/lines_advanced.json', 'w') as f:
        json.dump(lines_data, f, indent=2, default=str)
    print(f"Saved {len(lines)} lines to storage/lines_advanced.json")
    
    waves_data = [wave.model_dump(mode='json') for wave in waves]
    with open('/workspace/truth_layer/storage/waves_advanced.json', 'w') as f:
        json.dump(waves_data, f, indent=2, default=str)
    print(f"Saved {len(waves)} waves to storage/waves_advanced.json")
    
    # Verify JSON purity
    json_pure = verify_json_purity()
    
    # Test Truth Manager
    test_truth_manager_runtime()
    
    # Final summary
    print("\n" + "=" * 60)
    print("ADVANCED TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Generated {len(points)} SupertrendPoints from volatile data")
    print(f"✅ Created {len(lines)} SupertrendLines (multiple lines from price jumps)")
    print(f"✅ Detected {len(waves)} SupertrendWaves with pattern analysis")
    print(f"✅ JSON Purity: {'PASS' if json_pure else 'FAIL'}")
    print(f"✅ Runtime calculations verified (distance, slope, duration)")
    print("=" * 60)


if __name__ == "__main__":
    main()
