from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import uuid

from app.models import (
    Driver, Rider, Ride, GlobalState, DriverStatus, RideStatus,
    CreateDriverRequest, CreateRiderRequest, RequestRideRequest, Position
)
from app.dispatcher import Dispatcher, manhattan_distance

app = FastAPI(title="Ride Hailing Simulation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
state = GlobalState()
dispatcher = Dispatcher()


@app.get("/state", response_model=Dict[str, Any])
def get_state():
    """Get the entire state snapshot."""
    return {
        "tick": state.tick,
        "drivers": list(state.drivers.values()),
        "riders": list(state.riders.values()),
        "rides": list(state.rides.values())
    }


@app.post("/drivers", response_model=Dict[str, Driver])
def create_driver(request: CreateDriverRequest):
    """Create a new driver."""
    driver_id = request.id or str(uuid.uuid4())
    
    if driver_id in state.drivers:
        raise HTTPException(status_code=400, detail="Driver ID already exists")
    
    driver = Driver(id=driver_id, x=request.x, y=request.y)
    state.drivers[driver_id] = driver
    return {"driver": driver}


@app.delete("/drivers/{driver_id}")
def delete_driver(driver_id: str):
    """Delete a driver."""
    if driver_id not in state.drivers:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    driver = state.drivers[driver_id]
    
    # If driver is on a ride, mark ride as failed
    if driver.current_ride_id and driver.current_ride_id in state.rides:
        ride = state.rides[driver.current_ride_id]
        ride.status = RideStatus.failed
        ride.driver_id = None
    
    del state.drivers[driver_id]
    return {"message": "Driver deleted successfully"}


@app.post("/riders", response_model=Dict[str, Rider])
def create_rider(request: CreateRiderRequest):
    """Create a new rider."""
    rider_id = request.id or str(uuid.uuid4())
    
    if rider_id in state.riders:
        raise HTTPException(status_code=400, detail="Rider ID already exists")
    
    rider = Rider(id=rider_id, x=request.x, y=request.y)
    state.riders[rider_id] = rider
    return {"rider": rider}


@app.delete("/riders/{rider_id}")
def delete_rider(rider_id: str):
    """Delete a rider."""
    if rider_id not in state.riders:
        raise HTTPException(status_code=404, detail="Rider not found")
    
    # Mark any pending rides for this rider as failed
    for ride in state.rides.values():
        if ride.rider_id == rider_id and ride.status in [RideStatus.waiting, RideStatus.assigned, RideStatus.awaiting_accept, RideStatus.in_progress]:
            ride.status = RideStatus.failed
            if ride.driver_id and ride.driver_id in state.drivers:
                driver = state.drivers[ride.driver_id]
                driver.status = DriverStatus.available
                driver.current_ride_id = None
    
    del state.riders[rider_id]
    return {"message": "Rider deleted successfully"}


@app.post("/rides/request", response_model=Dict[str, Ride])
def request_ride(request: RequestRideRequest):
    """Request a new ride."""
    if request.rider_id not in state.riders:
        raise HTTPException(status_code=404, detail="Rider not found")
    
    ride_id = str(uuid.uuid4())
    ride = Ride(
        id=ride_id,
        rider_id=request.rider_id,
        pickup=request.pickup,
        dropoff=request.dropoff
    )
    
    state.rides[ride_id] = ride
    
    # Try to dispatch immediately
    driver_id = dispatcher.select_best_driver(ride, state)
    if driver_id:
        ride.driver_id = driver_id
        ride.status = RideStatus.awaiting_accept
        driver = state.drivers[driver_id]
        driver.status = DriverStatus.assigned
        driver.current_ride_id = ride_id
    else:
        ride.status = RideStatus.failed
    
    return {"ride": ride}


@app.post("/rides/{ride_id}/accept")
def accept_ride(ride_id: str):
    """Accept a ride."""
    if ride_id not in state.rides:
        raise HTTPException(status_code=404, detail="Ride not found")
    
    ride = state.rides[ride_id]
    
    if ride.status != RideStatus.awaiting_accept:
        raise HTTPException(status_code=400, detail="Ride is not awaiting acceptance")
    
    if not ride.driver_id or ride.driver_id not in state.drivers:
        raise HTTPException(status_code=400, detail="No driver assigned to this ride")
    
    driver = state.drivers[ride.driver_id]
    
    # Accept the ride
    ride.status = RideStatus.in_progress
    driver.status = DriverStatus.on_trip
    driver.assigned_count += 1  # Increment on accept as per fairness spec
    
    return {"ride": ride}


@app.post("/rides/{ride_id}/reject")
def reject_ride(ride_id: str):
    """Reject a ride."""
    if ride_id not in state.rides:
        raise HTTPException(status_code=404, detail="Ride not found")
    
    ride = state.rides[ride_id]
    
    if ride.status != RideStatus.awaiting_accept:
        raise HTTPException(status_code=400, detail="Ride is not awaiting acceptance")
    
    if not ride.driver_id or ride.driver_id not in state.drivers:
        raise HTTPException(status_code=400, detail="No driver assigned to this ride")
    
    driver = state.drivers[ride.driver_id]
    
    # Reject the ride
    ride.rejected_driver_ids.append(ride.driver_id)
    driver.status = DriverStatus.available
    driver.current_ride_id = None
    
    # Try to find another driver
    new_driver_id = dispatcher.select_best_driver(ride, state)
    if new_driver_id:
        ride.driver_id = new_driver_id
        ride.status = RideStatus.awaiting_accept
        new_driver = state.drivers[new_driver_id]
        new_driver.status = DriverStatus.assigned
        new_driver.current_ride_id = ride_id
    else:
        ride.status = RideStatus.failed
        ride.driver_id = None
    
    return {"ride": ride}


@app.post("/tick", response_model=Dict[str, Any])
def tick():
    """Advance simulation by one tick."""
    state.tick += 1
    
    # Move all on_trip drivers
    for ride in state.rides.values():
        if ride.status == RideStatus.in_progress and ride.driver_id:
            driver = state.drivers.get(ride.driver_id)
            if not driver or driver.status != DriverStatus.on_trip:
                continue
            
            # Check if driver reached pickup and should switch to dropoff
            if not driver.is_heading_to_dropoff and driver.x == ride.pickup.x and driver.y == ride.pickup.y:
                driver.is_heading_to_dropoff = True
            
            # Determine target based on phase
            target = {'x': ride.dropoff.x, 'y': ride.dropoff.y} if driver.is_heading_to_dropoff else {'x': ride.pickup.x, 'y': ride.pickup.y}
            
            # Move one step toward target using Manhattan path
            if driver.x != target['x']:
                driver.x += 1 if driver.x < target['x'] else -1
            elif driver.y != target['y']:
                driver.y += 1 if driver.y < target['y'] else -1
            
            # Check if reached dropoff (ride complete)
            if driver.x == ride.dropoff.x and driver.y == ride.dropoff.y:
                ride.status = RideStatus.completed
                driver.status = DriverStatus.available
                driver.current_ride_id = None
                driver.is_heading_to_dropoff = False  # Reset for next ride
                driver.last_busy_tick = state.tick  # Update on completion for fairness
                
                # Move rider to dropoff location
                if ride.rider_id in state.riders:
                    rider = state.riders[ride.rider_id]
                    rider.x = ride.dropoff.x
                    rider.y = ride.dropoff.y
    
    return get_state()


@app.post("/reset")
def reset():
    """Reset the simulation state."""
    global state
    state = GlobalState()
    return {"message": "State reset successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)