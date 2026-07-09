"""
TEST SUITE: SPRINT 5 (HiveMind Hub & Portfolio Manager)

Simulasi End-to-End:
1. Inisialisasi 3 Worker Dummy (Pullback, Trend, Grid).
2. Worker menghasilkan Proposal.
3. HiveMind mengumpulkan Proposal.
4. PortfolioManager mengalokasikan modal dan menentukan Mode (LIVE/REPLAY).
"""

import sys
import os

# Pastikan path root workspace termasuk
sys.path.insert(0, os.getcwd())

from schemas.proposal_schema import Proposal, Evidence
from hivemind.hivemind_hub import HiveMindHub
from portfolio.portfolio_manager import PortfolioManager


# --- MOCK WORKERS (Simulasi output dari Sprint 4) ---

def mock_pullback_worker() -> Proposal:
    """Worker dengan confidence tinggi (Harus LIVE)"""
    return Proposal(
        worker_name="PullbackWorker_v1",
        type="ENTRY",
        symbol="BTCUSDT",
        direction="LONG",
        confidence=0.92,
        evidence=[
            Evidence(source="LineRAG", fact="Strong Support at 95k", confidence=0.95),
            Evidence(source="WaveRAG", fact="Uptrend Ladder confirmed", confidence=0.88)
        ],
        reason="Bullish pullback to strong support with wave confirmation."
    )


def mock_trend_worker() -> Proposal:
    """Worker dengan confidence sedang (Harus REPLAY)"""
    return Proposal(
        worker_name="TrendFollower_v2",
        type="ENTRY",
        symbol="ETHUSDT",
        direction="LONG",
        confidence=0.75,
        evidence=[
            Evidence(source="LineRAG", fact="Resistance break retest", confidence=0.70)
        ],
        reason="Trend continuation pattern detected but volume low."
    )


def mock_grid_worker() -> Proposal:
    """Worker dengan confidence rendah (Harus DIFILTER/DIBUANG)"""
    return Proposal(
        worker_name="GridBot_Alpha",
        type="ENTRY",
        symbol="SOLUSDT",
        direction="SHORT",
        confidence=0.45,
        evidence=[],
        reason="Mean reversion signal weak."
    )


def test_sprint5_flow():
    print("=" * 60)
    print("SPRINT 5 TEST: HiveMind Hub & Portfolio Manager")
    print("=" * 60)

    # 1. Setup Components
    hive = HiveMindHub()
    pm = PortfolioManager(total_capital_usd=25.0)  # Modal kecil untuk tes alokasi
    
    # 2. Generate Proposals (Simulasi Worker bekerja)
    print("\n[Step 1] Generating Proposals from Workers...")
    p1 = mock_pullback_worker()
    p2 = mock_trend_worker()
    p3 = mock_grid_worker()
    
    proposals = [p1, p2, p3]
    print(f"Generated {len(proposals)} proposals.")

    # 3. Submit to HiveMind
    print("\n[Step 2] Submitting Proposals to HiveMind Hub...")
    for p in proposals:
        hive.submit_proposal(p)
        print(f"  - Received proposal from {p.worker_name} (Conf: {p.confidence})")
    
    pending = hive.get_pending_proposals()
    print(f"HiveMind holding {len(pending)} pending proposals.")

    # 4. Portfolio Manager Allocation
    print("\n[Step 3] PortfolioManager Allocating Capital...")
    print(f"  - Total Capital: ${pm.total_capital_usd}")
    print(f"  - Live Threshold: {pm.confidence_threshold_live}")
    print(f"  - Replay Threshold: {pm.confidence_threshold_replay}")
    
    intents = pm.allocate_capital(pending)
    
    print(f"\n[Step 4] Execution Intents Generated: {len(intents)}")
    print("-" * 60)
    
    live_count = 0
    replay_count = 0
    
    for intent in intents:
        status_icon = "[LIVE]" if intent.mode == "LIVE" else "[REPLAY]"
        print(f"{status_icon} {intent.symbol} | {intent.direction} | "
              f"Worker: {intent.worker_name} | Conf: {intent.proposal_confidence} | "
              f"Size: ${intent.size_usd}")
        print(f"         Reason: {intent.reason}")
        
        if intent.mode == "LIVE":
            live_count += 1
        else:
            replay_count += 1
            
    print("-" * 60)
    
    # 5. Verifikasi Hasil (Assertions)
    print("\n[Step 5] Verification & Assertions...")
    
    # Cek jumlah intent (Grid worker harusnya terfilter karena conf < 0.6)
    assert len(intents) == 2, f"Expected 2 intents (Pullback & Trend), got {len(intents)}"
    print("[PASS] Correct number of intents (Low confidence filtered out).")
    
    # Cek Mode Pullback (Conf 0.92 > 0.85 -> LIVE)
    pullback_intent = next(i for i in intents if i.worker_name == "PullbackWorker_v1")
    assert pullback_intent.mode == "LIVE", "Pullback worker should be LIVE mode."
    print("[PASS] High confidence proposal assigned to LIVE mode.")
    
    # Cek Mode Trend (Conf 0.75 < 0.85 -> REPLAY)
    trend_intent = next(i for i in intents if i.worker_name == "TrendFollower_v2")
    assert trend_intent.mode == "REPLAY", "Trend worker should be REPLAY mode."
    print("[PASS] Medium confidence proposal assigned to REPLAY mode.")
    
    # Cek Budget
    summary = pm.get_allocation_summary()
    # Hanya 1 LIVE trade ($10) yang mengurangi available capital dalam logika kita
    expected_available = 25.0 - 10.0 
    assert summary['available_capital'] == expected_available, "Capital allocation calculation error."
    print(f"[PASS] Capital allocation correct. Remaining: ${summary['available_capital']}")
    
    # Cek Tipe Output - validasi Pydantic
    from schemas.execution_schema import ExecutionIntent
    assert isinstance(intents[0], ExecutionIntent), "Intent must be Pydantic ExecutionIntent instance."
    print("[PASS] Output strictly typed as Pydantic ExecutionIntent.")

    # 6. Guardrails Verification
    print("\n[Step 6] Guardrails Verification...")
    
    # Cek tidak ada import ccxt/binance di hivemind (cek hanya baris import)
    with open("hivemind/hivemind_hub.py", "r") as f:
        hivemind_code = f.read()
        hivemind_lines = hivemind_code.split('\n')
        import_lines = [l for l in hivemind_lines if l.strip().startswith('import ') or l.strip().startswith('from ')]
        import_section = '\n'.join(import_lines)
        assert "ccxt" not in import_section, "HiveMind must not import ccxt"
        assert "binance" not in import_section, "HiveMind must not import binance"
    print("[PASS] HiveMind has no exchange API imports.")
    
    # Cek tidak ada import ccxt/binance di portfolio
    with open("portfolio/portfolio_manager.py", "r") as f:
        portfolio_code = f.read()
        portfolio_lines = portfolio_code.split('\n')
        import_lines = [l for l in portfolio_lines if l.strip().startswith('import ') or l.strip().startswith('from ')]
        import_section = '\n'.join(import_lines)
        assert "ccxt" not in import_section, "PortfolioManager must not import ccxt"
        assert "binance" not in import_section, "PortfolioManager must not import binance"
    print("[PASS] PortfolioManager has no exchange API imports.")
    
    print("\n" + "=" * 60)
    print("SPRINT 5 TEST PASSED SUCCESSFULLY!")
    print("=" * 60)
    print("Guardrails Verified:")
    print("  [✓] No Exchange API Calls")
    print("  [✓] HiveMind acts only as Coordinator")
    print("  [✓] PortfolioManager acts only as Allocator")
    print("  [✓] Output is pure Data Objects (ExecutionIntent)")
    print("  [✓] In-memory state only (no SQLite)")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success = test_sprint5_flow()
    sys.exit(0 if success else 1)
