from flask import Flask, render_template, jsonify, request
import requests
import math
import time

app = Flask(__name__)

# ============================================================
# JOURNEYGUARDIAN - WORLDWIDE BACKEND
# ============================================================

APP_NAME = "JourneyGuardian"
VERSION = "3.0"

HEADERS = {
    "User-Agent": "JourneyGuardian/3.0 (learning project)",
    "Accept": "application/json"
}

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

FOOT_ROUTE_URL = (
    "https://routing.openstreetmap.de/"
    "routed-foot/route/v1/driving"
)

DRIVING_ROUTE_URL = (
    "https://router.project-osrm.org/"
    "route/v1/driving"
)

LAST_SEARCH = 0


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():
    return render_template("index.html")


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    return jsonify({
        "app": APP_NAME,
        "version": VERSION,
        "status": "online",
        "services": {
            "search": "online",
            "walking": "online",
            "driving": "online",
            "transport": "online"
        }
    })


# ============================================================
# DISTANCE
# ============================================================

def distance_km(lat1, lon1, lat2, lon2):

    R = 6371.0

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(p1)
        * math.cos(p2)
        * math.sin(dlon / 2) ** 2
    )

    return (
        R
        * 2
        * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a)
        )
    )


# ============================================================
# WORLDWIDE SEARCH
# ============================================================

@app.route("/search")
def search():

    global LAST_SEARCH

    query = request.args.get("q", "").strip()

    if len(query) < 2:
        return jsonify([])

    # Protect public Nominatim service
    now = time.time()

    if now - LAST_SEARCH < 1:
        time.sleep(
            1 - (now - LAST_SEARCH)
        )

    LAST_SEARCH = time.time()

    try:

        response = requests.get(

            NOMINATIM_URL,

            params={
                "q": query,
                "format": "json",
                "limit": 8,
                "addressdetails": 1,
                "accept-language": "en"
            },

            headers=HEADERS,

            timeout=15
        )

        response.raise_for_status()

        places = response.json()

        results = []

        for place in places:

            try:

                results.append({
                    "name": place.get(
                        "display_name",
                        "Unknown place"
                    ),

                    "lat": float(
                        place["lat"]
                    ),

                    "lon": float(
                        place["lon"]
                    )
                })

            except Exception:
                continue

        return jsonify(results)

    except Exception as error:

        print(
            "SEARCH ERROR:",
            error
        )

        return jsonify({
            "error": "Search service unavailable"
        }), 503


# ============================================================
# WALKING ROUTE
# ============================================================

@app.route(
    "/walking-route",
    methods=["POST"]
)
def walking_route():

    data = request.get_json(
        silent=True
    ) or {}

    try:

        from_lat = float(
            data["from_lat"]
        )

        from_lon = float(
            data["from_lon"]
        )

        to_lat = float(
            data["to_lat"]
        )

        to_lon = float(
            data["to_lon"]
        )

    except Exception:

        return jsonify({
            "error": "Invalid coordinates"
        }), 400


    if not (
        -90 <= from_lat <= 90
        and -180 <= from_lon <= 180
        and -90 <= to_lat <= 90
        and -180 <= to_lon <= 180
    ):

        return jsonify({
            "error": "Coordinates out of range"
        }), 400


    url = (
        f"{FOOT_ROUTE_URL}/"
        f"{from_lon},{from_lat};"
        f"{to_lon},{to_lat}"
    )


    try:

        response = requests.get(

            url,

            params={
                "overview": "full",
                "geometries": "geojson",
                "steps": "true",
                "alternatives": "false"
            },

            headers=HEADERS,

            timeout=40
        )

        response.raise_for_status()

        data = response.json()


        if data.get("code") != "Ok":

            return jsonify({
                "error": "No walking route found"
            }), 404


        routes = data.get(
            "routes",
            []
        )

        if not routes:

            return jsonify({
                "error": "No walking route found"
            }), 404


        route = routes[0]


        return jsonify({

            "mode": "WALK",

            "distance_km": round(
                route["distance"] / 1000,
                2
            ),

            "duration_min": max(
                1,
                round(
                    route["duration"] / 60
                )
            ),

            "geometry":
                route["geometry"]

        })


    except Exception as error:

        print(
            "WALKING ERROR:",
            error
        )

        return jsonify({
            "error":
                "Walking routing service unavailable"
        }), 503


# ============================================================
# DRIVING ROUTE
# ============================================================

@app.route(
    "/driving-route",
    methods=["POST"]
)
def driving_route():

    data = request.get_json(
        silent=True
    ) or {}

    try:

        from_lat = float(
            data["from_lat"]
        )

        from_lon = float(
            data["from_lon"]
        )

        to_lat = float(
            data["to_lat"]
        )

        to_lon = float(
            data["to_lon"]
        )

    except Exception:

        return jsonify({
            "error": "Invalid coordinates"
        }), 400


    url = (
        f"{DRIVING_ROUTE_URL}/"
        f"{from_lon},{from_lat};"
        f"{to_lon},{to_lat}"
    )


    try:

        response = requests.get(

            url,

            params={
                "overview": "full",
                "geometries": "geojson",
                "steps": "true",
                "alternatives": "false"
            },

            headers=HEADERS,

            timeout=35
        )

        response.raise_for_status()

        data = response.json()


        if not data.get("routes"):

            return jsonify({
                "error": "No driving route found"
            }), 404


        route = data["routes"][0]


        return jsonify({

            "mode": "DRIVE",

            "distance_km": round(
                route["distance"] / 1000,
                2
            ),

            "duration_min": max(
                1,
                round(
                    route["duration"] / 60
                )
            ),

            "geometry":
                route["geometry"]

        })


    except Exception as error:

        print(
            "DRIVING ERROR:",
            error
        )

        return jsonify({
            "error":
                "Driving routing service unavailable"
        }), 503


# ============================================================
# NEARBY TRANSPORT
# ============================================================

@app.route(
    "/transport",
    methods=["POST"]
)
def transport():

    data = request.get_json(
        silent=True
    ) or {}

    try:

        lat = float(
            data["lat"]
        )

        lon = float(
            data["lon"]
        )

    except Exception:

        return jsonify({
            "error": "Invalid location"
        }), 400


    radius = 5000


    query = f"""
    [out:json][timeout:40];

    (
        node["highway"="bus_stop"]
        (around:{radius},{lat},{lon});

        node["railway"="station"]
        (around:{radius},{lat},{lon});

        node["railway"="halt"]
        (around:{radius},{lat},{lon});

        node["railway"="subway_entrance"]
        (around:{radius},{lat},{lon});

        node["railway"="tram_stop"]
        (around:{radius},{lat},{lon});

        node["railway"="light_rail"]
        (around:{radius},{lat},{lon});

        node["amenity"="ferry_terminal"]
        (around:{radius},{lat},{lon});

        node["public_transport"="platform"]
        (around:{radius},{lat},{lon});
    );

    out center;
    """


    try:

        response = requests.post(

            OVERPASS_URL,

            data={
                "data": query
            },

            headers=HEADERS,

            timeout=50
        )

        response.raise_for_status()

        raw = response.json()

    except Exception as error:

        print(
            "TRANSPORT ERROR:",
            error
        )

        return jsonify({
            "error":
                "Transport service unavailable"
        }), 503


    results = []

    seen = set()


    for element in raw.get(
        "elements",
        []
    ):

        tags = element.get(
            "tags",
            {}
        )


        name = (
            tags.get("name")
            or tags.get("ref")
            or "Unnamed stop"
        )


        item_lat = element.get(
            "lat"
        )

        item_lon = element.get(
            "lon"
        )


        if item_lat is None:

            center = element.get(
                "center",
                {}
            )

            item_lat = center.get(
                "lat"
            )

            item_lon = center.get(
                "lon"
            )


        if (
            item_lat is None
            or item_lon is None
        ):
            continue


        railway = tags.get(
            "railway"
        )

        highway = tags.get(
            "highway"
        )

        amenity = tags.get(
            "amenity"
        )


        if highway == "bus_stop":

            transport_type = "BUS"

        elif railway == "subway_entrance":

            transport_type = "METRO"

        elif railway in [
            "tram_stop",
            "light_rail"
        ]:

            transport_type = "TRAM"

        elif railway in [
            "station",
            "halt"
        ]:

            transport_type = "TRAIN"

        elif amenity == "ferry_terminal":

            transport_type = "FERRY"

        else:

            transport_type = "PUBLIC TRANSPORT"


        item_lat = float(
            item_lat
        )

        item_lon = float(
            item_lon
        )


        distance = distance_km(

            lat,
            lon,

            item_lat,
            item_lon

        )


        key = (
            transport_type,
            name,
            round(item_lat, 5),
            round(item_lon, 5)
        )


        if key in seen:
            continue


        seen.add(key)


        results.append({

            "type":
                transport_type,

            "name":
                name,

            "lat":
                item_lat,

            "lon":
                item_lon,

            "distance":
                round(
                    distance,
                    2
                )

        })


    results.sort(
        key=lambda item:
        item["distance"]
    )


    return jsonify(
        results[:60]
    )


# ============================================================
# JOURNEY INFORMATION
# ============================================================

@app.route(
    "/journey-info",
    methods=["POST"]
)
def journey_info():

    data = request.get_json(
        silent=True
    ) or {}


    try:

        distance = float(
            data.get(
                "distance_km",
                0
            )
        )

        duration = int(
            data.get(
                "duration_min",
                0
            )
        )

        mode = str(
            data.get(
                "mode",
                "WALK"
            )
        ).upper()

    except Exception:

        return jsonify({
            "error": "Invalid journey data"
        }), 400


    if distance < 0:
        distance = 0


    if duration < 0:
        duration = 0


    if mode == "WALK":

        label = "Walking"

    elif mode == "DRIVE":

        label = "Driving"

    elif mode == "TRAIN":

        label = "Train"

    elif mode == "BUS":

        label = "Bus"

    elif mode == "METRO":

        label = "Metro"

    else:

        label = mode


    return jsonify({

        "mode": mode,

        "mode_name": label,

        "distance_km": round(
            distance,
            2
        ),

        "duration_min": duration,

        "status": "ready",

        "message":
            f"{label} journey calculated successfully."

    })


# ============================================================
# SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("==========================================")
    print("          JOURNEYGUARDIAN")
    print("          WORLDWIDE BACKEND")
    print("==========================================")
    print()
    print("Server:")
    print("http://127.0.0.1:5000")
    print()
    print("Health check:")
    print("http://127.0.0.1:5000/health")
    print()
    print("==========================================")
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )