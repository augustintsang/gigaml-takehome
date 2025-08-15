from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Literal
from enum import Enum
import uuid


class DriverStatus(str, Enum):
    available = "available"
    assigned = "assigned"
    on_trip = "on_trip"
    offline = "offline"


class RideStatus(str, Enum):
    waiting = "waiting"
    assigned = "assigned"
    awaiting_accept = "awaiting_accept"
    rejected = "rejected"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class Position(BaseModel):
    x: int = Field(ge=0, le=99)
    y: int = Field(ge=0, le=99)


class Driver(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    x: int = Field(ge=0, le=99)
    y: int = Field(ge=0, le=99)
    status: DriverStatus = DriverStatus.available
    assigned_count: int = 0
    last_busy_tick: Optional[int] = None
    current_ride_id: Optional[str] = None
    is_heading_to_dropoff: bool = False  # Track if driver is past pickup phase


class Rider(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    x: int = Field(ge=0, le=99)
    y: int = Field(ge=0, le=99)


class Ride(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    rider_id: str
    pickup: Position
    dropoff: Position
    status: RideStatus = RideStatus.waiting
    driver_id: Optional[str] = None
    rejected_driver_ids: List[str] = Field(default_factory=list)


class GlobalState(BaseModel):
    tick: int = 0
    drivers: Dict[str, Driver] = Field(default_factory=dict)
    riders: Dict[str, Rider] = Field(default_factory=dict)
    rides: Dict[str, Ride] = Field(default_factory=dict)


class CreateDriverRequest(BaseModel):
    x: int = Field(ge=0, le=99)
    y: int = Field(ge=0, le=99)
    id: Optional[str] = None


class CreateRiderRequest(BaseModel):
    x: int = Field(ge=0, le=99)
    y: int = Field(ge=0, le=99)
    id: Optional[str] = None


class RequestRideRequest(BaseModel):
    rider_id: str
    pickup: Position
    dropoff: Position