"""
Portfolio Manager - Allocator Layer untuk Trading System

Tanggung Jawab:
1. Filtering: Menyaring Proposal berdasarkan confidence threshold.
2. Risk Management: Mengalokasikan modal terbatas ke strategi terbaik.
3. Routing: Menentukan mode eksekusi (LIVE vs REPLAY).

GUARDRAILS:
- DILARANG memanggil API Exchange.
- Output HANYA berupa list ExecutionIntent.
- Menggunakan in-memory state untuk budget tracking.
"""

import uuid
from typing import List
from datetime import datetime

from schemas.proposal_schema import Proposal
from schemas.execution_schema import ExecutionIntent


class PortfolioManager:
    """
    PORTFOLIO MANAGER (Allocator Layer)
    
    Bertanggung jawab mengalokasikan modal ke proposal terbaik
    dan menentukan apakah trade harus LIVE atau REPLAY.
    """

    def __init__(self, total_capital_usd: float, max_risk_per_trade_pct: float = 0.1):
        self.total_capital_usd = total_capital_usd
        self.available_capital_usd = total_capital_usd
        self.max_risk_per_trade_pct = max_risk_per_trade_pct
        self.confidence_threshold_live = 0.85  # Threshold untuk LIVE trading
        self.confidence_threshold_replay = 0.60  # Threshold minimal untuk REPLAY
        
        # Audit Log internal
        self._intent_history: List[ExecutionIntent] = []

    def allocate_capital(self, proposals: List[Proposal]) -> List[ExecutionIntent]:
        """
        Proses utama: Filter, Rank, Allocate, dan Generate Intent.
        """
        intents = []
        
        # 1. Filtering Dasar - hanya ENTRY dan confidence di atas threshold minimal
        qualified_proposals = [
            p for p in proposals 
            if p.confidence >= self.confidence_threshold_replay and p.type == "ENTRY"
        ]
        
        # 2. Sorting berdasarkan Confidence (Highest first)
        qualified_proposals.sort(key=lambda x: x.confidence, reverse=True)
        
        # 3. Alokasi Modal
        # Strategi sederhana: fixed size per trade untuk simulasi
        fixed_trade_size = 10.0  # $10 per trade
        
        for proposal in qualified_proposals:
            if self.available_capital_usd < fixed_trade_size:
                # Modal habis, skip
                continue
            
            # Tentukan Mode berdasarkan confidence
            if proposal.confidence >= self.confidence_threshold_live:
                mode = "LIVE"
            else:
                mode = "REPLAY"
            
            # Buat ExecutionIntent
            intent = ExecutionIntent(
                intent_id=str(uuid.uuid4()),
                symbol=proposal.symbol,
                direction=proposal.direction,
                size_usd=fixed_trade_size,
                leverage=5,  # Default leverage konservatif
                worker_name=proposal.worker_name,
                proposal_confidence=proposal.confidence,
                mode=mode,
                reason=f"Allocated by PortfolioManager. Strategy: {proposal.reason[:50]}..."
            )
            
            intents.append(intent)
            self._intent_history.append(intent)
            
            # Kurangi modal tersedia hanya untuk LIVE trade
            # REPLAY tidak mengunci modal nyata
            if mode == "LIVE":
                self.available_capital_usd -= fixed_trade_size

        return intents

    def get_allocation_summary(self) -> dict:
        """Ringkasan alokasi modal saat ini."""
        return {
            "total_capital": self.total_capital_usd,
            "available_capital": self.available_capital_usd,
            "allocated_capital": self.total_capital_usd - self.available_capital_usd,
            "intents_generated": len(self._intent_history)
        }

    # =====================================================================
    # AUDIT CHECKLIST: PortfolioManager
    # =====================================================================
    # [✓] Tidak ada panggilan ke exchange.buy() atau exchange.sell().
    # [✓] Output adalah list objek Pydantic ExecutionIntent, bukan boolean atau void.
    # [✓] State management (available_capital) menggunakan variable lokal, bukan DB.
    # [✓] Logika bisnis murni alokasi resource, tidak memprediksi harga.
    # [✓] Tidak ada import ccxt, binance, atau library networking.
    # =====================================================================
