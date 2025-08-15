import pytest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient


class TestPerformance:
    """Performance tests for the ride system."""

    def test_multiple_concurrent_rides_performance(self, client, clean_state):
        """Test system performance with many concurrent rides."""
        # Create many drivers and riders
        num_entities = 20
        driver_ids = []
        rider_ids = []
        
        start_time = time.time()
        
        # Create drivers
        for i in range(num_entities):
            x, y = (i * 4) % 100, (i * 4) % 100  # Spread them out, keep within bounds
            response = client.post("/drivers", json={"x": x, "y": y})
            driver_ids.append(response.json()["driver"]["id"])
        
        # Create riders
        for i in range(num_entities):
            x, y = (i * 3) % 100, (i * 3 + 10) % 100  # Keep within bounds
            response = client.post("/riders", json={"x": x, "y": y})
            rider_ids.append(response.json()["rider"]["id"])
        
        setup_time = time.time() - start_time
        print(f"Setup time for {num_entities} entities: {setup_time:.3f}s")
        
        # Request multiple rides simultaneously
        ride_start_time = time.time()
        ride_ids = []
        
        for rider_id in rider_ids:
            response = client.post("/rides/request", json={
                "rider_id": rider_id,
                "pickup": {"x": 25, "y": 25},
                "dropoff": {"x": 75, "y": 75}
            })
            if response.status_code == 200:
                ride_data = response.json()["ride"]
                ride_ids.append(ride_data["id"])
                
                # Accept each ride immediately
                if ride_data["status"] == "awaiting_accept":
                    client.post(f"/rides/{ride_data['id']}/accept")
        
        ride_request_time = time.time() - ride_start_time
        print(f"Time to request and accept {len(ride_ids)} rides: {ride_request_time:.3f}s")
        
        # Measure tick performance
        tick_times = []
        completed_rides = set()
        max_ticks = 200
        
        for tick in range(max_ticks):
            tick_start = time.time()
            response = client.post("/tick")
            tick_time = time.time() - tick_start
            tick_times.append(tick_time)
            
            if response.status_code == 200:
                state_data = response.json()
                for ride in state_data["rides"]:
                    if ride["status"] == "completed":
                        completed_rides.add(ride["id"])
            
            if len(completed_rides) == len(ride_ids):
                break
        
        avg_tick_time = sum(tick_times) / len(tick_times)
        max_tick_time = max(tick_times)
        
        print(f"Average tick time: {avg_tick_time:.3f}s")
        print(f"Max tick time: {max_tick_time:.3f}s")
        print(f"Total ticks to complete all rides: {len(tick_times)}")
        print(f"Completed rides: {len(completed_rides)}/{len(ride_ids)}")
        
        # Performance assertions
        assert avg_tick_time < 0.1, "Average tick time should be under 100ms"
        assert max_tick_time < 0.5, "No single tick should take over 500ms"
        assert len(completed_rides) >= len(ride_ids) * 0.8, "At least 80% of rides should complete"

    def test_dispatch_algorithm_performance(self, client, clean_state):
        """Test dispatch algorithm performance with many drivers."""
        num_drivers = 100
        
        # Create many drivers at random locations
        import random
        random.seed(42)  # Deterministic for testing
        
        for i in range(num_drivers):
            x = random.randint(0, 99)
            y = random.randint(0, 99)
            client.post("/drivers", json={"x": x, "y": y})
        
        # Create rider
        rider_response = client.post("/riders", json={"x": 50, "y": 50})
        rider_id = rider_response.json()["rider"]["id"]
        
        # Measure dispatch time
        start_time = time.time()
        response = client.post("/rides/request", json={
            "rider_id": rider_id,
            "pickup": {"x": 50, "y": 50},
            "dropoff": {"x": 60, "y": 60}
        })
        dispatch_time = time.time() - start_time
        
        print(f"Dispatch time with {num_drivers} drivers: {dispatch_time:.3f}s")
        
        assert response.status_code == 200
        assert dispatch_time < 0.05, f"Dispatch should be under 50ms, got {dispatch_time:.3f}s"

    def test_state_endpoint_performance(self, client, clean_state):
        """Test /state endpoint performance with large amounts of data."""
        # Create substantial state
        num_each = 50
        
        # Create drivers, riders, and rides
        for i in range(num_each):
            client.post("/drivers", json={"x": i, "y": i})
            client.post("/riders", json={"x": i + 50, "y": i + 50})
        
        # Create some rides
        state_response = client.get("/state")
        state_data = state_response.json()
        
        for i in range(min(10, len(state_data["riders"]))):
            rider_id = state_data["riders"][i]["id"]
            client.post("/rides/request", json={
                "rider_id": rider_id,
                "pickup": {"x": 25, "y": 25},
                "dropoff": {"x": 75, "y": 75}
            })
        
        # Measure state retrieval time
        times = []
        for _ in range(10):
            start_time = time.time()
            response = client.get("/state")
            end_time = time.time()
            times.append(end_time - start_time)
            assert response.status_code == 200
        
        avg_time = sum(times) / len(times)
        print(f"Average /state response time with {num_each} entities: {avg_time:.3f}s")
        
        assert avg_time < 0.1, f"State endpoint should respond in under 100ms, got {avg_time:.3f}s"

    def test_memory_usage_stability(self, client, clean_state):
        """Test that memory usage remains stable during long operations."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform many operations
        operations = 100
        
        for i in range(operations):
            # Create and delete entities
            driver_resp = client.post("/drivers", json={"x": i % 100, "y": i % 100})
            driver_id = driver_resp.json()["driver"]["id"]
            
            rider_resp = client.post("/riders", json={"x": (i + 50) % 100, "y": (i + 50) % 100})
            rider_id = rider_resp.json()["rider"]["id"]
            
            # Create and complete a quick ride
            ride_resp = client.post("/rides/request", json={
                "rider_id": rider_id,
                "pickup": {"x": (i + 50) % 100, "y": (i + 50) % 100},
                "dropoff": {"x": (i + 51) % 100, "y": (i + 51) % 100}
            })
            
            if ride_resp.status_code == 200:
                ride_data = ride_resp.json()["ride"]
                if ride_data["status"] == "awaiting_accept":
                    client.post(f"/rides/{ride_data['id']}/accept")
                    
                    # Complete the ride quickly
                    for _ in range(5):
                        client.post("/tick")
            
            # Cleanup
            client.delete(f"/drivers/{driver_id}")
            client.delete(f"/riders/{rider_id}")
            
            # Reset state periodically
            if i % 20 == 0:
                client.post("/reset")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"Initial memory: {initial_memory:.1f} MB")
        print(f"Final memory: {final_memory:.1f} MB")
        print(f"Memory increase: {memory_increase:.1f} MB")
        
        # Memory shouldn't grow too much (allowing for some overhead)
        assert memory_increase < 50, f"Memory usage grew by {memory_increase:.1f} MB, should be under 50 MB"

    def test_api_response_time_consistency(self, client, sample_driver, sample_rider):
        """Test that API response times are consistent."""
        endpoints_to_test = [
            ("GET", "/state", None),
            ("POST", "/tick", None),
            ("POST", "/drivers", {"x": 30, "y": 30}),
            ("POST", "/riders", {"x": 40, "y": 40}),
        ]
        
        for method, endpoint, data in endpoints_to_test:
            times = []
            
            for _ in range(20):
                start_time = time.time()
                
                if method == "GET":
                    response = client.get(endpoint)
                elif method == "POST":
                    if data:
                        response = client.post(endpoint, json=data)
                    else:
                        response = client.post(endpoint)
                
                end_time = time.time()
                times.append(end_time - start_time)
                
                # Clean up created entities
                if endpoint == "/drivers" and response.status_code == 200:
                    driver_id = response.json()["driver"]["id"]
                    client.delete(f"/drivers/{driver_id}")
                elif endpoint == "/riders" and response.status_code == 200:
                    rider_id = response.json()["rider"]["id"]
                    client.delete(f"/riders/{rider_id}")
            
            avg_time = sum(times) / len(times)
            std_dev = (sum((t - avg_time) ** 2 for t in times) / len(times)) ** 0.5
            
            print(f"{method} {endpoint}: avg={avg_time:.3f}s, std_dev={std_dev:.3f}s")
            
            # Response times should be consistent (low standard deviation)
            assert avg_time < 0.1, f"{endpoint} average response time too high: {avg_time:.3f}s"
            assert std_dev < 0.05, f"{endpoint} response time too variable: {std_dev:.3f}s"