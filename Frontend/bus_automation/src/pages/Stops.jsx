import React, { useState } from 'react';
import Sidebar from '../components/Sidebar';
import { MapContainer, TileLayer, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

function MapClickHandler({ addStop }) {
  useMapEvents({
    click(e) {
      addStop(e.latlng);
    },
  });
  return null;
}

export default function Stops() {
  const [stops, setStops] = useState([]);

  const addStop = (latlng) => {
    if (stops.length < 7) {
      setStops([...stops, latlng]);
    }
  };

  return (
    <div className="flex">
      <Sidebar stops={stops} />
      <div className="w-full h-screen">
        <MapContainer center={[20.5937, 78.9629]} zoom={5} className="h-full w-full">
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution="&copy; OpenStreetMap contributors"
          />
          <MapClickHandler addStop={addStop} />
        </MapContainer>
      </div>
    </div>
  );
}
