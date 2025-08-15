from typing import Optional, List
from app.models import Driver, Ride, GlobalState, DriverStatus


def manhattan_distance(a: dict, b: dict) -> int:
    """Calculate Manhattan distance between two points."""
    return abs(a['x'] - b['x']) + abs(a['y'] - b['y'])


class Dispatcher:
    @staticmethod
    def select_best_driver(ride: Ride, state: GlobalState) -> Optional[str]:
        """
        Select the best available driver for a ride based on:
        1. ETA to pickup (Manhattan distance) - ascending
        2. Total assignments count - ascending (for fairness)
        3. Idle time (ticks since last busy) - descending (prefer idle drivers)
        
        Returns driver_id or None if no available drivers.
        """
        available_drivers = [
            driver for driver in state.drivers.values()
            if driver.status == DriverStatus.available 
            and driver.id not in ride.rejected_driver_ids
        ]
        
        if not available_drivers:
            return None
        
        def driver_sort_key(driver: Driver):
            # Calculate ETA to pickup
            eta = manhattan_distance(
                {'x': driver.x, 'y': driver.y},
                {'x': ride.pickup.x, 'y': ride.pickup.y}
            )
            
            # Calculate idle ticks (negative for descending sort)
            idle_ticks = state.tick - (driver.last_busy_tick if driver.last_busy_tick is not None else -999999)
            
            # Return tuple for lexicographic sorting
            return (eta, driver.assigned_count, -idle_ticks)
        
        best_driver = min(available_drivers, key=driver_sort_key)
        return best_driver.id