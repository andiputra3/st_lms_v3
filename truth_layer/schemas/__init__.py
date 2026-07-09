"""
ST-LMS v3 - Truth Layer Schemas
Strictly follows 02_TRUTH_LAYER_SPEC.md
No computed fields (distance, slope, duration) stored in JSON.
"""
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime


class LineVersion(BaseModel):
    """
    Represents a single event in the life of a SupertrendLine.
    Event types: "CREATE" (initial formation) or "MOVE" (price shift).
    """
    point_id: str = Field(..., description="Time ID of the point triggering this version")
    price: float = Field(..., description="Price level at this version")
    event: Literal["CREATE", "MOVE"] = Field(..., description="Event type")
    time_wib: datetime = Field(..., description="WIB timestamp of the event")


class SupertrendLine(BaseModel):
    """
    A horizontal support/resistance level formed by grouping SupertrendPoints.
    Stores history of price shifts in 'versions' array for auditability.
    Members are point_ids that contributed to this line.
    """
    line_id: str = Field(..., description="Unique identifier for this line")
    type: Literal["SUPPORT", "RESISTANCE"] = Field(..., description="Line type based on Supertrend color")
    current_price: float = Field(..., description="Latest price level of this line")
    strength: int = Field(..., description="Number of points confirming this line")
    versions: List[LineVersion] = Field(default_factory=list, description="History of price movements")
    members: List[str] = Field(default_factory=list, description="List of point_ids contributing to this line")
    
    class Config:
        json_schema_extra = {
            "example": {
                "line_id": "L2607081920-SUP-001",
                "type": "SUPPORT",
                "current_price": 95000.0,
                "strength": 3,
                "versions": [
                    {"point_id": "P2607081920", "price": 94800.0, "event": "CREATE", "time_wib": "2026-07-09T02:20:00"},
                    {"point_id": "P2607081930", "price": 95000.0, "event": "MOVE", "time_wib": "2026-07-09T02:30:00"}
                ],
                "members": ["P2607081920", "P2607081930"]
            }
        }


class SupertrendWave(BaseModel):
    """
    A market structure pattern formed by grouping SupertrendLines.
    Pattern detection based on sequence of line types/colors.
    Signature is a hash-like string representing the wave structure.
    """
    wave_id: str = Field(..., description="Unique identifier for this wave")
    pattern: str = Field(..., description="Detected pattern name (e.g., UPTREND_LADDER, SIDEWAY_CHANNEL)")
    sequence: List[str] = Field(default_factory=list, description="Sequence of line types forming the pattern")
    members: List[str] = Field(default_factory=list, description="List of line_ids contributing to this wave")
    signature: str = Field(..., description="Hash-like signature of the wave structure")
    
    class Config:
        json_schema_extra = {
            "example": {
                "wave_id": "W2607081920-001",
                "pattern": "UPTREND_LADDER",
                "sequence": ["SUPPORT", "SUPPORT", "SUPPORT"],
                "members": ["L2607081920-SUP-001", "L2607081930-SUP-002", "L2607081940-SUP-003"],
                "signature": "SUP-SUP-SUP-94800-95200-95600"
            }
        }
