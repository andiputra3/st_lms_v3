"""
TREND FOLLOWING WORKER
Strategi: ENTRY LONG jika Wave = UPTREND_LADDER dan momentum mendukung.
"""
from typing import List, Optional
from schemas.proposal_schema import Proposal, Evidence

class TrendFollowingWorker:
    """
    Worker yang mengikuti trend.
    LOGIKA DUMMY UNTUK SPRINT 11:
    - Jika Wave Context adalah UPTREND_LADDER -> ENTRY LONG
    - Jika Wave Context adalah DOWNTREND_LADDER -> ENTRY SHORT
    - Selain itu -> WAIT
    """
    
    def __init__(self, dna: Optional[dict] = None):
        self.name = "TrendFollowingWorker_v1"
        self.dna = dna or {"min_confidence": 0.7}
        self.local_memory: dict = {}

    def analyze(self, current_price: float, time_id: str, rag) -> Proposal:
        """
        Menganalisis market menggunakan RAG.
        Hanya membaca dari RAG (Read-Only).
        """
        # Query RAG untuk Wave Context
        wave_cards = rag.get_facts_by_type("WAVE")
        
        if not wave_cards:
            return Proposal(
                worker_name=self.name,
                type="WAIT",
                symbol="UNKNOWN",
                direction="NEUTRAL",
                confidence=0.0,
                evidence=[],
                reason="No wave context available in RAG."
            )
        
        # Ambil wave terbaru
        latest_wave = wave_cards[-1]
        wave_type = latest_wave.fact.split(":")[1].strip() if ":" in latest_wave.fact else ""
        
        evidence = [latest_wave]
        
        # Logika sederhana
        if "UPTREND_LADDER" in wave_type:
            return Proposal(
                worker_name=self.name,
                type="ENTRY",
                symbol="BTCUSDT", # Akan di-set oleh orchestrator nanti
                direction="LONG",
                confidence=0.85,
                evidence=evidence,
                reason=f"Trend following: Detected {wave_type}. Entering LONG position."
            )
        elif "DOWNTREND_LADDER" in wave_type:
            return Proposal(
                worker_name=self.name,
                type="ENTRY",
                symbol="BTCUSDT",
                direction="SHORT",
                confidence=0.85,
                evidence=evidence,
                reason=f"Trend following: Detected {wave_type}. Entering SHORT position."
            )
        else:
            return Proposal(
                worker_name=self.name,
                type="WAIT",
                symbol="BTCUSDT",
                direction="NEUTRAL",
                confidence=0.3,
                evidence=evidence,
                reason=f"Trend unclear: Current wave is {wave_type}. Waiting."
            )
