"""
Predefined Road Network Topologies and Scenarios.
Includes Smart City Grid and Arterial Corridor with bypasses and bottlenecks.
"""
from road_network.network import RoadNetwork


def build_smart_city_network() -> RoadNetwork:
    """
    Builds a realistic 12-intersection Smart City network with:
    - Downtown commercial core (Bottleneck)
    - River bridge bottleneck
    - Outer ring road / bypass expressways (Faster free-flow speed, longer distance)
    - Residential suburbs and industrial zones
    - Bidirectional corridors with paired lane sharing
    """
    net = RoadNetwork(name="Metro Smart City")

    # Intersections layout in Euclidean coordinate space (meters)
    # [Row 1 - North]
    net.add_intersection("NW_RES", "Northwest Heights", x=100.0, y=700.0)
    net.add_intersection("N_GATE", "North Transit Hub", x=500.0, y=750.0)
    net.add_intersection("NE_TECH", "Northeast Tech Campus", x=900.0, y=700.0)

    # [Row 2 - Mid North / River Bridge]
    net.add_intersection("RIVER_BR", "River Bridge Crossing", x=500.0, y=550.0)

    # [Row 3 - Central Core]
    net.add_intersection("W_IND", "West Industrial Park", x=100.0, y=400.0)
    net.add_intersection("DOWNTOWN", "Downtown Central Core", x=500.0, y=400.0)
    net.add_intersection("E_FIN", "East Financial Center", x=900.0, y=400.0)

    # [Row 4 - South]
    net.add_intersection("SW_PORT", "Southwest Logistics Port", x=100.0, y=100.0)
    net.add_intersection("S_CIVIC", "South Civic Plaza", x=500.0, y=100.0)
    net.add_intersection("SE_SUB", "Southeast Suburbs", x=900.0, y=100.0)

    # [Expressway Bypasses - Outer Loop]
    net.add_intersection("W_BYPASS", "West Ring Expressway", x=-100.0, y=400.0)
    net.add_intersection("E_BYPASS", "East Ring Expressway", x=1100.0, y=400.0)

    # Roads definition
    # 1. North Horizontal Corridor
    net.add_bidirectional_road(
        "R_NW_NG", "R_NG_NW", "NW_RES", "N_GATE",
        length=800.0, free_flow_speed=13.89, lanes_each=2, capacity_per_lane=6
    )
    net.add_bidirectional_road(
        "R_NG_NE", "R_NE_NG", "N_GATE", "NE_TECH",
        length=800.0, free_flow_speed=13.89, lanes_each=2, capacity_per_lane=6
    )

    # 2. Central River Bridge Bottleneck (North to River, River to Downtown)
    # The bridge has high demand, only 2 lanes each, prime bottleneck!
    net.add_bidirectional_road(
        "R_NG_RB", "R_RB_NG", "N_GATE", "RIVER_BR",
        length=400.0, free_flow_speed=11.11, lanes_each=2, capacity_per_lane=5
    )
    net.add_bidirectional_road(
        "R_RB_DT", "R_DT_RB", "RIVER_BR", "DOWNTOWN",
        length=400.0, free_flow_speed=11.11, lanes_each=2, capacity_per_lane=5
    )

    # 3. Downtown Core Horizontal Arterial
    net.add_bidirectional_road(
        "R_WI_DT", "R_DT_WI", "W_IND", "DOWNTOWN",
        length=800.0, free_flow_speed=13.89, lanes_each=2, capacity_per_lane=6
    )
    net.add_bidirectional_road(
        "R_DT_EF", "R_EF_DT", "DOWNTOWN", "E_FIN",
        length=800.0, free_flow_speed=13.89, lanes_each=2, capacity_per_lane=6
    )

    # 4. South Arterial
    net.add_bidirectional_road(
        "R_DT_SC", "R_SC_DT", "DOWNTOWN", "S_CIVIC",
        length=700.0, free_flow_speed=13.89, lanes_each=2, capacity_per_lane=6
    )
    net.add_bidirectional_road(
        "R_SP_SC", "R_SC_SP", "SW_PORT", "S_CIVIC",
        length=800.0, free_flow_speed=13.89, lanes_each=2, capacity_per_lane=6
    )
    net.add_bidirectional_road(
        "R_SC_SE", "R_SE_SC", "S_CIVIC", "SE_SUB",
        length=800.0, free_flow_speed=13.89, lanes_each=2, capacity_per_lane=6
    )

    # 5. Vertical Side Avenues
    net.add_bidirectional_road(
        "R_NW_WI", "R_WI_NW", "NW_RES", "W_IND",
        length=700.0, free_flow_speed=13.89, lanes_each=2, capacity_per_lane=6
    )
    net.add_bidirectional_road(
        "R_WI_SP", "R_SP_WI", "W_IND", "SW_PORT",
        length=700.0, free_flow_speed=13.89, lanes_each=2, capacity_per_lane=6
    )
    net.add_bidirectional_road(
        "R_NE_EF", "R_EF_NE", "NE_TECH", "E_FIN",
        length=700.0, free_flow_speed=13.89, lanes_each=2, capacity_per_lane=6
    )
    net.add_bidirectional_road(
        "R_EF_SE", "R_SE_EF", "E_FIN", "SE_SUB",
        length=700.0, free_flow_speed=13.89, lanes_each=2, capacity_per_lane=6
    )

    # 6. High-Speed Outer Ring Road / Expressways (Bypass routes)
    # Higher speed limit (22.2 m/s = 80 km/h), slightly longer distance, higher capacity
    net.add_bidirectional_road(
        "R_NW_WBP", "R_WBP_NW", "NW_RES", "W_BYPASS",
        length=900.0, free_flow_speed=22.22, lanes_each=3, capacity_per_lane=8
    )
    net.add_bidirectional_road(
        "R_WBP_SP", "R_SP_WBP", "W_BYPASS", "SW_PORT",
        length=900.0, free_flow_speed=22.22, lanes_each=3, capacity_per_lane=8
    )
    net.add_bidirectional_road(
        "R_NE_EBP", "R_EBP_NE", "NE_TECH", "E_BYPASS",
        length=900.0, free_flow_speed=22.22, lanes_each=3, capacity_per_lane=8
    )
    net.add_bidirectional_road(
        "R_EBP_SE", "R_SE_EBP", "E_BYPASS", "SE_SUB",
        length=900.0, free_flow_speed=22.22, lanes_each=3, capacity_per_lane=8
    )

    # 7. Diagonal Feeder Links
    net.add_bidirectional_road(
        "R_NW_DT", "R_DT_NW", "NW_RES", "DOWNTOWN",
        length=1100.0, free_flow_speed=12.50, lanes_each=1, capacity_per_lane=5
    )
    net.add_bidirectional_road(
        "R_NE_DT", "R_DT_NE", "NE_TECH", "DOWNTOWN",
        length=1100.0, free_flow_speed=12.50, lanes_each=1, capacity_per_lane=5
    )

    net.update_graph_weights("travel_time")
    return net


def build_arterial_corridor_network() -> RoadNetwork:
    """
    Builds a 6-node linear arterial network with parallel relief avenues.
    Specifically optimized for testing Dynamic Reversible Lane Assignment during rush hour.
    """
    net = RoadNetwork(name="Commuter Arterial Corridor")

    # Linear nodes along East-West Axis
    net.add_intersection("WEST_SUB", "West Residential Suburb", x=0.0, y=300.0)
    net.add_intersection("W_PLAZA", "West Junction Plaza", x=300.0, y=300.0)
    net.add_intersection("MID_CORR", "Midtown Corridor", x=600.0, y=300.0)
    net.add_intersection("E_PLAZA", "East Junction Plaza", x=900.0, y=300.0)
    net.add_intersection("EAST_CBD", "East Central Business District", x=1200.0, y=300.0)

    # Parallel Relief Bypass
    net.add_intersection("NORTH_BYPASS", "North Relief Parkway", x=600.0, y=550.0)

    # Main Arterial Segments (2-lane base each way, reversible up to 3:1)
    net.add_bidirectional_road("R_WS_WP", "R_WP_WS", "WEST_SUB", "W_PLAZA", 600.0, 13.89, 2, 6)
    net.add_bidirectional_road("R_WP_MC", "R_MC_WP", "W_PLAZA", "MID_CORR", 600.0, 13.89, 2, 6)
    net.add_bidirectional_road("R_MC_EP", "R_EP_MC", "MID_CORR", "E_PLAZA", 600.0, 13.89, 2, 6)
    net.add_bidirectional_road("R_EP_EC", "R_EC_EP", "E_PLAZA", "EAST_CBD", 600.0, 13.89, 2, 6)

    # Bypass connectors
    net.add_bidirectional_road("R_WP_NB", "R_NB_WP", "W_PLAZA", "NORTH_BYPASS", 800.0, 19.44, 2, 7)
    net.add_bidirectional_road("R_NB_EP", "R_EP_NB", "NORTH_BYPASS", "E_PLAZA", 800.0, 19.44, 2, 7)

    net.update_graph_weights("travel_time")
    return net
