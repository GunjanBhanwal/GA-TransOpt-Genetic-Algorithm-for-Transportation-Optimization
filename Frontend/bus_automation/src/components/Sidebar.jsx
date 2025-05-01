import React from 'react';

export default function Sidebar({ stops }) {
  return (
    <div className="h-screen w-64 bg-gray-600 p-4 overflow-y-auto">
      <h1 className="text-center py-3 text-2xl font-bold text-blue-400">Bus Route Planner</h1>
      <h3 className="text-xl text-white font-semibold mb-4">Stops</h3>

      {stops.length === 0 ? (
        <p className="text-white">Click on the map to add up to 3 stops</p>
      ) : (
        <ul className="space-y-3">
          {stops.map((stop, index) => (
            <li key={index} className="text-white bg-gray-700 p-2 rounded">
              <p><strong>Stop {index + 1}</strong></p>
              <p>Lat: {stop.lat.toFixed(4)}</p>
              <p>Lng: {stop.lng.toFixed(4)}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
