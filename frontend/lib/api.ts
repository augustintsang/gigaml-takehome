const API_BASE_URL = 'http://localhost:8000';

interface Position {
  x: number;
  y: number;
}

interface Driver {
  id: string;
  x: number;
  y: number;
  status: 'available' | 'assigned' | 'on_trip' | 'offline';
  assigned_count: number;
  last_busy_tick: number | null;
  current_ride_id: string | null;
  is_heading_to_dropoff: boolean;
}

interface Rider {
  id: string;
  x: number;
  y: number;
}

interface Ride {
  id: string;
  rider_id: string;
  pickup: Position;
  dropoff: Position;
  status: 'waiting' | 'assigned' | 'awaiting_accept' | 'rejected' | 'in_progress' | 'completed' | 'failed';
  driver_id: string | null;
  rejected_driver_ids: string[];
}

interface State {
  tick: number;
  drivers: Driver[];
  riders: Rider[];
  rides: Ride[];
}

export class API {
  static async getState(): Promise<State> {
    const response = await fetch(`${API_BASE_URL}/state`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  }

  static async createDriver(x: number, y: number, id?: string): Promise<Driver> {
    const response = await fetch(`${API_BASE_URL}/drivers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ x, y, id }),
    });
    const data = await response.json();
    return data.driver;
  }

  static async deleteDriver(id: string): Promise<void> {
    await fetch(`${API_BASE_URL}/drivers/${id}`, {
      method: 'DELETE',
    });
  }

  static async createRider(x: number, y: number, id?: string): Promise<Rider> {
    const response = await fetch(`${API_BASE_URL}/riders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ x, y, id }),
    });
    const data = await response.json();
    return data.rider;
  }

  static async deleteRider(id: string): Promise<void> {
    await fetch(`${API_BASE_URL}/riders/${id}`, {
      method: 'DELETE',
    });
  }

  static async requestRide(rider_id: string, pickup: Position, dropoff: Position): Promise<Ride> {
    const response = await fetch(`${API_BASE_URL}/rides/request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rider_id, pickup, dropoff }),
    });
    const data = await response.json();
    return data.ride;
  }

  static async acceptRide(ride_id: string): Promise<Ride> {
    const response = await fetch(`${API_BASE_URL}/rides/${ride_id}/accept`, {
      method: 'POST',
    });
    const data = await response.json();
    return data.ride;
  }

  static async rejectRide(ride_id: string): Promise<Ride> {
    const response = await fetch(`${API_BASE_URL}/rides/${ride_id}/reject`, {
      method: 'POST',
    });
    const data = await response.json();
    return data.ride;
  }

  static async tick(): Promise<State> {
    const response = await fetch(`${API_BASE_URL}/tick`, {
      method: 'POST',
    });
    return response.json();
  }

  static async reset(): Promise<void> {
    await fetch(`${API_BASE_URL}/reset`, {
      method: 'POST',
    });
  }
}

export type { Driver, Rider, Ride, State, Position };