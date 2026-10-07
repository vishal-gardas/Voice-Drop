"""Mapbox service for geocoding and routing"""

from typing import Any, Dict, List

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

try:
    from geopy.distance import geodesic

    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False
    geodesic = None


class MapboxService:
    """Mapbox API service for geocoding and routing without fallbacks"""

    def __init__(self, config):
        self.config = config
        self.api_key = getattr(config, "MAPBOX_API_KEY", None)

        if not REQUESTS_AVAILABLE:
            raise ImportError(
                "requests package is not installed. MapboxService requires it."
            )
        if not self.api_key:
            raise ValueError(
                "MAPBOX_API_KEY is not configured. MapboxService requires it."
            )

        self.user_location = {
            "lat": (
                float(config.USER_LAT)
                if hasattr(config, "USER_LAT")
                else 12.974072987767554
            ),
            "lng": (
                float(config.USER_LNG)
                if hasattr(config, "USER_LNG")
                else 79.16395954535963
            ),
        }
        self.call_count = 0
        self.base_url = "https://api.mapbox.com"

    def geocode_location(
        self, address_text: str, max_distance_km: int = 10
    ) -> List[Dict[str, Any]]:
        """Geocode location using Mapbox Geocoding API"""
        from ..utils.text_processing import clean_location_text

        cleaned_text = clean_location_text(address_text)

        if not cleaned_text:
            return []

        enhanced_queries = self._enhance_search_query(cleaned_text)
        final_results = []
        user_loc = (self.user_location["lat"], self.user_location["lng"])

        print(f"🔍 [Mapbox] Enhanced queries for '{cleaned_text}': {enhanced_queries}")

        for query in enhanced_queries:
            try:
                # Mapbox Geocoding API endpoint
                url = f"{self.base_url}/geocoding/v5/mapbox.places/{requests.utils.quote(query)}.json"
                params = {
                    "access_token": self.api_key,
                    "proximity": f"{self.user_location['lng']},{self.user_location['lat']}",
                    "limit": 5,
                    "types": "place,address,poi",
                }

                resp = requests.get(url, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                features = data.get("features", [])
                if not features:
                    continue

                for feature in features:
                    coords = feature.get("geometry", {}).get("coordinates", [])
                    if len(coords) != 2:
                        continue

                    lng, lat = coords
                    location_coords = (lat, lng)

                    # Calculate distance
                    if GEOPY_AVAILABLE:
                        distance = geodesic(location_coords, user_loc).km
                    else:
                        lat_diff = abs(location_coords[0] - user_loc[0])
                        lng_diff = abs(location_coords[1] - user_loc[1])
                        distance = ((lat_diff**2 + lng_diff**2) ** 0.5) * 111

                    if distance <= max_distance_km:
                        place_name = feature.get("text", "Unknown Place")
                        address = feature.get("place_name", "")
                        place_type = feature.get("place_type", [])

                        result_data = {
                            "lat": lat,
                            "lng": lng,
                            "place_name": place_name,
                            "address": address,
                            "distance_from_user": round(distance, 2),
                            "types": place_type,
                            "query_used": query,
                        }

                        # Avoid duplicates
                        if not any(
                            r["place_name"] == result_data["place_name"]
                            for r in final_results
                        ):
                            final_results.append(result_data)

            except Exception as e:
                print(f"❌ [Mapbox] Geocoding error for query '{query}': {e}")
                raise RuntimeError(f"Mapbox geocoding failed: {e}")

        # Sort by distance
        final_results.sort(key=lambda x: x["distance_from_user"])

        print(f"✅ [Mapbox] Found {len(final_results)} results for '{cleaned_text}'")
        self.call_count += 1
        return final_results

    def get_directions_to_customer(
        self, current_location: Dict[str, Any], customer_address: str
    ) -> Dict[str, Any]:
        """Get directions using Mapbox Directions API"""
        try:
            origin_lng = current_location["lng"]
            origin_lat = current_location["lat"]
            dest_lng = self.user_location["lng"]
            dest_lat = self.user_location["lat"]

            # Mapbox Directions API endpoint
            url = f"{self.base_url}/directions/v5/mapbox/driving/{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
            params = {
                "access_token": self.api_key,
                "steps": "true",
                "geometries": "geojson",
                "overview": "full",
            }

            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            routes = data.get("routes", [])
            if not routes:
                return {"success": False, "error": "No route found"}

            route = routes[0]
            duration_seconds = route.get("duration", 0)
            distance_meters = route.get("distance", 0)

            # Extract steps
            steps_text = []
            legs = route.get("legs", [])
            if legs:
                steps = legs[0].get("steps", [])
                for step in steps:
                    instruction = step.get("maneuver", {}).get("instruction", "")
                    if instruction:
                        steps_text.append(instruction)

            result = {
                "success": True,
                "duration_minutes": round(duration_seconds / 60, 1),
                "distance_km": round(distance_meters / 1000, 2),
                "steps": steps_text[:10],  # First 10 steps
                "summary": f"{round(distance_meters / 1000, 1)} km, {round(duration_seconds / 60)} minutes",
            }

            print(f"✅ [Mapbox] Directions: {result['summary']}")
            return result

        except Exception as e:
            print(f"❌ [Mapbox] Directions error: {e}")
            raise RuntimeError(f"Mapbox directions failed: {e}")

    def _enhance_search_query(self, text: str) -> List[str]:
        """Generate enhanced search queries"""
        queries = [text]

        # Add location context
        if "vit" in text.lower() or "vellore" in text.lower():
            if text not in ["vit vellore", "VIT Vellore"]:
                queries.append(f"{text}, Vellore")

        return queries[:3]
