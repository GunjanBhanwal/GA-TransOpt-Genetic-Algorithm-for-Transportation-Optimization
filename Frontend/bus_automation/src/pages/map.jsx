import { useState, useEffect } from "react";
import axios from "axios";
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';

const colors = ["red", "blue", "green", "orange", "purple"];

export default function RouteMap() {
  const [routes, setRoutes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.post("http://localhost:8000/api/run/", {
          buses: [
            { id: "bus1", capacity: 50, depotCoordinates: [29.3463, 79.5674] },
            { id: "bus2", capacity: 50, depotCoordinates: [29.3463, 79.5674] }
          ],
          stops: [
            { id: "stopA", coordinates: [29.3463, 79.5674], studentCount: 70 },
            { id: "stopB", coordinates: [29.27, 79.54], studentCount: 30 },
            { id: "stopC", coordinates: [29.24, 79.53], studentCount: 40 },
            { id: "stopD", coordinates: [29.3, 79.55], studentCount: 50 },
            { id: "stopE", coordinates: [29.2192, 79.5231], studentCount: 60 },
            { id: "stopF", coordinates: [29.2192, 79.5231], studentCount: 60 },
            { id: "college", coordinates: [29.3463, 79.5674], studentCount: 0 }
          ],
          constraints: {
            hard: {
              maxStudentsPerBus: 50,
              collegeLast: true,
              latestArrivalTime: "09:00"
            },
            soft: {
              fuelWeight: 0.7,
              balanceWeight: 0.3
            }
          }
        });

        console.log("GA Result:", response.data);

        const busroutes = response.data.busroutes;
        if (busroutes && typeof busroutes === "object") {
          const parsedRoutes = Object.entries(busroutes).map(([busId, stops]) => ({
            busId,
            path: stops.map(stop => stop.coordinates)
          }));
          setRoutes(parsedRoutes);
        } else {
          console.warn("No valid busroutes in response");
        }

      } catch (error) {
        console.error("Error fetching GA result:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return <p>Loading map data...</p>;
  }

  return (
    <MapContainer center={[29.27, 79.54]} zoom={10} style={{ height: '100vh', width: '100%' }}>
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

      {routes.map((route, index) => (
        <Polyline
          key={index}
          positions={route.path}
          color={colors[index % colors.length]}
        />
      ))}

      {routes.flatMap(route =>
        route.path.map((coord, idx) => (
          <Marker key={`${route.busId}-${idx}`} position={coord}>
            <Popup>{`${route.busId} - Stop ${idx + 1}`}</Popup>
          </Marker>
        ))
      )}
    </MapContainer>
  );
}
