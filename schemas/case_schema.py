"""Schema untuk TradingCase - Closed Feedback Loop"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class TradingCase(BaseModel):
    """
    TradingCase: Bungkus lengkap dari satu siklus trading.
    Digunakan untuk menyimpan hasil trade ke Data Lake agar bisa dipelajari oleh Academy/Darwin.
    """
    case_id: str = Field(..., description="Unique ID for this trading case")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Informasi Worker & Strategi
    worker_name: str
    symbol: str
    direction: str  # LONG/SHORT
    
    # Detail Entry & Exit
    entry_price: float
    exit_price: float
    pnl_usd: float
    outcome: str  # WIN/LOSS
    
    # Konteks Market
    market_regime: str  # UPTREND_LADDER, DOWNTREND_LADDER, SIDEWAY, dll.
    exit_reason: str
    
    # Evidence dari RAG saat entry
    evidence_summary: List[Dict[str, Any]]
    proposal_confidence: float
    
    # Snapshot Truth Layer saat trade
    truth_layer_snapshot: Dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "case_id": "case_20240101_120000_pos_123",
                "timestamp": "2024-01-01T12:05:00",
                "worker_name": "PullbackWorker_v1",
                "symbol": "BTCUSDT",
                "direction": "LONG",
                "entry_price": 50000.0,
                "exit_price": 51500.0,
                "pnl_usd": 150.0,
                "outcome": "WIN",
                "market_regime": "UPTREND_LADDER",
                "exit_reason": "Take Profit hit",
                "evidence_summary": [
                    {"source": "LineRAG", "fact": "Strong Support at 49800", "confidence": 0.9}
                ],
                "proposal_confidence": 0.85,
                "truth_layer_snapshot": {
                    "points_count": 50,
                    "lines_count": 5,
                    "wave_context": "UPTREND_LADDER"
                }
            }
        }
