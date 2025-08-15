from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Literal
from enum import Enum
import uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    x: int
    y: int

class Driver(BaseModel):
    id: str
    x: int
    y: int
    status: DriverStatus = DriverStatus.available
    assigned_count: int = 0
    last_busy_tick: Optional[int] = None
    current_ride_id: Optional[str] = None

class Rider(BaseModel):
    id: str
    x: int
    y: int

class Ride(BaseModel):
    id: str
    rider_id: str
    pickup: Position
    dropoff: Position
    status: RideStatus = RideStatus.waiting
    driver_id: Optional[str] = None
    rejected_driver_ids: List[str] = []

class CreateDriverRequest(BaseModel):
    x: int
    y: int

class CreateRiderRequest(BaseModel):
    x: int
    y: int

class RequestRideRequest(BaseModel):
    rider_id: str
    dropoff: Position

class AcceptRejectRequest(BaseModel):
    driver_id: str
    ride_id: str
    accept: bool

class State:
    def __init__(self):
        self.drivers: Dict[str, Driver] = {}
        self.riders: Dict[str, Rider] = {}
        self.rides: Dict[str, Ride] = {}
        self.current_tick: int = 0

state = State()

def manhattan_distance(x1: int, y1: int, x2: int, y2: int) -> int:
    return abs(x1 - x2) + abs(y1 - y2)

def find_best_driver(ride: Ride) -> Optional[str]:
    available_drivers = [
        d for d in state.drivers.values() 
        if d.status == DriverStatus.available and d.id not in ride.rejected_driver_ids
    ]
    
    if not available_drivers:
        return None
    
    def driver_key(driver: Driver):
        eta = manhattan_distance(driver.x, driver.y, ride.pickup.x, ride.pickup.y)
        idle_ticks = state.current_tick - (driver.last_busy_tick if driver.last_busy_tick is not None else -999999)
        return (eta, driver.assigned_count, -idle_ticks)
    
    best_driver = min(available_drivers, key=driver_key)
    return best_driver.id

@app.post("/drivers")
def create_driver(request: CreateDriverRequest):
    driver_id = str(uuid.uuid4())
    driver = Driver(id=driver_id, x=request.x, y=request.y)
    state.drivers[driver_id] = driver
    return {"driver": driver}

@app.post("/riders")
def create_rider(request: CreateRiderRequest):
    rider_id = str(uuid.uuid4())
    rider = Rider(id=rider_id, x=request.x, y=request.y)
    state.riders[rider_id] = rider
    return {"rider": rider}

@app.post("/rides/request")
def request_ride(request: RequestRideRequest):
    if request.rider_id not in state.riders:
        raise HTTPException(status_code=404, detail="Rider not found")
    
    rider = state.riders[request.rider_id]
    ride_id = str(uuid.uuid4())
    ride = Ride(
        id=ride_id,
        rider_id=request.rider_id,
        pickup=Position(x=rider.x, y=rider.y),
        dropoff=request.dropoff
    )
    
    state.rides[ride_id] = ride
    
    driver_id = find_best_driver(ride)
    if driver_id:
        ride.driver_id = driver_id
        ride.status = RideStatus.awaiting_accept
        driver = state.drivers[driver_id]
        driver.status = DriverStatus.assigned
        driver.current_ride_id = ride_id
    else:
        ride.status = RideStatus.failed
    
    return {"ride": ride}

@app.post("/rides/accept-reject")
def accept_reject(request: AcceptRejectRequest):
    if request.ride_id not in state.rides:
        raise HTTPException(status_code=404, detail="Ride not found")
    if request.driver_id not in state.drivers:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    ride = state.rides[request.ride_id]
    driver = state.drivers[request.driver_id]
    
    if ride.driver_id != request.driver_id:
        raise HTTPException(status_code=400, detail="Driver not assigned to this ride")
    
    if request.accept:
        ride.status = RideStatus.in_progress
        driver.status = DriverStatus.on_trip
        driver.last_busy_tick = state.current_tick
    else:
        ride.rejected_driver_ids.append(request.driver_id)
        driver.status = DriverStatus.available
        driver.current_ride_id = None
        
        new_driver_id = find_best_driver(ride)
        if new_driver_id:
            ride.driver_id = new_driver_id
            ride.status = RideStatus.awaiting_accept
            new_driver = state.drivers[new_driver_id]
            new_driver.status = DriverStatus.assigned
            new_driver.current_ride_id = ride.id
        else:
            ride.status = RideStatus.failed
            ride.driver_id = None
    
    return {"ride": ride}

@app.post("/tick")
def tick():
    state.current_tick += 1
    
    for ride in state.rides.values():
        if ride.status == RideStatus.in_progress and ride.driver_id:
            driver = state.drivers[ride.driver_id]
            
            if driver.x != ride.pickup.x or driver.y != ride.pickup.y:
                if driver.x < ride.pickup.x:
                    driver.x += 1
                elif driver.x > ride.pickup.x:
                    driver.x -= 1
                elif driver.y < ride.pickup.y:
                    driver.y += 1
                elif driver.y > ride.pickup.y:
                    driver.y -= 1
            else:
                if driver.x != ride.dropoff.x or driver.y != ride.dropoff.y:
                    if driver.x < ride.dropoff.x:
                        driver.x += 1
                    elif driver.x > ride.dropoff.x:
                        driver.x -= 1
                    elif driver.y < ride.dropoff.y:
                        driver.y += 1
                    elif driver.y > ride.dropoff.y:
                        driver.y -= 1
                else:
                    ride.status = RideStatus.completed
                    driver.status = DriverStatus.available
                    driver.assigned_count += 1
                    driver.current_ride_id = None
                    rider = state.riders[ride.rider_id]
                    rider.x = ride.dropoff.x
                    rider.y = ride.dropoff.y
    
    return {"tick": state.current_tick}

@app.get("/state")
def get_state():
    return {
        "tick": state.current_tick,
        "drivers": list(state.drivers.values()),
        "riders": list(state.riders.values()),
        "rides": list(state.rides.values())
    }

@app.post("/reset")
def reset():
    state.drivers.clear()
    state.riders.clear()
    state.rides.clear()
    state.current_tick = 0
    return {"message": "State reset"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)