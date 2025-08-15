import pytest
from fastapi.testclient import TestClient
from app.models import DriverStatus, RideStatus


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_no_available_drivers(self, client, clean_state):
        """Test ride request when no drivers are available."""
        # Create rider but no drivers
        rider_response = client.post("/riders", json={"x": 50, "y": 50})
        rider_id = rider_response.json()["rider"]["id"]
        
        # Request ride
        ride_response = client.post("/rides/request", json={
            "rider_id": rider_id,
            "pickup": {"x": 50, "y": 50},
            "dropoff": {"x": 60, "y": 60}
        })
        
        assert ride_response.status_code == 200
        ride_data = ride_response.json()["ride"]
        assert ride_data["status"] == "failed"
        assert ride_data["driver_id"] is None

    def test_all_drivers_busy(self, client, busy_driver):
        """Test ride request when all drivers are busy."""
        # Create rider
        rider_response = client.post("/riders", json={"x": 50, "y": 50})
        rider_id = rider_response.json()["rider"]["id"]
        
        # Request ride
        ride_response = client.post("/rides/request", json={
            "rider_id": rider_id,
            "pickup": {"x": 50, "y": 50},
            "dropoff": {"x": 60, "y": 60}
        })
        
        ride_data = ride_response.json()["ride"]
        assert ride_data["status"] == "failed"

    def test_all_drivers_offline(self, client, offline_driver):
        """Test ride request when all drivers are offline."""
        rider_response = client.post("/riders", json={"x": 50, "y": 50})
        rider_id = rider_response.json()["rider"]["id"]
        
        ride_response = client.post("/rides/request", json={
            "rider_id": rider_id,
            "pickup": {"x": 50, "y": 50},
            "dropoff": {"x": 60, "y": 60}
        })
        
        ride_data = ride_response.json()["ride"]
        assert ride_data["status"] == "failed"

    def test_driver_rejection_cascade(self, client, multiple_drivers):
        """Test what happens when multiple drivers reject the same ride."""
        # Create rider
        rider_response = client.post("/riders", json={"x": 45, "y": 45})
        rider_id = rider_response.json()["rider"]["id"]
        
        # Request ride
        ride_response = client.post("/rides/request", json={
            "rider_id": rider_id,
            "pickup": {"x": 45, "y": 45},
            "dropoff": {"x": 55, "y": 55}
        })
        ride_id = ride_response.json()["ride"]["id"]
        first_driver_id = ride_response.json()["ride"]["driver_id"]
        
        # First driver rejects
        reject_response = client.post(f"/rides/{ride_id}/reject")
        assert reject_response.status_code == 200
        
        ride_data = reject_response.json()["ride"]
        assert first_driver_id in ride_data["rejected_driver_ids"]
        
        # Should be reassigned to another driver
        second_driver_id = ride_data["driver_id"]
        assert second_driver_id != first_driver_id
        assert ride_data["status"] == "awaiting_accept"
        
        # Second driver also rejects
        reject_response2 = client.post(f"/rides/{ride_id}/reject")
        ride_data2 = reject_response2.json()["ride"]
        
        # Should try third driver or fail if none available
        assert len(ride_data2["rejected_driver_ids"]) == 2

    def test_all_drivers_reject_ride(self, client, clean_state):
        """Test ride failure when all drivers reject."""
        # Create exactly 2 drivers
        driver1_resp = client.post("/drivers", json={"x": 10, "y": 10})
        driver2_resp = client.post("/drivers", json={"x": 15, "y": 15})
        
        rider_resp = client.post("/riders", json={"x": 12, "y": 12})
        rider_id = rider_resp.json()["rider"]["id"]
        
        # Request ride
        ride_response = client.post("/rides/request", json={
            "rider_id": rider_id,
            "pickup": {"x": 12, "y": 12},
            "dropoff": {"x": 20, "y": 20}
        })
        ride_id = ride_response.json()["ride"]["id"]
        
        # Both drivers reject
        client.post(f"/rides/{ride_id}/reject")
        final_response = client.post(f"/rides/{ride_id}/reject")
        
        final_ride = final_response.json()["ride"]
        assert final_ride["status"] == "failed"
        assert final_ride["driver_id"] is None

    def test_invalid_coordinates(self, client, clean_state):
        """Test handling of invalid coordinates."""
        # Test creating driver with invalid coordinates
        invalid_driver_response = client.post("/drivers", json={"x": -5, "y": 105})
        assert invalid_driver_response.status_code == 422  # Validation error
        
        # Test creating rider with invalid coordinates
        invalid_rider_response = client.post("/riders", json={"x": 100, "y": -1})
        assert invalid_rider_response.status_code == 422
        
        # Test ride request with invalid coordinates
        rider_response = client.post("/riders", json={"x": 50, "y": 50})
        rider_id = rider_response.json()["rider"]["id"]
        
        invalid_ride_response = client.post("/rides/request", json={
            "rider_id": rider_id,
            "pickup": {"x": 150, "y": 50},
            "dropoff": {"x": 50, "y": -10}
        })
        assert invalid_ride_response.status_code == 422

    def test_nonexistent_rider_ride_request(self, client, clean_state):
        """Test ride request for non-existent rider."""
        ride_response = client.post("/rides/request", json={
            "rider_id": "non-existent-id",
            "pickup": {"x": 50, "y": 50},
            "dropoff": {"x": 60, "y": 60}
        })
        assert ride_response.status_code == 404

    def test_invalid_ride_operations(self, client, sample_driver, sample_rider):
        """Test operations on invalid or non-existent rides."""
        # Test accepting non-existent ride
        accept_response = client.post("/rides/non-existent-id/accept")
        assert accept_response.status_code == 404
        
        # Test rejecting non-existent ride
        reject_response = client.post("/rides/non-existent-id/reject")
        assert reject_response.status_code == 404
        
        # Create a ride and complete it, then try to accept it
        ride_response = client.post("/rides/request", json={
            "rider_id": sample_rider.id,
            "pickup": {"x": sample_rider.x, "y": sample_rider.y},
            "dropoff": {"x": 60, "y": 60}
        })
        ride_id = ride_response.json()["ride"]["id"]
        
        # Accept the ride
        client.post(f"/rides/{ride_id}/accept")
        
        # Try to accept again (should fail)
        double_accept_response = client.post(f"/rides/{ride_id}/accept")
        assert double_accept_response.status_code == 400

    def test_driver_deletion_during_ride(self, client, sample_driver, sample_rider):
        """Test deleting a driver during an active ride."""
        # Create and start a ride
        ride_response = client.post("/rides/request", json={
            "rider_id": sample_rider.id,
            "pickup": {"x": sample_rider.x, "y": sample_rider.y},
            "dropoff": {"x": 60, "y": 60}
        })
        ride_id = ride_response.json()["ride"]["id"]
        client.post(f"/rides/{ride_id}/accept")
        
        # Delete the driver during the ride
        delete_response = client.delete(f"/drivers/{sample_driver.id}")
        assert delete_response.status_code == 200
        
        # Check that ride is marked as failed
        state_response = client.get("/state")
        state_data = state_response.json()
        ride = next(r for r in state_data["rides"] if r["id"] == ride_id)
        assert ride["status"] == "failed"
        assert ride["driver_id"] is None

    def test_rider_deletion_during_ride(self, client, sample_driver, sample_rider):
        """Test deleting a rider during an active ride."""
        # Create and start a ride
        ride_response = client.post("/rides/request", json={
            "rider_id": sample_rider.id,
            "pickup": {"x": sample_rider.x, "y": sample_rider.y},
            "dropoff": {"x": 60, "y": 60}
        })
        ride_id = ride_response.json()["ride"]["id"]
        client.post(f"/rides/{ride_id}/accept")
        
        # Delete the rider during the ride
        delete_response = client.delete(f"/riders/{sample_rider.id}")
        assert delete_response.status_code == 200
        
        # Check that ride is marked as failed and driver is freed
        state_response = client.get("/state")
        state_data = state_response.json()
        ride = next(r for r in state_data["rides"] if r["id"] == ride_id)
        driver = next(d for d in state_data["drivers"] if d["id"] == sample_driver.id)
        
        assert ride["status"] == "failed"
        assert driver["status"] == "available"
        assert driver["current_ride_id"] is None

    def test_extreme_coordinates(self, client, clean_state):
        """Test edge cases with boundary coordinates."""
        # Test valid boundary coordinates
        driver_corner1 = client.post("/drivers", json={"x": 0, "y": 0})
        assert driver_corner1.status_code == 200
        
        driver_corner2 = client.post("/drivers", json={"x": 99, "y": 99})
        assert driver_corner2.status_code == 200
        
        rider_corner = client.post("/riders", json={"x": 0, "y": 99})
        assert rider_corner.status_code == 200
        rider_id = rider_corner.json()["rider"]["id"]
        
        # Test ride across maximum distance
        max_distance_ride = client.post("/rides/request", json={
            "rider_id": rider_id,
            "pickup": {"x": 0, "y": 99},
            "dropoff": {"x": 99, "y": 0}
        })
        assert max_distance_ride.status_code == 200

    def test_concurrent_ride_requests(self, client, sample_driver):
        """Test multiple simultaneous ride requests for the same driver."""
        # Create multiple riders
        rider1_resp = client.post("/riders", json={"x": 20, "y": 20})
        rider2_resp = client.post("/riders", json={"x": 21, "y": 21})
        rider1_id = rider1_resp.json()["rider"]["id"]
        rider2_id = rider2_resp.json()["rider"]["id"]
        
        # Request rides simultaneously (in quick succession)
        ride1_resp = client.post("/rides/request", json={
            "rider_id": rider1_id,
            "pickup": {"x": 20, "y": 20},
            "dropoff": {"x": 30, "y": 30}
        })
        
        ride2_resp = client.post("/rides/request", json={
            "rider_id": rider2_id,
            "pickup": {"x": 21, "y": 21},
            "dropoff": {"x": 31, "y": 31}
        })
        
        # Only one should get the driver, the other should fail
        ride1_data = ride1_resp.json()["ride"]
        ride2_data = ride2_resp.json()["ride"]
        
        assigned_rides = [r for r in [ride1_data, ride2_data] if r["status"] != "failed"]
        failed_rides = [r for r in [ride1_data, ride2_data] if r["status"] == "failed"]
        
        assert len(assigned_rides) == 1, "Only one ride should be assigned"
        assert len(failed_rides) == 1, "One ride should fail"