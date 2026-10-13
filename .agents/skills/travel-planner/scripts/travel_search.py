#!/usr/bin/env python3
"""
travel_search.py — Real-time travel search via Firecrawl Alexandria API.
Called by Allie's travel-bot via `terminal`. Zero external dependencies (stdlib only).

Usage:
    python3 travel_search.py hotels --destination "Hermann, Missouri" --checkin 2026-11-15 --checkout 2026-11-17
    python3 travel_search.py flights --origin "Kansas City" --destination "Tokyo" --departure 2026-03-15 --return 2026-03-25
    python3 travel_search.py flight-calendar --origin "Kansas City" --destination "Los Angeles"
    python3 travel_search.py cars --latitude 38.7046 --longitude -90.3882 --start 2026-11-15T10:00 --end 2026-11-17T10:00
    python3 travel_search.py advisories
"""
import argparse
import json
import os
import ssl
import sys
import urllib.request
import urllib.error
from datetime import datetime

# ─── Config ──────────────────────────────────────────────────────────────────
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")
FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"
TIMEOUT = 45  # seconds per request


def log(msg):
    """Print to stderr so stdout stays clean JSON."""
    print(msg, file=sys.stderr)


def alexandria(provider: str, capability: str, options: dict) -> dict:
    """Call a single Firecrawl Alexandria provider. Returns parsed JSON response."""
    if not FIRECRAWL_API_KEY:
        log("ERROR: FIRECRAWL_API_KEY not set in environment")
        return {"error": "FIRECRAWL_API_KEY not set"}

    payload = json.dumps({
        "alexandria": {
            "provider": provider,
            "capability": capability,
            "options": options
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{FIRECRAWL_BASE}/scrape",
        data=payload,
        headers={
            "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        log(f"Alexandria HTTP {e.code}: {body[:500]}")
        return {"error": f"HTTP {e.code}", "detail": body[:500]}
    except urllib.error.URLError as e:
        log(f"Alexandria connection error: {e.reason}")
        return {"error": str(e.reason)}
    except Exception as e:
        log(f"Alexandria error: {e}")
        return {"error": str(e)}


def scrape_url(url: str, extract_schema: dict = None) -> dict:
    """Fallback: scrape a URL directly with optional JSON extraction schema."""
    if not FIRECRAWL_API_KEY:
        return {"error": "FIRECRAWL_API_KEY not set"}

    body = {"url": url, "formats": ["markdown"]}
    if extract_schema:
        body["formats"] = ["extract"]
        body["jsonOptions"] = {"schema": extract_schema}

    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{FIRECRAWL_BASE}/scrape",
        data=payload,
        headers={
            "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log(f"Scrape fallback error: {e}")
        return {"error": str(e)}


# ─── Extractors ──────────────────────────────────────────────────────────────
# These pull structured results out of raw Alexandria responses.

def extract_data(resp: dict) -> list | dict | None:
    """Walk common Alexandria response shapes and return the payload."""
    if "error" in resp:
        return None
    # typical: resp -> data -> extract / alexandria / content
    data = resp.get("data", resp)
    if isinstance(data, dict):
        for key in ("extract", "alexandria", "results", "data", "content"):
            if key in data and data[key]:
                return data[key]
    return data


# ─── Hotel search ────────────────────────────────────────────────────────────

def search_hotels(args):
    destination = args.destination
    checkin = args.checkin
    checkout = args.checkout
    adults = getattr(args, "adults", 2)

    results = []

    # ── Booking.com ──────────────────────────────────────────────────────
    log(f"Resolving destination on Booking.com: {destination}")
    loc = alexandria("booking-com", "hotels/locations", {"query": destination})
    loc_data = extract_data(loc)

    dest_id = None
    dest_type = "CITY"
    if loc_data:
        if isinstance(loc_data, list) and len(loc_data) > 0:
            first = loc_data[0]
            dest_id = first.get("dest_id") or first.get("id")
            dest_type = first.get("dest_type", "CITY")
        elif isinstance(loc_data, dict):
            dest_id = loc_data.get("dest_id") or loc_data.get("id")
            dest_type = loc_data.get("dest_type", "CITY")

    if dest_id:
        log(f"Searching Booking.com (dest_id={dest_id})...")
        search = alexandria("booking-com", "hotels/search", {
            "dest_id": str(dest_id),
            "dest_type": dest_type,
            "checkin": checkin,
            "checkout": checkout,
            "adults": adults,
            "sort": "review_score"
        })
        hotels = extract_data(search)
        if hotels and isinstance(hotels, list):
            for h in hotels[:10]:
                results.append({
                    "name": h.get("name", h.get("hotel_name", "Unknown")),
                    "source": "Booking.com",
                    "price_per_night": h.get("price_per_night") or h.get("min_total_price") or h.get("price"),
                    "total_price": h.get("total_price") or h.get("min_total_price"),
                    "rating": h.get("review_score") or h.get("rating"),
                    "type": h.get("accommodation_type_name") or h.get("type", ""),
                    "url": h.get("url") or h.get("link", ""),
                    "features": h.get("facilities", []) or [],
                    "address": h.get("address", ""),
                    "hotel_id": h.get("hotel_id") or h.get("id")
                })
        elif hotels and isinstance(hotels, dict):
            # Sometimes results are nested
            for key in ("hotels", "results", "properties"):
                if key in hotels and isinstance(hotels[key], list):
                    for h in hotels[key][:10]:
                        results.append({
                            "name": h.get("name", "Unknown"),
                            "source": "Booking.com",
                            "price_per_night": h.get("price_per_night") or h.get("price"),
                            "total_price": h.get("total_price"),
                            "rating": h.get("review_score") or h.get("rating"),
                            "type": h.get("accommodation_type_name", ""),
                            "url": h.get("url", ""),
                            "features": h.get("facilities", []),
                            "address": h.get("address", ""),
                            "hotel_id": h.get("hotel_id") or h.get("id")
                        })
                    break
    else:
        log("Booking.com: could not resolve destination")

    # ── Vrbo ─────────────────────────────────────────────────────────────
    log(f"Resolving destination on Vrbo: {destination}")
    vrbo_loc = alexandria("vrbo-com", "vacation-rentals/suggest_destinations", {"query": destination})
    vrbo_loc_data = extract_data(vrbo_loc)

    region_id = None
    if vrbo_loc_data:
        if isinstance(vrbo_loc_data, list) and len(vrbo_loc_data) > 0:
            region_id = vrbo_loc_data[0].get("region_id") or vrbo_loc_data[0].get("id")
        elif isinstance(vrbo_loc_data, dict):
            region_id = vrbo_loc_data.get("region_id") or vrbo_loc_data.get("id")

    if region_id:
        log(f"Searching Vrbo (region_id={region_id})...")
        vrbo_search = alexandria("vrbo-com", "vacation-rentals/search", {
            "region_id": str(region_id),
            "checkin": checkin,
            "checkout": checkout,
            "adults": adults
        })
        rentals = extract_data(vrbo_search)
        if rentals and isinstance(rentals, list):
            for r in rentals[:10]:
                results.append({
                    "name": r.get("name") or r.get("title", "Unknown"),
                    "source": "Vrbo",
                    "price_per_night": r.get("price_per_night") or r.get("nightly_rate") or r.get("price"),
                    "total_price": r.get("total_price") or r.get("total"),
                    "rating": r.get("rating") or r.get("review_score"),
                    "type": r.get("property_type", "Rental"),
                    "url": r.get("url") or r.get("link", ""),
                    "features": r.get("amenities", []) or [],
                    "address": r.get("address", ""),
                    "listing_id": r.get("listing_id") or r.get("id")
                })
        elif rentals and isinstance(rentals, dict):
            for key in ("listings", "results", "properties"):
                if key in rentals and isinstance(rentals[key], list):
                    for r in rentals[key][:10]:
                        results.append({
                            "name": r.get("name") or r.get("title", "Unknown"),
                            "source": "Vrbo",
                            "price_per_night": r.get("price_per_night") or r.get("price"),
                            "total_price": r.get("total_price"),
                            "rating": r.get("rating"),
                            "type": r.get("property_type", "Rental"),
                            "url": r.get("url", ""),
                            "features": r.get("amenities", []),
                            "address": r.get("address", ""),
                            "listing_id": r.get("listing_id") or r.get("id")
                        })
                    break
    else:
        log("Vrbo: could not resolve destination")

    # Sort by price
    results.sort(key=lambda x: x.get("price_per_night") or x.get("total_price") or 999999)

    return {
        "status": "ok",
        "search_type": "hotels",
        "result_count": len(results),
        "results": results,
        "query": {
            "destination": destination,
            "checkin": checkin,
            "checkout": checkout,
            "adults": adults
        }
    }


# ─── Flight search ───────────────────────────────────────────────────────────

def search_flights(args):
    origin = args.origin
    destination = args.destination
    departure = args.departure
    return_date = getattr(args, "return_date", None)
    adults = getattr(args, "adults", 1)

    results = []

    # ── Google Flights ───────────────────────────────────────────────────
    log(f"Resolving airports on Google Flights...")
    orig_resp = alexandria("flights-google-com", "flights/suggest_places", {"query": origin})
    dest_resp = alexandria("flights-google-com", "flights/suggest_places", {"query": destination})

    orig_data = extract_data(orig_resp)
    dest_data = extract_data(dest_resp)

    orig_code = _extract_airport_code(orig_data, origin)
    dest_code = _extract_airport_code(dest_data, destination)

    if orig_code and dest_code:
        log(f"Searching Google Flights: {orig_code} → {dest_code}")
        opts = {
            "origin": orig_code,
            "destination": dest_code,
            "departure_date": departure,
            "adults": adults,
            "limit": 8
        }
        if return_date:
            opts["return_date"] = return_date

        gf = alexandria("flights-google-com", "flights/search_flights", opts)
        flights = extract_data(gf)
        results.extend(_parse_flights(flights, "Google Flights"))
    else:
        log(f"Google Flights: could not resolve airports (origin={orig_code}, dest={dest_code})")

    # ── Skyscanner ───────────────────────────────────────────────────────
    log(f"Resolving airports on Skyscanner...")
    sk_orig = alexandria("skyscanner-net", "flights/suggest_places", {"query": origin})
    sk_dest = alexandria("skyscanner-net", "flights/suggest_places", {"query": destination})

    sk_orig_data = extract_data(sk_orig)
    sk_dest_data = extract_data(sk_dest)

    sk_orig_id = _extract_skyscanner_id(sk_orig_data)
    sk_dest_id = _extract_skyscanner_id(sk_dest_data)

    if sk_orig_id and sk_dest_id:
        log(f"Searching Skyscanner: {sk_orig_id} → {sk_dest_id}")
        opts = {
            "origin_entity_id": sk_orig_id,
            "destination_entity_id": sk_dest_id,
            "outbound_date": departure,
            "adults": adults,
            "sort": "cheapest",
            "max_results": 8
        }
        if return_date:
            opts["inbound_date"] = return_date

        sk = alexandria("skyscanner-net", "flights/search_flights", opts)
        flights = extract_data(sk)
        results.extend(_parse_flights(flights, "Skyscanner"))
    else:
        log(f"Skyscanner: could not resolve airports (origin={sk_orig_id}, dest={sk_dest_id})")

    results.sort(key=lambda x: x.get("price") or 999999)

    return {
        "status": "ok",
        "search_type": "flights",
        "result_count": len(results),
        "results": results,
        "query": {
            "origin": origin,
            "destination": destination,
            "departure": departure,
            "return": return_date,
            "adults": adults
        }
    }


def _extract_airport_code(data, fallback_query):
    """Pull an IATA airport code from suggest_places response."""
    if not data:
        return None
    if isinstance(data, list) and len(data) > 0:
        item = data[0]
        return item.get("iata") or item.get("code") or item.get("skyId") or item.get("id")
    if isinstance(data, dict):
        for key in ("iata", "code", "skyId", "id", "airport_code"):
            if key in data:
                return data[key]
        # nested
        if "airports" in data and isinstance(data["airports"], list) and data["airports"]:
            return data["airports"][0].get("iata") or data["airports"][0].get("code")
    return None


def _extract_skyscanner_id(data):
    """Pull entity_id from Skyscanner suggest_places response."""
    if not data:
        return None
    if isinstance(data, list) and len(data) > 0:
        item = data[0]
        return item.get("entity_id") or item.get("entityId") or item.get("id")
    if isinstance(data, dict):
        for key in ("entity_id", "entityId", "id"):
            if key in data:
                return data[key]
        if "places" in data and isinstance(data["places"], list) and data["places"]:
            return data["places"][0].get("entity_id") or data["places"][0].get("entityId")
    return None


def _parse_flights(data, source):
    """Parse flight results from either Google or Skyscanner."""
    results = []
    if not data:
        return results

    items = data
    if isinstance(data, dict):
        for key in ("flights", "results", "itineraries", "quotes"):
            if key in data and isinstance(data[key], list):
                items = data[key]
                break
        else:
            return results

    if not isinstance(items, list):
        return results

    for f in items[:10]:
        results.append({
            "route": f.get("route") or f"{f.get('origin', '?')} → {f.get('destination', '?')}",
            "airline": f.get("airline") or f.get("carrier") or f.get("carriers", ""),
            "stops": f.get("stops") if f.get("stops") is not None else f.get("num_stops", "?"),
            "duration": f.get("duration") or f.get("total_duration", ""),
            "price": f.get("price") or f.get("raw_price") or f.get("min_price"),
            "currency": f.get("currency", "USD"),
            "departure_time": f.get("departure_time") or f.get("depart_time", ""),
            "arrival_time": f.get("arrival_time") or f.get("arrive_time", ""),
            "url": f.get("url") or f.get("link", ""),
            "source": source
        })
    return results


# ─── Flight price calendar ───────────────────────────────────────────────────

def flight_calendar(args):
    origin = args.origin
    destination = args.destination

    log(f"Resolving Skyscanner places for calendar...")
    sk_orig = alexandria("skyscanner-net", "flights/suggest_places", {"query": origin})
    sk_dest = alexandria("skyscanner-net", "flights/suggest_places", {"query": destination})

    sk_orig_data = extract_data(sk_orig)
    sk_dest_data = extract_data(sk_dest)

    # For price_calendar, Skyscanner uses place_id (e.g. "MKCA") not entity_id
    orig_place = _extract_skyscanner_place_id(sk_orig_data)
    dest_place = _extract_skyscanner_place_id(sk_dest_data)
    orig_entity = _extract_skyscanner_id(sk_orig_data)
    dest_entity = _extract_skyscanner_id(sk_dest_data)

    results = {}

    # Monthly overview
    if orig_entity and dest_entity:
        log(f"Fetching monthly prices...")
        monthly = alexandria("skyscanner-net", "flights/monthly_prices", {
            "origin_entity_id": orig_entity,
            "destination_entity_id": dest_entity
        })
        results["monthly"] = extract_data(monthly)

    # Daily calendar
    if orig_place and dest_place:
        log(f"Fetching price calendar ({orig_place} → {dest_place})...")
        cal = alexandria("skyscanner-net", "flights/price_calendar", {
            "origin": orig_place,
            "destination": dest_place,
            "max_days": getattr(args, "max_days", 90)
        })
        results["daily"] = extract_data(cal)

    return {
        "status": "ok",
        "search_type": "flight_calendar",
        "results": results,
        "query": {"origin": origin, "destination": destination}
    }


def _extract_skyscanner_place_id(data):
    """Pull place_id (like 'MKCA') from Skyscanner suggest response."""
    if not data:
        return None
    if isinstance(data, list) and len(data) > 0:
        return data[0].get("place_id") or data[0].get("skyId") or data[0].get("iata")
    if isinstance(data, dict):
        for key in ("place_id", "skyId", "iata"):
            if key in data:
                return data[key]
        if "places" in data and isinstance(data["places"], list) and data["places"]:
            return data["places"][0].get("place_id") or data["places"][0].get("skyId")
    return None


# ─── Car rental search ───────────────────────────────────────────────────────

def search_cars(args):
    log(f"Searching Turo at ({args.latitude}, {args.longitude})...")
    resp = alexandria("turo-com", "car-rentals/search", {
        "latitude": float(args.latitude),
        "longitude": float(args.longitude),
        "start": args.start,
        "end": args.end,
        "sort": "PRICE_LOW",
        "limit": 10
    })
    data = extract_data(resp)

    results = []
    items = data if isinstance(data, list) else (data.get("vehicles") or data.get("results") or []) if isinstance(data, dict) else []

    for v in items[:10]:
        results.append({
            "name": f"{v.get('year', '')} {v.get('make', '')} {v.get('model', '')}".strip() or v.get("name", "Unknown"),
            "source": "Turo",
            "daily_rate": v.get("daily_rate") or v.get("rate") or v.get("price"),
            "total_price": v.get("total_price") or v.get("total"),
            "rating": v.get("rating"),
            "trips": v.get("trips") or v.get("trip_count"),
            "url": v.get("url", ""),
            "features": v.get("features", [])
        })

    return {
        "status": "ok",
        "search_type": "cars",
        "result_count": len(results),
        "results": results,
        "query": {
            "latitude": args.latitude,
            "longitude": args.longitude,
            "start": args.start,
            "end": args.end
        }
    }


# ─── Travel advisories ──────────────────────────────────────────────────────

def search_advisories(args):
    log("Fetching travel advisories...")
    resp = alexandria("travel-state-gov", "advisories/countries", {})
    data = extract_data(resp)

    country = getattr(args, "country", None)
    if country and data and isinstance(data, list):
        data = [a for a in data if country.lower() in json.dumps(a).lower()]

    return {
        "status": "ok",
        "search_type": "advisories",
        "results": data or [],
        "query": {"country": country}
    }


# ─── Events search ──────────────────────────────────────────────────────────

def search_events(args):
    log(f"Searching events: {args.query} near {args.location}...")
    resp = alexandria("seatgeek-com", "events/search", {
        "query": args.query,
        "location": args.location,
        "per_page": 10
    })
    data = extract_data(resp)

    results = []
    items = data if isinstance(data, list) else (data.get("events") or data.get("results") or []) if isinstance(data, dict) else []

    for e in items[:10]:
        results.append({
            "name": e.get("title") or e.get("name", "Unknown"),
            "source": "SeatGeek",
            "date": e.get("datetime_local") or e.get("date", ""),
            "venue": e.get("venue", {}).get("name", "") if isinstance(e.get("venue"), dict) else e.get("venue", ""),
            "price_min": e.get("stats", {}).get("lowest_price") if isinstance(e.get("stats"), dict) else e.get("min_price"),
            "price_max": e.get("stats", {}).get("highest_price") if isinstance(e.get("stats"), dict) else e.get("max_price"),
            "url": e.get("url", ""),
            "type": e.get("type", "")
        })

    return {
        "status": "ok",
        "search_type": "events",
        "result_count": len(results),
        "results": results,
        "query": {"query": args.query, "location": args.location}
    }


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Real-time travel search via Firecrawl Alexandria",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 travel_search.py hotels --destination "Hermann, Missouri" --checkin 2026-11-15 --checkout 2026-11-17
  python3 travel_search.py flights --origin "Kansas City" --destination "Tokyo" --departure 2026-03-15
  python3 travel_search.py flight-calendar --origin "Kansas City" --destination "Los Angeles"
  python3 travel_search.py cars --latitude 38.7046 --longitude -90.3882 --start 2026-11-15T10:00 --end 2026-11-17T10:00
  python3 travel_search.py events --query "concerts" --location "Kansas City"
  python3 travel_search.py advisories --country Japan"""
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # hotels
    h = sub.add_parser("hotels", help="Search hotels and vacation rentals")
    h.add_argument("--destination", required=True)
    h.add_argument("--checkin", required=True, help="YYYY-MM-DD")
    h.add_argument("--checkout", required=True, help="YYYY-MM-DD")
    h.add_argument("--adults", type=int, default=2)

    # flights
    f = sub.add_parser("flights", help="Search flights across providers")
    f.add_argument("--origin", required=True)
    f.add_argument("--destination", required=True)
    f.add_argument("--departure", required=True, help="YYYY-MM-DD")
    f.add_argument("--return-date", dest="return_date", help="YYYY-MM-DD")
    f.add_argument("--adults", type=int, default=1)

    # flight-calendar
    fc = sub.add_parser("flight-calendar", help="Cheapest dates calendar")
    fc.add_argument("--origin", required=True)
    fc.add_argument("--destination", required=True)
    fc.add_argument("--max-days", dest="max_days", type=int, default=90)

    # cars
    c = sub.add_parser("cars", help="Search rental cars on Turo")
    c.add_argument("--latitude", required=True, type=float)
    c.add_argument("--longitude", required=True, type=float)
    c.add_argument("--start", required=True, help="ISO datetime")
    c.add_argument("--end", required=True, help="ISO datetime")

    # events
    e = sub.add_parser("events", help="Search events on SeatGeek")
    e.add_argument("--query", required=True)
    e.add_argument("--location", required=True)

    # advisories
    a = sub.add_parser("advisories", help="Get travel advisories")
    a.add_argument("--country", default=None)

    args = parser.parse_args()

    dispatch = {
        "hotels": search_hotels,
        "flights": search_flights,
        "flight-calendar": flight_calendar,
        "cars": search_cars,
        "events": search_events,
        "advisories": search_advisories,
    }

    handler = dispatch.get(args.command)
    if not handler:
        log(f"Unknown command: {args.command}")
        sys.exit(1)

    try:
        result = handler(args)
    except Exception as exc:
        result = {"status": "error", "error": str(exc), "search_type": args.command}
        log(f"Fatal error: {exc}")

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
