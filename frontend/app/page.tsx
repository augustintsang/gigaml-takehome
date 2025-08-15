'use client'

import { useState, useEffect, useRef } from 'react'
import { API, type Driver, type Rider, type Ride, type State, type Position } from '@/lib/api'

export default function Home() {
  const [state, setState] = useState<State>({ tick: 0, drivers: [], riders: [], rides: [] })
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [selectedRider, setSelectedRider] = useState<string | null>(null)
  const [pickupX, setPickupX] = useState(0)
  const [pickupY, setPickupY] = useState(0)
  const [dropoffX, setDropoffX] = useState(50)
  const [dropoffY, setDropoffY] = useState(50)
  const [clickPos, setClickPos] = useState<{x: number, y: number} | null>(null)
  const [tickSpeed, setTickSpeed] = useState(1000)
  const gridRef = useRef<HTMLDivElement>(null)

  const fetchState = async () => {
    try {
      console.log('Fetching state...')
      const data = await API.getState()
      console.log('Received state:', data)
      setState(data)
    } catch (error) {
      console.error('Failed to fetch state:', error)
    }
  }

  useEffect(() => {
    fetchState()
  }, [])

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(fetchState, tickSpeed)
      return () => clearInterval(interval)
    }
  }, [autoRefresh, tickSpeed])

  // Update pickup when rider is selected
  useEffect(() => {
    if (selectedRider) {
      const rider = state.riders.find(r => r.id === selectedRider)
      if (rider) {
        setPickupX(rider.x)
        setPickupY(rider.y)
      }
    }
  }, [selectedRider, state.riders])

  const createDriver = async (x: number, y: number) => {
    try {
      await API.createDriver(x, y)
      fetchState()
    } catch (error) {
      console.error('Failed to create driver:', error)
    }
  }

  const createRider = async (x: number, y: number) => {
    try {
      await API.createRider(x, y)
      fetchState()
    } catch (error) {
      console.error('Failed to create rider:', error)
    }
  }

  const requestRide = async (riderId: string) => {
    try {
      await API.requestRide(riderId, 
        { x: pickupX, y: pickupY }, 
        { x: dropoffX, y: dropoffY }
      )
      fetchState()
    } catch (error) {
      console.error('Failed to request ride:', error)
    }
  }

  const acceptRide = async (rideId: string) => {
    try {
      await API.acceptRide(rideId)
      fetchState()
    } catch (error) {
      console.error('Failed to accept ride:', error)
    }
  }

  const rejectRide = async (rideId: string) => {
    try {
      await API.rejectRide(rideId)
      fetchState()
    } catch (error) {
      console.error('Failed to reject ride:', error)
    }
  }

  const tick = async () => {
    try {
      const newState = await API.tick()
      setState(newState)
    } catch (error) {
      console.error('Failed to tick:', error)
    }
  }

  const reset = async () => {
    try {
      setAutoRefresh(false)
      await API.reset()
      fetchState()
    } catch (error) {
      console.error('Failed to reset:', error)
    }
  }

  const deleteDriver = async (driverId: string) => {
    try {
      await API.deleteDriver(driverId)
      fetchState()
    } catch (error) {
      console.error('Failed to delete driver:', error)
    }
  }

  const deleteRider = async (riderId: string) => {
    try {
      await API.deleteRider(riderId)
      fetchState()
    } catch (error) {
      console.error('Failed to delete rider:', error)
    }
  }

  const handleGridClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!gridRef.current) return
    const rect = gridRef.current.getBoundingClientRect()
    const x = Math.floor(((e.clientX - rect.left) / rect.width) * 100)
    const y = Math.floor(((e.clientY - rect.top) / rect.height) * 100)
    setClickPos({ x, y })
  }

  const gridSize = 600
  const cellSize = gridSize / 100

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold mb-6 text-gray-800">🚗 Ride Hailing Simulation</h1>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="mb-6">
              <h2 className="text-xl font-semibold mb-4 text-gray-700">Simulation Controls</h2>
              <div className="flex flex-wrap gap-3 mb-4">
                <button onClick={() => tick()} className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors">
                  Next Tick ⏭️
                </button>
                <button onClick={() => setAutoRefresh(!autoRefresh)} className={`px-6 py-3 ${autoRefresh ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'} text-white rounded-lg font-medium transition-colors`}>
                  {autoRefresh ? '⏸️ Stop Auto Refresh' : '▶️ Auto Refresh'}
                </button>
                <button onClick={() => fetchState()} className="px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors">
                  🔄 Refresh State
                </button>
                <button onClick={reset} className="px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-medium transition-colors">
                  🔄 Reset
                </button>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-lg font-medium text-gray-700">Tick: <span className="text-2xl font-bold text-blue-600">{state.tick}</span></span>
                {autoRefresh && (
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-gray-600">Refresh Speed:</label>
                    <input
                      type="range"
                      min="500"
                      max="3000"
                      step="250"
                      value={tickSpeed}
                      onChange={(e) => setTickSpeed(Number(e.target.value))}
                      className="w-32"
                    />
                    <span className="text-sm text-gray-600">{tickSpeed}ms</span>
                  </div>
                )}
              </div>
            </div>

            <div className="mb-6">
              <h2 className="text-xl font-semibold mb-4 text-gray-700">City Grid (Click to place entities)</h2>
              <div className="mb-3 flex gap-3">
                {clickPos && (
                  <>
                    <button 
                      onClick={() => clickPos && createDriver(clickPos.x, clickPos.y)}
                      className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium transition-colors"
                    >
                      Add Driver at ({clickPos.x},{clickPos.y})
                    </button>
                    <button 
                      onClick={() => clickPos && createRider(clickPos.x, clickPos.y)}
                      className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg text-sm font-medium transition-colors"
                    >
                      Add Rider at ({clickPos.x},{clickPos.y})
                    </button>
                  </>
                )}
              </div>
              
              <div 
                ref={gridRef}
                className="relative border-4 border-gray-400 bg-white cursor-crosshair"
                style={{ width: gridSize + 'px', height: gridSize + 'px' }}
                onClick={handleGridClick}
              >
                {Array.from({ length: 10 }, (_, i) => (
                  <div key={`h${i}`} className="absolute w-full border-t border-gray-200" style={{ top: (i + 1) * gridSize / 10 + 'px' }} />
                ))}
                {Array.from({ length: 10 }, (_, i) => (
                  <div key={`v${i}`} className="absolute h-full border-l border-gray-200" style={{ left: (i + 1) * gridSize / 10 + 'px' }} />
                ))}
                
                {state.drivers.map(driver => (
                  <div
                    key={driver.id}
                    className={`absolute w-4 h-4 rounded-full border-2 border-gray-800 transition-all duration-500 ${
                      driver.status === 'available' ? 'bg-green-500' :
                      driver.status === 'assigned' ? 'bg-yellow-500' :
                      driver.status === 'on_trip' ? 'bg-purple-500' : 'bg-gray-500'
                    }`}
                    style={{
                      left: (driver.x / 100) * gridSize - 8 + 'px',
                      top: (driver.y / 100) * gridSize - 8 + 'px'
                    }}
                    title={`Driver ${driver.id.slice(0, 8)}\nStatus: ${driver.status}\nPosition: (${driver.x},${driver.y})\nTrips: ${driver.assigned_count}`}
                  />
                ))}
                
                {state.riders.map(rider => (
                  <div
                    key={rider.id}
                    className="absolute w-4 h-4 bg-orange-500 border-2 border-gray-800 transition-all duration-500"
                    style={{
                      left: (rider.x / 100) * gridSize - 8 + 'px',
                      top: (rider.y / 100) * gridSize - 8 + 'px'
                    }}
                    title={`Rider ${rider.id.slice(0, 8)}\nPosition: (${rider.x},${rider.y})`}
                  />
                ))}
                
                {state.rides.filter(r => r.status === 'in_progress' || r.status === 'awaiting_accept').map(ride => (
                  <div key={ride.id}>
                    <div
                      className="absolute w-3 h-3 bg-blue-600 rounded-full opacity-70"
                      style={{
                        left: (ride.pickup.x / 100) * gridSize - 6 + 'px',
                        top: (ride.pickup.y / 100) * gridSize - 6 + 'px'
                      }}
                      title="Pickup"
                    />
                    <div
                      className="absolute w-3 h-3 bg-red-600 rounded-full opacity-70"
                      style={{
                        left: (ride.dropoff.x / 100) * gridSize - 6 + 'px',
                        top: (ride.dropoff.y / 100) * gridSize - 6 + 'px'
                      }}
                      title="Dropoff"
                    />
                    {ride.status === 'in_progress' && ride.driver_id && (
                      <svg className="absolute pointer-events-none" style={{ left: 0, top: 0, width: gridSize, height: gridSize }}>
                        <line
                          x1={(state.drivers.find(d => d.id === ride.driver_id)?.x || 0) / 100 * gridSize}
                          y1={(state.drivers.find(d => d.id === ride.driver_id)?.y || 0) / 100 * gridSize}
                          x2={ride.dropoff.x / 100 * gridSize}
                          y2={ride.dropoff.y / 100 * gridSize}
                          stroke="rgba(239, 68, 68, 0.3)"
                          strokeWidth="2"
                          strokeDasharray="5,5"
                        />
                      </svg>
                    )}
                  </div>
                ))}
                
                {clickPos && (
                  <div
                    className="absolute w-6 h-6 border-2 border-blue-600 bg-blue-200 opacity-50 pointer-events-none"
                    style={{
                      left: (clickPos.x / 100) * gridSize - 12 + 'px',
                      top: (clickPos.y / 100) * gridSize - 12 + 'px'
                    }}
                  />
                )}
              </div>
              
              <div className="mt-4 flex flex-wrap gap-4 text-sm">
                <span className="flex items-center gap-2"><div className="w-4 h-4 bg-green-500 rounded-full border border-gray-800" /> Available Driver</span>
                <span className="flex items-center gap-2"><div className="w-4 h-4 bg-yellow-500 rounded-full border border-gray-800" /> Assigned Driver</span>
                <span className="flex items-center gap-2"><div className="w-4 h-4 bg-purple-500 rounded-full border border-gray-800" /> On Trip</span>
                <span className="flex items-center gap-2"><div className="w-4 h-4 bg-orange-500 border border-gray-800" /> Rider</span>
                <span className="flex items-center gap-2"><div className="w-3 h-3 bg-blue-600 rounded-full" /> Pickup</span>
                <span className="flex items-center gap-2"><div className="w-3 h-3 bg-red-600 rounded-full" /> Dropoff</span>
              </div>
            </div>

            <div className="mb-6">
              <h2 className="text-xl font-semibold mb-4 text-gray-700">Quick Add Entities</h2>
              <div className="space-y-3">
                <div>
                  <p className="text-sm text-gray-600 mb-2">Drivers:</p>
                  <div className="flex flex-wrap gap-2">
                    <button onClick={() => createDriver(Math.floor(Math.random() * 100), Math.floor(Math.random() * 100))} className="px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded text-sm font-medium transition-colors">
                      Random Driver
                    </button>
                    <button onClick={() => createDriver(25, 25)} className="px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded text-sm font-medium transition-colors">
                      (25,25)
                    </button>
                    <button onClick={() => createDriver(75, 75)} className="px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded text-sm font-medium transition-colors">
                      (75,75)
                    </button>
                    <button onClick={() => createDriver(50, 50)} className="px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded text-sm font-medium transition-colors">
                      (50,50)
                    </button>
                  </div>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-2">Riders:</p>
                  <div className="flex flex-wrap gap-2">
                    <button onClick={() => createRider(Math.floor(Math.random() * 100), Math.floor(Math.random() * 100))} className="px-3 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded text-sm font-medium transition-colors">
                      Random Rider
                    </button>
                    <button onClick={() => createRider(20, 80)} className="px-3 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded text-sm font-medium transition-colors">
                      (20,80)
                    </button>
                    <button onClick={() => createRider(80, 20)} className="px-3 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded text-sm font-medium transition-colors">
                      (80,20)
                    </button>
                    <button onClick={() => createRider(50, 10)} className="px-3 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded text-sm font-medium transition-colors">
                      (50,10)
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-semibold mb-4 text-gray-700">Request Ride</h2>
              <div className="space-y-3">
                <select
                  value={selectedRider || ''}
                  onChange={(e) => setSelectedRider(e.target.value)}
                  className="w-full border-2 border-gray-300 rounded-lg px-4 py-2 focus:border-blue-500 focus:outline-none"
                >
                  <option value="">Select a Rider</option>
                  {state.riders.map(rider => (
                    <option key={rider.id} value={rider.id}>
                      Rider {rider.id.slice(0, 8)} - At ({rider.x},{rider.y})
                    </option>
                  ))}
                </select>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">Pickup X</label>
                    <input
                      type="number"
                      value={pickupX}
                      onChange={(e) => setPickupX(Number(e.target.value))}
                      className="w-full border-2 border-gray-300 rounded-lg px-4 py-2 focus:border-blue-500 focus:outline-none"
                      min="0"
                      max="99"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">Pickup Y</label>
                    <input
                      type="number"
                      value={pickupY}
                      onChange={(e) => setPickupY(Number(e.target.value))}
                      className="w-full border-2 border-gray-300 rounded-lg px-4 py-2 focus:border-blue-500 focus:outline-none"
                      min="0"
                      max="99"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">Dropoff X</label>
                    <input
                      type="number"
                      value={dropoffX}
                      onChange={(e) => setDropoffX(Number(e.target.value))}
                      className="w-full border-2 border-gray-300 rounded-lg px-4 py-2 focus:border-blue-500 focus:outline-none"
                      min="0"
                      max="99"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">Dropoff Y</label>
                    <input
                      type="number"
                      value={dropoffY}
                      onChange={(e) => setDropoffY(Number(e.target.value))}
                      className="w-full border-2 border-gray-300 rounded-lg px-4 py-2 focus:border-blue-500 focus:outline-none"
                      min="0"
                      max="99"
                    />
                  </div>
                </div>
                <button
                  onClick={() => selectedRider && requestRide(selectedRider)}
                  disabled={!selectedRider}
                  className="w-full px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                >
                  🚕 Request Ride
                </button>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-semibold mb-4 text-gray-700">Active Rides</h2>
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {state.rides.length === 0 ? (
                  <p className="text-gray-500 text-center py-4">No rides yet</p>
                ) : (
                  state.rides.map(ride => (
                    <div key={ride.id} className={`border-2 p-4 rounded-lg ${
                      ride.status === 'completed' ? 'border-green-300 bg-green-50' :
                      ride.status === 'failed' ? 'border-red-300 bg-red-50' :
                      ride.status === 'in_progress' ? 'border-blue-300 bg-blue-50' :
                      ride.status === 'awaiting_accept' ? 'border-yellow-300 bg-yellow-50' :
                      'border-gray-300'
                    }`}>
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="font-medium">Ride {ride.id.slice(0, 8)}</div>
                          <div className="text-sm text-gray-600 mt-1">
                            Status: <span className={`font-semibold ${
                              ride.status === 'completed' ? 'text-green-600' :
                              ride.status === 'failed' ? 'text-red-600' :
                              ride.status === 'in_progress' ? 'text-blue-600' :
                              ride.status === 'awaiting_accept' ? 'text-yellow-600' :
                              'text-gray-600'
                            }`}>{ride.status.replace('_', ' ').toUpperCase()}</span>
                          </div>
                          <div className="text-sm text-gray-600">
                            📍 ({ride.pickup.x},{ride.pickup.y}) → 🎯 ({ride.dropoff.x},{ride.dropoff.y})
                          </div>
                          {ride.driver_id && (
                            <div className="text-sm text-gray-600">
                              Driver: {ride.driver_id.slice(0, 8)}
                            </div>
                          )}
                        </div>
                        {ride.status === 'awaiting_accept' && ride.driver_id && (
                          <div className="flex gap-2">
                            <button
                              onClick={() => acceptRide(ride.id)}
                              className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white rounded text-sm font-medium transition-colors"
                            >
                              ✓ Accept
                            </button>
                            <button
                              onClick={() => rejectRide(ride.id)}
                              className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-sm font-medium transition-colors"
                            >
                              ✗ Reject
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-semibold mb-4 text-gray-700">Drivers Status</h2>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {state.drivers.length === 0 ? (
                  <p className="text-gray-500 text-center py-4">No drivers yet</p>
                ) : (
                  state.drivers.map(driver => (
                    <div key={driver.id} className="border border-gray-200 p-3 rounded-lg">
                      <div className="flex justify-between items-center">
                        <div>
                          <span className="font-medium text-sm">Driver {driver.id.slice(0, 8)}</span>
                          <div className="text-xs text-gray-600 mt-1">
                            📍 ({driver.x},{driver.y}) | Status: <span className={`font-semibold ${
                              driver.status === 'available' ? 'text-green-600' :
                              driver.status === 'on_trip' ? 'text-purple-600' :
                              driver.status === 'assigned' ? 'text-yellow-600' :
                              'text-gray-600'
                            }`}>{driver.status}</span> | Trips: {driver.assigned_count}
                          </div>
                        </div>
                        <button
                          onClick={() => deleteDriver(driver.id)}
                          className="px-2 py-1 bg-red-500 hover:bg-red-600 text-white rounded text-xs font-medium transition-colors"
                          title="Delete Driver"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-semibold mb-4 text-gray-700">Riders</h2>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {state.riders.length === 0 ? (
                  <p className="text-gray-500 text-center py-4">No riders yet</p>
                ) : (
                  state.riders.map(rider => (
                    <div key={rider.id} className="border border-gray-200 p-3 rounded-lg">
                      <div className="flex justify-between items-center">
                        <div>
                          <span className="font-medium text-sm">Rider {rider.id.slice(0, 8)}</span>
                          <div className="text-xs text-gray-600 mt-1">
                            📍 ({rider.x},{rider.y})
                          </div>
                        </div>
                        <button
                          onClick={() => deleteRider(rider.id)}
                          className="px-2 py-1 bg-red-500 hover:bg-red-600 text-white rounded text-xs font-medium transition-colors"
                          title="Delete Rider"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}