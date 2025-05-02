import random
import math
from datetime import datetime, timedelta
from collections import defaultdict

LATEST_ARRIVAL_TIME = "09:00 AM"
EARLIEST_DEPARTURE_TIME = "07:00 AM"
PENALTY_FOR_LATE_ARRIVAL = 1000
CAPACITY_UTILIZATION_WEIGHT = 0.7
ROUTE_EFFICIENCY_WEIGHT = 0.3
MUTATION_RATE = 0.2
POPULATION_SIZE = 50
NUM_GENERATIONS = 10
ELITISM_COUNT = 5

def mock_get_traffic_time(from_coords, to_coords):
    lat1, lon1 = from_coords
    lat2, lon2 = to_coords
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    distance = math.sqrt(dlat**2 + dlon**2) * 111
    base_time = distance * 2
    variation = random.randint(-3, 3)
    return max(5, int(base_time + variation))

def create_traffic_time_matrix(stops):
    num_stops = len(stops)
    time_matrix = [[0 for _ in range(num_stops)] for _ in range(num_stops)]
    stop_list = list(stops.keys())
    for i in range(num_stops):
        for j in range(i+1, num_stops):
            stop_i = stop_list[i]
            stop_j = stop_list[j]
            traffic_time = mock_get_traffic_time(stops[stop_i]["coordinates"], stops[stop_j]["coordinates"])
            time_matrix[i][j] = traffic_time
            time_matrix[j][i] = traffic_time
    return time_matrix

def generate_chromosome(data):
    UNIVERSITY_COORDS = [29.37546011959419, 79.53087868204494]
    stops = {stop["id"]: stop for stop in data["stops"] if stop["id"] != "college"}
    buses = data["buses"]
    
    chromosome = {
        "busroutes": {},
        "studentgroups": {},
        "departuretime": {},
        "total_distance": 0
    }

    # Student allocation (unchanged)
    for stop_id, stop in stops.items():
        remaining = stop["studentCount"]
        allocation = defaultdict(int)
        bus_order = random.sample(buses, len(buses))
        for bus in bus_order:
            if remaining <= 0: break
            max_possible = min(bus["capacity"] - sum(allocation.values()), remaining)
            if max_possible > 0:
                alloc = random.randint(0, max_possible)
                allocation[bus["id"]] = alloc
                remaining -= alloc
        chromosome["studentgroups"][stop_id] = dict(allocation)

    # Route generation with proper university timing
    for bus in buses:
        # Get stops this bus serves
        bus_stops = [stop_id for stop_id in stops 
                    if chromosome["studentgroups"][stop_id].get(bus["id"], 0) > 0]
        
        if not bus_stops:
            bus_stops = random.sample(list(stops.keys()), min(3, len(stops)))

        # Generate route: University → Stops → University
        route = ["college"] + bus_stops + ["college"]
        
        travel_segments = []
        current_coords = UNIVERSITY_COORDS
        departure_time = datetime.strptime(EARLIEST_DEPARTURE_TIME, "%I:%M %p")
        
        # University departure (only departure time)
        travel_segments.append({
            "stop_number": 1,
            "coordinates": UNIVERSITY_COORDS,
            "arrival_time": departure_time.strftime("%I:%M %p"),  # Same as departure for first stop
            "departure_time": departure_time.strftime("%I:%M %p")  # When bus leaves college
        })
        
        # Visit stops
        stop_number = 2
        for stop_id in route[1:-1]:
            next_coords = stops[stop_id]["coordinates"]
            traffic_time = mock_get_traffic_time(current_coords, next_coords)
            arrival_time = departure_time + timedelta(minutes=traffic_time)
            
            # At each stop, bus arrives, picks up students, and departs immediately
            travel_segments.append({
                "stop_number": stop_number,
                "coordinates": next_coords,
                "arrival_time": arrival_time.strftime("%I:%M %p"),
                "departure_time": arrival_time.strftime("%I:%M %p")  # Immediate departure
            })
            
            current_coords = next_coords
            departure_time = arrival_time
            stop_number += 1
        
        # Return to university (only arrival time)
        traffic_time = mock_get_traffic_time(current_coords, UNIVERSITY_COORDS)
        arrival_time = departure_time + timedelta(minutes=traffic_time)
        travel_segments.append({
            "stop_number": stop_number,
            "coordinates": UNIVERSITY_COORDS,
            "arrival_time": arrival_time.strftime("%I:%M %p"),  # When bus returns to college
            "departure_time": ""  # No departure time for final stop
        })
        
        chromosome["busroutes"][bus["id"]] = travel_segments
        chromosome["departuretime"][bus["id"]] = travel_segments[0]["departure_time"]
        chromosome["total_distance"] += sum(
            mock_get_traffic_time(
                travel_segments[i]["coordinates"],
                travel_segments[i+1]["coordinates"]
            )
            for i in range(len(travel_segments)-1)
        )
    
    return chromosome


def calculate_fitness(chromosome):
    fitness_score = 0
    latest_arrival = datetime.strptime(LATEST_ARRIVAL_TIME, "%I:%M %p")
    late_penalty = 0
    for bus_id, bus_route in chromosome["busroutes"].items():
        if not bus_route: continue
        last_stop = bus_route[-1]
        arrival_time = datetime.strptime(last_stop["arrival_time"], "%I:%M %p")
        if arrival_time > latest_arrival:
            late_penalty += PENALTY_FOR_LATE_ARRIVAL * (1 + (arrival_time - latest_arrival).total_seconds() / 60)
    fitness_score -= late_penalty
    capacity_score = 0
    bus_loads = defaultdict(int)
    total_students = 0
    for stop_id, allocation in chromosome["studentgroups"].items():
        for bus_id, count in allocation.items():
            bus_loads[bus_id] += count
            total_students += count
    avg_load = total_students / len(bus_loads) if bus_loads else 0
    for bus_id, load in bus_loads.items():
        capacity_score -= abs(load - avg_load) * CAPACITY_UTILIZATION_WEIGHT
    fitness_score += capacity_score
    route_efficiency = -chromosome.get("total_distance", 0) * ROUTE_EFFICIENCY_WEIGHT
    fitness_score += route_efficiency
    all_visited = set()
    redundancy_penalty = 0
    for bus_id, bus_route in chromosome["busroutes"].items():
        route_stops = [tuple(segment["coordinates"]) for segment in bus_route[1:-1]]
        for stop in route_stops:
            if stop in all_visited:
                redundancy_penalty += 10
            all_visited.add(stop)
    fitness_score -= redundancy_penalty
    return fitness_score

def select_parents(population, fitness_scores, tournament_size=3):
    parents = []
    for _ in range(2):
        tournament = random.sample(list(zip(population, fitness_scores)), tournament_size)
        winner = max(tournament, key=lambda x: x[1])[0]
        parents.append(winner)
    return parents[0], parents[1]

def crossover(parent1, parent2):
    child1 = {"busroutes": {}, "studentgroups": {}, "departuretime": {}, "total_distance": 0}
    child2 = {"busroutes": {}, "studentgroups": {}, "departuretime": {}, "total_distance": 0}
    for stop_id in parent1["studentgroups"]:
        if random.random() < 0.5:
            child1["studentgroups"][stop_id] = parent1["studentgroups"][stop_id].copy()
            child2["studentgroups"][stop_id] = parent2["studentgroups"][stop_id].copy()
        else:
            child1["studentgroups"][stop_id] = parent2["studentgroups"][stop_id].copy()
            child2["studentgroups"][stop_id] = parent1["studentgroups"][stop_id].copy()
    bus_ids = list(parent1["busroutes"].keys())
    split_point = random.randint(1, len(bus_ids)-1)
    for i, bus_id in enumerate(bus_ids):
        if i < split_point:
            child1["busroutes"][bus_id] = parent1["busroutes"][bus_id]
            child1["departuretime"][bus_id] = parent1["departuretime"][bus_id]
            child2["busroutes"][bus_id] = parent2["busroutes"][bus_id]
            child2["departuretime"][bus_id] = parent2["departuretime"][bus_id]
        else:
            child1["busroutes"][bus_id] = parent2["busroutes"][bus_id]
            child1["departuretime"][bus_id] = parent2["departuretime"][bus_id]
            child2["busroutes"][bus_id] = parent1["busroutes"][bus_id]
            child2["departuretime"][bus_id] = parent1["departuretime"][bus_id]
    for child in [child1, child2]:
        child["total_distance"] = sum(sum(mock_get_traffic_time(segment["coordinates"], child["busroutes"][bus_id][i+1]["coordinates"]) for i, segment in enumerate(route[:-1])) for bus_id, route in child["busroutes"].items())
    return child1, child2

def mutate(chromosome, data):
    stops = {stop["id"]: stop for stop in data["stops"] if stop["id"] != "college"}
    college = [stop for stop in data["stops"] if stop["id"] == "college"][0]
    if random.random() < MUTATION_RATE:
        mutation_type = random.choice(["route_optimize", "student_reallocate", "time_adjust"])
        if mutation_type == "route_optimize":
            bus_id = random.choice(list(chromosome["busroutes"].keys()))
            route = chromosome["busroutes"][bus_id]
            if len(route) > 3:
                middle = route[1:-1]
                if len(middle) > 1:
                    i, j = sorted(random.sample(range(len(middle)), 2))
                    middle[i:j+1] = middle[i:j+1][::-1]
                chromosome["busroutes"][bus_id] = [route[0]] + middle + [route[-1]]
                travel_segments = []
                current_coords = college["coordinates"]
                departure_time = datetime.strptime(route[0]["departure_time"], "%I:%M %p")
                stop_number = 1
                travel_segments.append({"stop_number": stop_number, "coordinates": current_coords, "arrival_time": departure_time.strftime("%I:%M %p"), "departure_time": departure_time.strftime("%I:%M %p")})
                stop_number += 1
                for stop in middle:
                    next_coords = stop["coordinates"]
                    traffic_time = mock_get_traffic_time(current_coords, next_coords)
                    arrival_time = departure_time + timedelta(minutes=traffic_time)
                    travel_segments.append({"stop_number": stop_number, "coordinates": next_coords, "arrival_time": arrival_time.strftime("%I:%M %p"), "departure_time": arrival_time.strftime("%I:%M %p")})
                    current_coords = next_coords
                    departure_time = arrival_time
                    stop_number += 1
                traffic_time = mock_get_traffic_time(current_coords, college["coordinates"])
                arrival_time = departure_time + timedelta(minutes=traffic_time)
                travel_segments.append({"stop_number": stop_number, "coordinates": college["coordinates"], "arrival_time": arrival_time.strftime("%I:%M %p"), "departure_time": arrival_time.strftime("%I:%M %p")})
                chromosome["busroutes"][bus_id] = travel_segments
                chromosome["departuretime"][bus_id] = travel_segments[0]["departure_time"]
        elif mutation_type == "student_reallocate":
            stop_id = random.choice(list(chromosome["studentgroups"].keys()))
            bus_ids = list(chromosome["studentgroups"][stop_id].keys())
            if len(bus_ids) > 1:
                from_bus, to_bus = random.sample(bus_ids, 2)
                max_transfer = min(chromosome["studentgroups"][stop_id][from_bus], next(bus["capacity"] for bus in data["buses"] if bus["id"] == to_bus) - sum(chromosome["studentgroups"][s].get(to_bus, 0) for s in chromosome["studentgroups"]))
                if max_transfer > 0:
                    transfer = random.randint(1, max_transfer)
                    chromosome["studentgroups"][stop_id][from_bus] -= transfer
                    chromosome["studentgroups"][stop_id][to_bus] = chromosome["studentgroups"][stop_id].get(to_bus, 0) + transfer
        elif mutation_type == "time_adjust":
            bus_id = random.choice(list(chromosome["busroutes"].keys()))
            current_time = datetime.strptime(chromosome["departuretime"][bus_id], "%I:%M %p")
            adjustment = random.randint(-30, 30)
            new_time = current_time + timedelta(minutes=adjustment)
            if new_time < datetime.strptime("06:00 AM", "%I:%M %p"):
                new_time = datetime.strptime("06:00 AM", "%I:%M %p")
            elif new_time > datetime.strptime("08:00 AM", "%I:%M %p"):
                new_time = datetime.strptime("08:00 AM", "%I:%M %p")
            chromosome["departuretime"][bus_id] = new_time.strftime("%I:%M %p")
            route = chromosome["busroutes"][bus_id]
            current_coords = college["coordinates"]
            departure_time = new_time
            stop_number = 1
            new_route = [{"stop_number": stop_number, "coordinates": current_coords, "arrival_time": departure_time.strftime("%I:%M %p"), "departure_time": departure_time.strftime("%I:%M %p")}]
            stop_number += 1
            for segment in route[1:-1]:
                next_coords = segment["coordinates"]
                traffic_time = mock_get_traffic_time(current_coords, next_coords)
                arrival_time = departure_time + timedelta(minutes=traffic_time)
                new_route.append({"stop_number": stop_number, "coordinates": next_coords, "arrival_time": arrival_time.strftime("%I:%M %p"), "departure_time": arrival_time.strftime("%I:%M %p")})
                current_coords = next_coords
                departure_time = arrival_time
                stop_number += 1
            traffic_time = mock_get_traffic_time(current_coords, college["coordinates"])
            arrival_time = departure_time + timedelta(minutes=traffic_time)
            new_route.append({"stop_number": stop_number, "coordinates": college["coordinates"], "arrival_time": arrival_time.strftime("%I:%M %p"), "departure_time": arrival_time.strftime("%I:%M %p")})
            chromosome["busroutes"][bus_id] = new_route
    chromosome["total_distance"] = sum(sum(mock_get_traffic_time(segment["coordinates"], chromosome["busroutes"][bus_id][i+1]["coordinates"]) for i, segment in enumerate(route[:-1])) for bus_id, route in chromosome["busroutes"].items())
    return chromosome

def validate_and_repair_solution(solution, data):
    buses = {bus["id"]: bus for bus in data["buses"]}
    stops = {stop["id"]: stop for stop in data["stops"] if stop["id"] != "college"}
    for stop_id, stop in stops.items():
        total_assigned = sum(solution["studentgroups"].get(stop_id, {}).values())
        if total_assigned < stop["studentCount"]:
            remaining = stop["studentCount"] - total_assigned
            available_buses = [bus_id for bus_id in buses if sum(solution["studentgroups"].get(s, {}).get(bus_id, 0) for s in stops) < buses[bus_id]["capacity"]]
            if available_buses:
                bus_id = random.choice(available_buses)
                if stop_id not in solution["studentgroups"]:
                    solution["studentgroups"][stop_id] = {}
                solution["studentgroups"][stop_id][bus_id] = solution["studentgroups"][stop_id].get(bus_id, 0) + remaining
    for bus_id in buses:
        total = sum(solution["studentgroups"].get(stop_id, {}).get(bus_id, 0) for stop_id in stops)
        if total > buses[bus_id]["capacity"]:
            over_by = total - buses[bus_id]["capacity"]
            assigned_stops = [stop_id for stop_id in stops if solution["studentgroups"].get(stop_id, {}).get(bus_id, 0) > 0]
            while over_by > 0 and assigned_stops:
                stop_id = random.choice(assigned_stops)
                current = solution["studentgroups"][stop_id][bus_id]
                reduce_by = min(current, over_by)
                solution["studentgroups"][stop_id][bus_id] -= reduce_by
                over_by -= reduce_by
                if solution["studentgroups"][stop_id][bus_id] == 0:
                    assigned_stops.remove(stop_id)
    return solution

def local_search_2opt(chromosome, data):
    improved = True
    while improved:
        improved = False
        for bus_id, route in chromosome['busroutes'].items():
            if len(route) < 4:
                continue
            best_distance = sum(mock_get_traffic_time(route[i]['coordinates'], route[i+1]['coordinates']) for i in range(len(route)-1))
            for i in range(1, len(route)-2):
                for j in range(i+1, len(route)-1):
                    if j-i == 1: continue
                    new_route = route[:i] + route[i:j][::-1] + route[j:]
                    new_distance = sum(mock_get_traffic_time(new_route[k]['coordinates'], new_route[k+1]['coordinates']) for k in range(len(new_route)-1))
                    if new_distance < best_distance:
                        chromosome['busroutes'][bus_id] = new_route
                        chromosome['total_distance'] += (new_distance - best_distance)
                        best_distance = new_distance
                        improved = True
    return chromosome

def run_hybrid_ga(data):
    population = [generate_chromosome(data) for _ in range(POPULATION_SIZE)]
    for generation in range(NUM_GENERATIONS):
        fitness_scores = [calculate_fitness(c) for c in population]
        elite_indices = sorted(range(len(fitness_scores)), key=lambda i: fitness_scores[i], reverse=True)[:ELITISM_COUNT]
        new_population = [population[i] for i in elite_indices]
        while len(new_population) < POPULATION_SIZE:
            parent1, parent2 = select_parents(population, fitness_scores)
            child1, child2 = crossover(parent1, parent2)
            if random.random() < 0.2:
                child1 = local_search_2opt(child1, data)
            child1 = mutate(child1, data)
            if random.random() < 0.2:
                child2 = local_search_2opt(child2, data)
            child2 = mutate(child2, data)
            new_population.extend([child1, child2])
        population = new_population[:POPULATION_SIZE]
    best = max(population, key=calculate_fitness)
    return local_search_2opt(best, data)

SAMPLE_INPUT = {
    "buses": [{"id": f"bus{i}", "capacity": 50} for i in range(1,7)],
    "stops": [
        {"id": "stopA", "coordinates": [29.3463, 79.5674], "studentCount": 70},
        {"id": "stopB", "coordinates": [29.2700, 79.5400], "studentCount": 30},
        {"id": "stopC", "coordinates": [29.2400, 79.5300], "studentCount": 40},
        {"id": "stopD", "coordinates": [29.3000, 79.5500], "studentCount": 50},
        {"id": "stopE", "coordinates": [29.2192, 79.5231], "studentCount": 60},
        {"id": "stopF", "coordinates": [29.2192, 79.5237], "studentCount": 60},
        {"id": "nainital", "coordinates": [29.3911, 79.4621], "studentCount": 50},
        {"id": "halwani", "coordinates": [29.6181, 79.6149], "studentCount": 50},
        {"id": "bhimtal", "coordinates": [29.3912, 79.5568], "studentCount": 50},
        {"id": "college", "coordinates": [29.3463, 79.5674], "studentCount": 0}
    ]
}

if __name__ == "__main__":
    best_solution = run_hybrid_ga(SAMPLE_INPUT)
    print(best_solution)