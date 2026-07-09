from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime


class ExecutionIntent(BaseModel):
    """
    Objek akhir dari Pipeline Decision Making.
    Ini BUKAN order eksekusi, melainkan 'niat' yang akan diproses oleh Executor Module di masa depan.
    
    GUARDRAIL: Kelas ini hanya sebagai struktur data. Tidak memiliki method untuk eksekusi order.
    """
    intent_id: str = Field(..., description="Unique ID for this execution intent")
    symbol: str
    direction: Literal["LONG", "SHORT"]
    size_usd: float = Field(..., gt=0, description="Alokasi modal dalam USD")
    leverage: int = Field(default=1, ge=1, le=125)
    
    # Metadata Sumber
    worker_name: str
    proposal_confidence: float = Field(..., ge=0.0, le=1.0)
    
    # Mode Eksekusi
    mode: Literal["LIVE", "REPLAY"] = Field(
        default="REPLAY", 
        description="LIVE untuk eksekusi nyata, REPLAY untuk shadow trading/backtest"
    )
    
    reason: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "intent_id": "exec_12345",
                "symbol": "BTCUSDT",
                "direction": "LONG",
                "size_usd": 10.0,
                "leverage": 5,
                "worker_name": "PullbackWorker_v1",
                "proposal_confidence": 0.92,
                "mode": "LIVE",
                "reason": "High confidence pullback strategy selected."
            }
        }
