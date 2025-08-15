import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app, state
from app.models import GlobalState, Driver, Rider, Ride, DriverStatus, RideStatus


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def clean_state():
    """Reset the global state before each test."""
    global state
    state.drivers.clear()
    state.riders.clear() 
    state.rides.clear()
    state.tick = 0
    yield state


@pytest.fixture
def sample_driver(clean_state):
    """Create a sample driver for testing."""
    from app.models import Driver
    driver = Driver(x=25, y=25)
    clean_state.drivers[driver.id] = driver
    return driver


@pytest.fixture 
def sample_rider(clean_state):
    """Create a sample rider for testing."""
    from app.models import Rider
    rider = Rider(x=50, y=50)
    clean_state.riders[rider.id] = rider
    return rider


@pytest.fixture
def multiple_drivers(clean_state):
    """Create multiple drivers at different locations."""
    drivers = []
    positions = [(10, 10), (30, 30), (70, 70), (90, 90)]
    
    for x, y in positions:
        driver = Driver(x=x, y=y)
        clean_state.drivers[driver.id] = driver
        drivers.append(driver)
    
    return drivers


@pytest.fixture
def multiple_riders(clean_state):
    """Create multiple riders at different locations."""
    riders = []
    positions = [(20, 20), (40, 40), (60, 60), (80, 80)]
    
    for x, y in positions:
        rider = Rider(x=x, y=y)
        clean_state.riders[rider.id] = rider
        riders.append(rider)
    
    return riders


@pytest.fixture
def busy_driver(clean_state):
    """Create a driver that is currently on a trip."""
    driver = Driver(x=25, y=25, status=DriverStatus.on_trip, assigned_count=5, last_busy_tick=10)
    clean_state.drivers[driver.id] = driver
    return driver


@pytest.fixture
def offline_driver(clean_state):
    """Create an offline driver."""
    driver = Driver(x=25, y=25, status=DriverStatus.offline)
    clean_state.drivers[driver.id] = driver
    return driver


class TestScenario:
    """Helper class for creating complex test scenarios."""
    
    @staticmethod
    def create_pending_ride(rider_id: str, pickup_x: int, pickup_y: int, dropoff_x: int, dropoff_y: int, state):
        """Create a ride in pending state."""
        from app.models import Ride, Position
        ride = Ride(
            rider_id=rider_id,
            pickup=Position(x=pickup_x, y=pickup_y),
            dropoff=Position(x=dropoff_x, y=dropoff_y)
        )
        state.rides[ride.id] = ride
        return ride
    
    @staticmethod
    def assign_driver_to_ride(driver_id: str, ride_id: str, state):
        """Assign a driver to a ride."""
        driver = state.drivers[driver_id]
        ride = state.rides[ride_id]
        
        driver.status = DriverStatus.assigned
        driver.current_ride_id = ride_id
        ride.driver_id = driver_id
        ride.status = RideStatus.awaiting_accept


@pytest.fixture
def test_scenario():
    """Provide the TestScenario helper class."""
    return TestScenario