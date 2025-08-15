# Ride Hailing Simulation

A fullstack ride-hailing dispatch system with FastAPI backend and Next.js frontend, implementing a grid-based city simulation with driver assignment, fairness algorithms, and ride management.

## Quick Start

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Backend runs on http://localhost:8000

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend runs on http://localhost:3001

## System Architecture

### Backend Structure
- **`app/models.py`** - Pydantic models for Driver, Rider, Ride, and GlobalState
- **`app/dispatcher.py`** - Dispatch logic and fairness algorithms
- **`app/main.py`** - FastAPI application with all endpoints

### Key Features
- 100×100 grid city with coordinate-based positioning
- Deterministic tick-based simulation
- Fairness-based driver dispatch algorithm
- Accept/reject ride workflow
- Manhattan distance pathfinding
- Real-time state management

## Dispatch Algorithm

The system selects drivers using a lexicographic tuple for fairness:

```python
def driver_sort_key(driver):
    eta = manhattan_distance(driver_pos, pickup_pos)
    idle_ticks = current_tick - (driver.last_busy_tick or -infinity)
    return (eta, driver.assigned_count, -idle_ticks)
```

**Priority order:**
1. **ETA to pickup** (Manhattan distance) - Lower is better
2. **Assignment count** - Fewer assignments preferred (fairness)
3. **Idle time** - Longer idle time preferred (fairness)

**Fairness tracking:**
- `assigned_count` increments on ride **acceptance** (actual work)
- `last_busy_tick` updates on ride **completion** (availability measurement)

## API Endpoints

### State Management
- `GET /state` - Get entire simulation state
- `POST /tick` - Advance simulation by one tick
- `POST /reset` - Reset all simulation data

### Driver Management  
- `POST /drivers` - Create driver `{x, y, id?}`
- `DELETE /drivers/{id}` - Remove driver (fails active rides)

### Rider Management
- `POST /riders` - Create rider `{x, y, id?}`  
- `DELETE /riders/{id}` - Remove rider (fails pending rides)

### Ride Management
- `POST /rides/request` - Request ride `{rider_id, pickup: {x,y}, dropoff: {x,y}}`
- `POST /rides/{ride_id}/accept` - Accept assigned ride
- `POST /rides/{ride_id}/reject` - Reject ride (triggers re-dispatch)

## Example Usage (curl)

### 1. Add drivers and riders
```bash
# Add drivers at different positions
curl -X POST http://localhost:8000/drivers \
  -H "Content-Type: application/json" \
  -d '{"x": 10, "y": 10}'

curl -X POST http://localhost:8000/drivers \
  -H "Content-Type: application/json" \
  -d '{"x": 50, "y": 50}'

# Add a rider
curl -X POST http://localhost:8000/riders \
  -H "Content-Type: application/json" \
  -d '{"x": 20, "y": 20}'
```

### 2. Request a ride
```bash
curl -X POST http://localhost:8000/rides/request \
  -H "Content-Type: application/json" \
  -d '{
    "rider_id": "RIDER_ID_FROM_STEP_1",
    "pickup": {"x": 20, "y": 20},
    "dropoff": {"x": 80, "y": 80}
  }'
```

### 3. Accept the ride
```bash
curl -X POST http://localhost:8000/rides/RIDE_ID_FROM_STEP_2/accept
```

### 4. Advance simulation
```bash
# Move drivers toward their destinations
curl -X POST http://localhost:8000/tick
curl -X POST http://localhost:8000/tick
curl -X POST http://localhost:8000/tick
# ... continue until ride completes
```

### 5. Check state
```bash
curl http://localhost:8000/state | jq .
```

## Simulation Flow

1. **Ride Request**: System finds best available driver using dispatch algorithm
2. **Assignment**: Driver status → "assigned", ride status → "awaiting_accept"
3. **Accept/Reject**: 
   - **Accept**: Driver status → "on_trip", ride status → "in_progress"
   - **Reject**: Try next best driver, or mark ride as "failed"
4. **Movement**: Each tick moves driver 1 unit toward pickup, then dropoff
5. **Completion**: Driver status → "available", ride status → "completed"

## Assumptions and Simplifications

- **Single-threaded**: No concurrency concerns, pure in-memory state
- **No persistence**: State resets on server restart
- **Manhattan movement**: Drivers move along grid lines (no diagonal)
- **One unit per tick**: Deterministic movement speed
- **Single rider per ride**: No pooling or multi-passenger rides
- **Manual time progression**: Time advances only via `/tick` endpoint

## Movement Algorithm

Drivers follow Manhattan pathfinding:
```python
# Priority: x-axis first, then y-axis
if driver.x != target.x:
    driver.x += 1 if driver.x < target.x else -1
elif driver.y != target.y:
    driver.y += 1 if driver.y < target.y else -1
```

**Phases:**
1. **To pickup**: Driver moves from current position → ride.pickup
2. **To dropoff**: Driver moves from pickup → ride.dropoff  
3. **Complete**: Rider teleports to dropoff, driver becomes available

## Testing the Happy Path

1. Start both servers (backend on :8000, frontend on :3001)
2. Add 2 drivers at different positions
3. Add 1 rider
4. Request ride with pickup at rider's location, dropoff elsewhere
5. Accept the ride in the UI
6. Click "Next Tick" repeatedly until driver reaches dropoff
7. Verify driver returns to "available" status and ride shows "completed"

## Error Handling

- **No available drivers**: Ride status → "failed"
- **All drivers reject**: Ride status → "failed" after trying all candidates
- **Driver deleted mid-ride**: Ride status → "failed", driver removed
- **Rider deleted mid-ride**: Ride status → "failed", active driver freed