"""
ST-LMS v3 - Proposal Schema Definitions
Pydantic models for Evidence and Proposal objects.
Workers output ONLY Proposal objects - no direct trading execution.
"""
import uuid
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class Evidence(BaseModel):
    """
    Evidence item from RAG (FactCard) supporting a proposal.
    This is a lightweight reference to RAG findings.
    """
    source: str = Field(..., description="Source of evidence (e.g., LineRAG, WaveRAG)")
    fact: str = Field(..., description="The factual finding from RAG")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of this evidence")
    
    class Config:
        json_schema_extra = {
            "example": {
                "source": "WaveRAG",
                "fact": "UPTREND_LADDER structure (Bullish), 3 lines",
                "confidence": 0.85
            }
        }


class Proposal(BaseModel):
    """
    Standardized proposal output from any Worker.
    Workers NEVER execute trades - they only propose actions.
    
    Guardrails:
    - type must be ENTRY, EXIT, or WAIT
    - direction must be LONG, SHORT, or NEUTRAL
    - confidence must be between 0.0 and 1.0
    - evidence must be list of FactCard-derived objects
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for this proposal")
    worker_name: str = Field(..., description="Name of the worker that generated this proposal")
    type: Literal["ENTRY", "EXIT", "WAIT"] = Field(..., description="Type of proposal")
    symbol: str = Field(..., description="Trading symbol (e.g., BTCUSDT)")
    direction: Literal["LONG", "SHORT", "NEUTRAL"] = Field(..., description="Trade direction")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence in this proposal")
    evidence: List[Evidence] = Field(default_factory=list, description="List of RAG FactCards supporting this proposal")
    reason: str = Field(..., description="Human-readable explanation for this proposal")
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "worker_name": "PullbackWorker_v1",
                "type": "ENTRY",
                "symbol": "BTCUSDT",
                "direction": "LONG",
                "confidence": 0.91,
                "evidence": [
                    {"source": "WaveRAG", "fact": "UPTREND_LADDER", "confidence": 0.88},
                    {"source": "LineRAG", "fact": "Strong Support retested 16 times", "confidence": 0.94}
                ],
                "reason": "Deep pullback to strong support with bullish wave structure"
            }
        }
