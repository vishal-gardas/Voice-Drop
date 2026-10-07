"""Delivery Guidance Service - Uses OpenStreetMap Overpass API for POI searches"""

import time
from typing import Any, Dict, List

import requests


class DeliveryGuidanceService:
    """Service to guide delivery personnel from nearby landmarks to destination"""

    def __init__(self, config):
        self.config = config
        self.mapbox_api_key = getattr(config, "MAPBOX_API_KEY", None)
        self.destination_lat = (
            float(config.USER_LAT)
            if hasattr(config, "USER_LAT")
            else 12.970827983276324
        )
        self.destination_lng = (
            float(config.USER_LNG) if hasattr(config, "USER_LNG") else 79.15943441076058
        )
        self.mapbox_base_url = "https://api.mapbox.com"
        self.osm_base_url = "https://nominatim.openstreetmap.org"
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.osm_headers = {"User-Agent": "VoiceDrop-AI-Delivery-Assistant/1.0"}

        # Map common terms to OSM tags
        self.category_map = {
            "pharmacy": [("amenity", "pharmacy")],
            "hospital": [("amenity", "hospital"), ("amenity", "clinic")],
            "restaurant": [("amenity", "restaurant")],
            "college": [("amenity", "college"), ("amenity", "university")],
            "school": [("amenity", "school")],
            "bank": [("amenity", "bank")],
            "atm": [("amenity", "atm")],
            "store": [("shop", "*")],
            "shop": [("shop", "*")],
            "mall": [("shop", "mall")],
            "supermarket": [("shop", "supermarket")],
            "market": [("amenity", "marketplace")],
            "hotel": [("tourism", "hotel")],
            "temple": [("amenity", "place_of_worship")],
            "church": [("amenity", "place_of_worship")],
            "mosque": [("amenity", "place_of_worship")],
            "gate": [("barrier", "gate"), ("entrance", "*")],
            "parking": [("amenity", "parking")],
            "petrol": [("amenity", "fuel")],
            "gas station": [("amenity", "fuel")],
            "cafe": [("amenity", "cafe")],
            "samsung": [("shop", "electronics"), ("shop", "mobile_phone")],
            "electronics": [("shop", "electronics")],
            "domino": [("amenity", "fast_food")],
            "pizza": [("amenity", "fast_food"), ("amenity", "restaurant")],
        }

    def guide_delivery_person(
        self,
        landmark_description: str,
        max_radius_km: float = 2.0,
        destination_coords: tuple = None,
    ) -> Dict[str, Any]:
        """Guide delivery person from nearby landmark to destination

        Args:
            landmark_description: Description of landmark near delivery person
            max_radius_km: Search radius in kilometers
            destination_coords: Optional tuple of (latitude, longitude) - uses live location if provided,
                                 otherwise falls back to config values
        """
        # Use provided coordinates or fall back to config
        if destination_coords:
            dest_lat, dest_lng = destination_coords
            print(f"[DELIVERY GUIDE] Using LIVE destination: {dest_lat}, {dest_lng}")
        else:
            dest_lat, dest_lng = self.destination_lat, self.destination_lng
            print(f"[DELIVERY GUIDE] Using CONFIG destination: {dest_lat}, {dest_lng}")

        print(
            f"[DELIVERY GUIDE] Searching for '{landmark_description}' near destination..."
        )

        # Try Overpass API first for category searches (pharmacy, hospital, etc.)
        landmarks = self._search_overpass(
            landmark_description, max_radius_km, dest_lat, dest_lng
        )

        # Fallback to Nominatim for specific place names
        if not landmarks:
            landmarks = self._search_osm(
                landmark_description, max_radius_km, dest_lat, dest_lng
            )

        if not landmarks:
            return {
                "success": False,
                "error": f"Could not find '{landmark_description}' within {max_radius_km}km",
                "suggestion": "Can you describe another nearby landmark or building?",
            }

        closest = landmarks[0]
        print(
            f"[DELIVERY GUIDE] Found: {closest['name']} ({closest['distance_km']}km away)"
        )

        # Get directions from landmark to destination
        directions = self._get_directions(
            closest["lat"], closest["lng"], dest_lat, dest_lng
        )

        return {
            "success": True,
            "landmark": {
                "name": closest["name"],
                "address": closest["address"],
                "distance_from_destination": closest["distance_km"],
            },
            "route": {
                "total_distance_km": directions["distance_km"],
                "estimated_time_minutes": directions["duration_minutes"],
                "summary": directions["summary"],
            },
            "turn_by_turn_directions": directions["steps"],
        }

    def _search_overpass(
        self,
        query: str,
        radius_km: float,
        dest_lat: float = None,
        dest_lng: float = None,
    ) -> List[Dict[str, Any]]:
        """Search OpenStreetMap using Overpass API for category-based POI searches"""
        if dest_lat is None:
            dest_lat = self.destination_lat
        if dest_lng is None:
            dest_lng = self.destination_lng

        try:
            cleaned = self._clean_query(query).lower()

            # Find matching category
            osm_tags = []
            for keyword, tags in self.category_map.items():
                if keyword in cleaned:
                    osm_tags.extend(tags)
                    break

            if not osm_tags:
                print(f"[OVERPASS] No category match for '{cleaned}', skipping")
                return []

            print(f"[OVERPASS] Searching category: {osm_tags}")

            # Build Overpass query
            radius_meters = int(radius_km * 1000)
            queries = []
            for key, value in osm_tags:
                if value == "*":
                    queries.append(
                        f'node["{key}"](around:{radius_meters},{dest_lat},{dest_lng});'
                    )
                    queries.append(
                        f'way["{key}"](around:{radius_meters},{dest_lat},{dest_lng});'
                    )
                else:
                    queries.append(
                        f'node["{key}"="{value}"](around:{radius_meters},{dest_lat},{dest_lng});'
                    )
                    queries.append(
                        f'way["{key}"="{value}"](around:{radius_meters},{dest_lat},{dest_lng});'
                    )

            overpass_query = f"[out:json];({' '.join(queries)});out center;"

            time.sleep(1)  # Respect rate limit

            resp = requests.post(self.overpass_url, data=overpass_query, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            landmarks = []
            for element in data.get("elements", []):
                if element["type"] == "node":
                    lat = element.get("lat")
                    lng = element.get("lon")
                elif element["type"] == "way" and "center" in element:
                    lat = element["center"].get("lat")
                    lng = element["center"].get("lon")
                else:
                    continue

                if not lat or not lng:
                    continue

                distance = self._calc_distance(lat, lng, dest_lat, dest_lng)
                if distance <= radius_km:
                    tags = element.get("tags", {})
                    name = tags.get("name", tags.get("brand", "Unnamed"))

                    # Build address
                    address_parts = [name]
                    if tags.get("addr:street"):
                        address_parts.append(tags.get("addr:street"))
                    if tags.get("addr:city"):
                        address_parts.append(tags.get("addr:city"))

                    landmarks.append(
                        {
                            "name": name,
                            "address": ", ".join(address_parts),
                            "lat": lat,
                            "lng": lng,
                            "distance_km": round(distance, 2),
                        }
                    )

            landmarks.sort(key=lambda x: x["distance_km"])
            print(f"[OVERPASS] Found {len(landmarks)} results")
            return landmarks

        except Exception as e:
            print(f"[OVERPASS] Error: {e}")
            return []

    def _search_osm(
        self,
        query: str,
        radius_km: float,
        dest_lat: float = None,
        dest_lng: float = None,
    ) -> List[Dict[str, Any]]:
        """Search OpenStreetMap Nominatim"""
        if dest_lat is None:
            dest_lat = self.destination_lat
        if dest_lng is None:
            dest_lng = self.destination_lng

        try:
            cleaned = self._clean_query(query)
            print(f"[OSM] Searching: '{cleaned}'")

            url = f"{self.osm_base_url}/search"
            params = {
                "q": f"{cleaned}, Vellore, Tamil Nadu, India",
                "format": "json",
                "addressdetails": 1,
                "limit": 10,
            }

            time.sleep(1)  # Respect rate limit

            resp = requests.get(
                url, params=params, headers=self.osm_headers, timeout=10
            )
            resp.raise_for_status()
            results = resp.json()

            landmarks = []
            for place in results:
                lat = float(place.get("lat", 0))
                lng = float(place.get("lon", 0))
                distance = self._calc_distance(lat, lng, dest_lat, dest_lng)

                if distance <= radius_km:
                    name = place.get("display_name", "").split(",")[0]
                    landmarks.append(
                        {
                            "name": name or "Unknown",
                            "address": place.get("display_name", ""),
                            "lat": lat,
                            "lng": lng,
                            "distance_km": round(distance, 2),
                        }
                    )

            landmarks.sort(key=lambda x: x["distance_km"])
            print(f"[OSM] Found {len(landmarks)} results")
            return landmarks

        except Exception as e:
            print(f"[OSM] Error: {e}")
            return []

    def _get_directions(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float = None,
        dest_lng: float = None,
    ) -> Dict[str, Any]:
        """Get directions using OSRM (free routing)"""
        if dest_lat is None:
            dest_lat = self.destination_lat
        if dest_lng is None:
            dest_lng = self.destination_lng

        try:
            url = f"http://router.project-osrm.org/route/v1/walking/{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
            params = {"overview": "false", "steps": "true"}

            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != "Ok":
                return self._simple_directions(
                    origin_lat, origin_lng, dest_lat, dest_lng
                )

            route = data["routes"][0]
            duration = route.get("duration", 0)
            distance = route.get("distance", 0)

            steps = []
            for leg in route.get("legs", []):
                for step in leg.get("steps", [])[:10]:
                    maneuver = step.get("maneuver", {})
                    instruction = f"{maneuver.get('type', 'continue')} {maneuver.get('modifier', '')}".strip()
                    dist = step.get("distance", 0)
                    if instruction:
                        steps.append(f"{instruction.capitalize()} ({int(dist)}m)")

            return {
                "distance_km": round(distance / 1000, 2),
                "duration_minutes": round(duration / 60, 1),
                "steps": steps,
                "summary": f"{round(distance/1000, 1)}km, about {round(duration/60)} min walk",
            }

        except Exception as e:
            print(f"[OSRM] Error: {e}")
            return self._simple_directions(origin_lat, origin_lng, dest_lat, dest_lng)

    def _simple_directions(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float = None,
        dest_lng: float = None,
    ) -> Dict[str, Any]:
        """Simple fallback directions"""
        if dest_lat is None:
            dest_lat = self.destination_lat
        if dest_lng is None:
            dest_lng = self.destination_lng

        distance = self._calc_distance(origin_lat, origin_lng, dest_lat, dest_lng)
        time_min = distance / 5 * 60  # Assume 5 km/h walking

        return {
            "distance_km": round(distance, 2),
            "duration_minutes": round(time_min, 1),
            "steps": ["Walk towards the destination"],
            "summary": f"Approximately {round(distance, 1)}km, {round(time_min)} minutes walk",
        }

    def _clean_query(self, query: str) -> str:
        """Clean search query"""
        cleaned = query.lower().strip()
        phrases = [
            "i'm near",
            "i am near",
            "i'm at",
            "i am at",
            "near the",
            "near a",
            "the ",
        ]
        for phrase in phrases:
            if cleaned.startswith(phrase):
                cleaned = cleaned[len(phrase) :].strip()
        return cleaned.rstrip(".?!")

    def _calc_distance(
        self, lat: float, lng: float, dest_lat: float = None, dest_lng: float = None
    ) -> float:
        """Calculate distance using Haversine formula"""
        from math import atan2, cos, radians, sin, sqrt

        if dest_lat is None:
            dest_lat = self.destination_lat
        if dest_lng is None:
            dest_lng = self.destination_lng

        R = 6371
        lat1, lng1, lat2, lng2 = map(radians, [dest_lat, dest_lng, lat, lng])
        dlat = lat2 - lat1
        dlng = lng2 - lng1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c
