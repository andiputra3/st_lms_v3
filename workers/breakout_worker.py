"""
BREAKOUT WORKER
Strategi: ENTRY LONG jika Wave sebelumnya COMPRESSION dan harga menembus Resistance.
"""
from typing import List, Optional
from schemas.proposal_schema import Proposal, Evidence

class BreakoutWorker:
    """
    Worker yang mencari breakout dari konsolidasi.
    LOGIKA DUMMY UNTUK SPRINT 11:
    - Jika ada Resistance Line terdekat dan harga > resistance -> ENTRY LONG
    - Jika ada Support Line terdekat dan harga < support -> ENTRY SHORT
    - Selain itu -> WAIT
    """
    
    def __init__(self, dna: Optional[dict] = None):
        self.name = "BreakoutWorker_v1"
        self.dna = dna or {"breakout_threshold": 0.02} # 2% di atas resistance
        self.local_memory: dict = {}

    def analyze(self, current_price: float, time_id: str, rag) -> Proposal:
        """
        Menganalisis market menggunakan RAG.
        Hanya membaca dari RAG (Read-Only).
        """
        # Query RAG untuk Line (Support/Resistance)
        line_cards = rag.get_facts_by_type("LINE")
        
        if not line_cards:
            return Proposal(
                worker_name=self.name,
                type="WAIT",
                symbol="UNKNOWN",
                direction="NEUTRAL",
                confidence=0.0,
                evidence=[],
                reason="No line context available in RAG."
            )
        
        # Cari resistance terdekat di bawah harga saat ini (untuk breakout long)
        # Atau support terdekat di atas harga saat ini (untuk breakdown short)
        # Simplifikasi: ambil line terakhir sebagai acuan
        latest_line = line_cards[-1]
        
        # Parse dummy fact: "Strong Resistance at 95000.00"
        fact_text = latest_line.fact
        is_resistance = "Resistance" in fact_text
        is_support = "Support" in fact_text
        
        # Extract price from fact string (dummy parsing)
        try:
            price_str = [s for s in fact_text.split() if s.replace('.', '').isdigit()][0]
            line_price = float(price_str)
        except:
            line_price = current_price * 0.98 # Fallback
            
        evidence = [latest_line]
        
        threshold = self.dna.get("breakout_threshold", 0.02)
        
        # Logika Breakout Long
        if is_resistance and current_price > line_price:
            breakout_strength = (current_price - line_price) / line_price
            if breakout_strength > 0: # Sedikit di atas resistance
                return Proposal(
                    worker_name=self.name,
                    type="ENTRY",
                    symbol="BTCUSDT",
                    direction="LONG",
                    confidence=0.75 + min(breakout_strength, 0.2), # Max 0.95
                    evidence=evidence,
                    reason=f"Breakout detected! Price {current_price} broke Resistance at {line_price}. Strength: {breakout_strength:.2%}"
                )
        
        # Logika Breakdown Short
        if is_support and current_price < line_price:
            breakdown_strength = (line_price - current_price) / line_price
            if breakdown_strength > 0:
                return Proposal(
                    worker_name=self.name,
                    type="ENTRY",
                    symbol="BTCUSDT",
                    direction="SHORT",
                    confidence=0.75 + min(breakdown_strength, 0.2),
                    evidence=evidence,
                    reason=f"Breakdown detected! Price {current_price} broke Support at {line_price}. Strength: {breakdown_strength:.2%}"
                )
        
        return Proposal(
            worker_name=self.name,
            type="WAIT",
            symbol="BTCUSDT",
            direction="NEUTRAL",
            confidence=0.3,
            evidence=evidence,
            reason=f"No clear breakout. Price {current_price} vs Line {line_price}."
        )
