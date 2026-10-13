#!/usr/bin/env python3
"""
travel_search.py — Real-time travel search via Firecrawl direct URL scraping.
Works on the FREE Firecrawl plan (no Alexandria needed).
Called by Allie's travel-bot via `terminal`. Zero external dependencies (stdlib only).

Usage:
    python3 travel_search.py hotels --destination "Hermann, Missouri" --checkin 2026-11-15 --checkout 2026-11-17
    python3 travel_search.py flights --origin "Kansas City" --destination "Tokyo" --departure 2026-03-15 --return 2026-03-25
    python3 travel_search.py cars --destination "Hermann, Missouri" --start 2026-11-15 --end 2026-11-17
    python3 travel_search.py events --query "concerts" --location "Kansas City"
"""
import argparse
import json
import os
import re
import ssl
import sys
import urllib.request
import urllib.error
import urllib.parse

# ─── Config ──────────────────────────────────────────────────────────────────
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")
FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"
TIMEOUT = 60  # seconds per request


def log(msg):
    """Print to stderr so stdout stays clean JSON."""
    print(msg, file=sys.stderr)


# ─── Firecrawl API helpers ───────────────────────────────────────────────────

def firecrawl_scrape(url: str, extract_schema: dict = None, extract_prompt: str = None) -> dict:
    """Scrape a URL using Firecrawl's /v1/scrape endpoint.
    Optionally extract structured data with a JSON schema or prompt.
    Works on the FREE Firecrawl plan.
    """
    if not FIRECRAWL_API_KEY:
        log("ERROR: FIRECRAWL_API_KEY not set in environment")
        return {"error": "FIRECRAWL_API_KEY not set"}

    body = {"url": url}

    if extract_schema or extract_prompt:
        body["formats"] = ["extract"]
        extract_opts = {}
        if extract_schema:
            extract_opts["schema"] = extract_schema
        if extract_prompt:
            extract_opts["prompt"] = extract_prompt
        body["extract"] = extract_opts
    else:
        body["formats"] = ["markdown"]

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
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        log(f"Firecrawl HTTP {e.code}: {body_text[:500]}")
        return {"error": f"HTTP {e.code}", "detail": body_text[:500]}
    except urllib.error.URLError as e:
        log(f"Firecrawl connection error: {e.reason}")
        return {"error": str(e.reason)}
    except Exception as e:
        log(f"Firecrawl error: {e}")
        return {"error": str(e)}


def firecrawl_search(query: str, limit: int = 5) -> dict:
    """Search the web using Firecrawl's /v1/search endpoint."""
    if not FIRECRAWL_API_KEY:
        return {"error": "FIRECRAWL_API_KEY not set"}

    payload = json.dumps({
        "query": query,
        "limit": limit,
        "scrapeOptions": {"formats": ["markdown"]}
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{FIRECRAWL_BASE}/search",
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
        body_text = e.read().decode("utf-8", errors="replace")
        log(f"Firecrawl search HTTP {e.code}: {body_text[:300]}")
        return {"error": f"HTTP {e.code}", "detail": body_text[:300]}
    except Exception as e:
        log(f"Firecrawl search error: {e}")
        return {"error": str(e)}


# ─── Extraction schemas ─────────────────────────────────────────────────────

HOTEL_SCHEMA = {
    "type": "object",
    "properties": {
        "hotels": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "price_per_night": {"type": "number"},
                    "total_price": {"type": "number"},
                    "currency": {"type": "string"},
                    "rating": {"type": "number"},
                    "review_count": {"type": "integer"},
                    "type": {"type": "string"},
                    "address": {"type": "string"},
                    "features": {"type": "array", "items": {"type": "string"}},
                    "url": {"type": "string"},
                    "image_url": {"type": "string"}
                }
            }
        }
    }
}

FLIGHT_SCHEMA = {
    "type": "object",
    "properties": {
        "flights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "airline": {"type": "string"},
                    "route": {"type": "string"},
                    "departure_time": {"type": "string"},
                    "arrival_time": {"type": "string"},
                    "duration": {"type": "string"},
                    "stops": {"type": "integer"},
                    "price": {"type": "number"},
                    "currency": {"type": "string"},
                    "cabin_class": {"type": "string"},
                    "booking_url": {"type": "string"}
                }
            }
        }
    }
}

CAR_SCHEMA = {
    "type": "object",
    "properties": {
        "cars": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "vehicle_type": {"type": "string"},
                    "daily_rate": {"type": "number"},
                    "total_price": {"type": "number"},
                    "currency": {"type": "string"},
                    "rating": {"type": "number"},
                    "trips": {"type": "integer"},
                    "features": {"type": "array", "items": {"type": "string"}},
                    "url": {"type": "string"}
                }
            }
        }
    }
}

EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                    "venue": {"type": "string"},
                    "price_min": {"type": "number"},
                    "price_max": {"type": "number"},
                    "currency": {"type": "string"},
                    "category": {"type": "string"},
                    "url": {"type": "string"}
                }
            }
        }
    }
}


# ─── URL builders ────────────────────────────────────────────────────────────

def booking_search_url(destination: str, checkin: str, checkout: str, adults: int = 2) -> str:
    params = urllib.parse.urlencode({
        "ss": destination,
        "checkin": checkin,
        "checkout": checkout,
        "group_adults": adults,
        "no_rooms": 1,
        "group_children": 0
    })
    return f"https://www.booking.com/searchresults.html?{params}"


def google_flights_url(origin: str, destination: str, departure: str, return_date: str = None, adults: int = 1) -> str:
    """Build a Google Flights explore URL. Note: Google Flights uses JS heavily,
    so we scrape the search results page with a prompt-based extraction."""
    params = {
        "q": f"flights from {origin} to {destination} on {departure}",
    }
    if return_date:
        params["q"] += f" returning {return_date}"
    return f"https://www.google.com/search?{urllib.parse.urlencode(params)}&tbm=flg"


def kayak_flights_url(origin: str, destination: str, departure: str, return_date: str = None) -> str:
    path = f"{origin}-{destination}/{departure}"
    if return_date:
        path += f"/{return_date}"
    return f"https://www.kayak.com/flights/{path}?sort=price_a"


def turo_search_url(destination: str, start: str, end: str) -> str:
    params = urllib.parse.urlencode({
        "location": destination,
        "startDate": start,
        "endDate": end,
        "sortType": "PRICE",
        "sortDirection": "ASC"
    })
    return f"https://turo.com/us/en/search?{params}"


def seatgeek_search_url(query: str, location: str) -> str:
    q = f"{query} {location}".strip()
    return f"https://seatgeek.com/search?search={urllib.parse.quote(q)}"


# ─── Search functions ────────────────────────────────────────────────────────

def search_hotels(args):
    destination = args.destination
    checkin = args.checkin
    checkout = args.checkout
    adults = getattr(args, "adults", 2)

    results = []

    # ── Strategy 1: Scrape Booking.com search results ────────────────────
    log(f"Scraping Booking.com for: {destination}")
    booking_url = booking_search_url(destination, checkin, checkout, adults)
    log(f"URL: {booking_url}")

    booking_resp = firecrawl_scrape(
        booking_url,
        extract_schema=HOTEL_SCHEMA,
        extract_prompt=f"Extract all hotel/accommodation listings from this Booking.com search results page. For each property, get the name, price per night, total price, rating score, number of reviews, property type, address, key features/amenities, and booking URL."
    )

    booking_data = _extract_response(booking_resp)
    if booking_data and isinstance(booking_data, dict) and "hotels" in booking_data:
        for h in booking_data["hotels"][:10]:
            h["source"] = "Booking.com"
            results.append(h)
    elif booking_data and isinstance(booking_data, list):
        for h in booking_data[:10]:
            h["source"] = "Booking.com"
            results.append(h)

    # ── Strategy 2: Firecrawl search for more options ────────────────────
    log(f"Searching web for vacation rentals in: {destination}")
    search_query = f"vacation rentals {destination} {checkin} to {checkout} prices"
    search_resp = firecrawl_search(search_query, limit=3)

    if search_resp and "data" in search_resp:
        for item in search_resp["data"][:3]:
            url = item.get("url", "")
            title = item.get("title", "")
            # Only scrape if it's from a known travel site
            if any(domain in url for domain in ["vrbo.com", "airbnb.com", "hotels.com", "tripadvisor.com"]):
                log(f"Scraping additional source: {url}")
                extra = firecrawl_scrape(
                    url,
                    extract_schema=HOTEL_SCHEMA,
                    extract_prompt="Extract hotel/accommodation listings with name, price, rating, type, and features."
                )
                extra_data = _extract_response(extra)
                if extra_data and isinstance(extra_data, dict) and "hotels" in extra_data:
                    source = _domain_to_source(url)
                    for h in extra_data["hotels"][:5]:
                        h["source"] = source
                        results.append(h)

    # ── Strategy 3: Google search fallback ───────────────────────────────
    if not results:
        log("No results from scraping. Trying Google search fallback...")
        fallback_query = f"best hotels bed and breakfast {destination} prices {checkin}"
        fallback_resp = firecrawl_search(fallback_query, limit=5)
        if fallback_resp and "data" in fallback_resp:
            for item in fallback_resp["data"]:
                results.append({
                    "name": item.get("title", "Unknown"),
                    "source": "Web Search",
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "price_per_night": None,
                    "rating": None,
                    "type": "Unknown"
                })

    # Sort by price (entries with prices first)
    results.sort(key=lambda x: x.get("price_per_night") or x.get("total_price") or 999999)

    return {
        "status": "ok" if results else "no_results",
        "search_type": "hotels",
        "result_count": len(results),
        "results": results,
        "query": {
            "destination": destination,
            "checkin": checkin,
            "checkout": checkout,
            "adults": adults,
            "booking_url": booking_url
        }
    }


def search_flights(args):
    origin = args.origin
    destination = args.destination
    departure = args.departure
    return_date = getattr(args, "return_date", None)
    adults = getattr(args, "adults", 1)

    results = []

    # ── Strategy 1: Scrape Google search for flight prices ───────────────
    log(f"Searching for flights: {origin} → {destination}")
    query = f"flights from {origin} to {destination} {departure}"
    if return_date:
        query += f" return {return_date}"
    query += f" {adults} passenger{'s' if adults > 1 else ''} cheapest"

    search_resp = firecrawl_search(query, limit=5)
    if search_resp and "data" in search_resp:
        for item in search_resp["data"]:
            url = item.get("url", "")
            if any(d in url for d in ["google.com/travel", "kayak.com", "skyscanner", "expedia.com", "cheapflights"]):
                log(f"Scraping flight source: {url}")
                flight_resp = firecrawl_scrape(
                    url,
                    extract_schema=FLIGHT_SCHEMA,
                    extract_prompt=f"Extract flight listings from {origin} to {destination} on {departure}. For each flight get airline, route, departure time, arrival time, duration, number of stops, price, and booking URL."
                )
                flight_data = _extract_response(flight_resp)
                if flight_data and isinstance(flight_data, dict) and "flights" in flight_data:
                    source = _domain_to_source(url)
                    for f in flight_data["flights"][:8]:
                        f["source"] = source
                        results.append(f)

    # ── Strategy 2: Scrape Kayak directly ────────────────────────────────
    if not results:
        # Try to build origin/dest airport codes from the search
        orig_code = _guess_airport_code(origin)
        dest_code = _guess_airport_code(destination)

        if orig_code and dest_code:
            kayak_url = kayak_flights_url(orig_code, dest_code, departure, return_date)
            log(f"Scraping Kayak: {kayak_url}")
            kayak_resp = firecrawl_scrape(
                kayak_url,
                extract_schema=FLIGHT_SCHEMA,
                extract_prompt=f"Extract all flight options from this Kayak search results page. Get airline, departure/arrival times, duration, stops, and price for each flight."
            )
            kayak_data = _extract_response(kayak_resp)
            if kayak_data and isinstance(kayak_data, dict) and "flights" in kayak_data:
                for f in kayak_data["flights"][:10]:
                    f["source"] = "Kayak"
                    results.append(f)

    # ── Strategy 3: Fallback to web search results ───────────────────────
    if not results:
        log("No structured flight data. Returning web search results...")
        fallback_query = f"cheapest flights {origin} to {destination} {departure} price"
        fallback_resp = firecrawl_search(fallback_query, limit=5)
        if fallback_resp and "data" in fallback_resp:
            for item in fallback_resp["data"]:
                results.append({
                    "name": item.get("title", "Unknown"),
                    "source": "Web Search",
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "price": None,
                    "airline": "See link"
                })

    results.sort(key=lambda x: x.get("price") or 999999)

    return {
        "status": "ok" if results else "no_results",
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


def search_cars(args):
    destination = args.destination
    start = args.start
    end = args.end

    results = []

    # ── Scrape Turo search ───────────────────────────────────────────────
    log(f"Searching Turo for cars near: {destination}")
    turo_url = turo_search_url(destination, start, end)
    log(f"URL: {turo_url}")

    turo_resp = firecrawl_scrape(
        turo_url,
        extract_schema=CAR_SCHEMA,
        extract_prompt=f"Extract all car rental listings from this Turo search page. For each car get the name (year make model), vehicle type, daily rate, total price, rating, number of trips, features, and listing URL."
    )
    turo_data = _extract_response(turo_resp)
    if turo_data and isinstance(turo_data, dict) and "cars" in turo_data:
        for c in turo_data["cars"][:10]:
            c["source"] = "Turo"
            results.append(c)

    # ── Fallback: web search ─────────────────────────────────────────────
    if not results:
        log("Turo scrape failed. Trying web search...")
        query = f"car rental {destination} {start} to {end} best prices"
        search_resp = firecrawl_search(query, limit=5)
        if search_resp and "data" in search_resp:
            for item in search_resp["data"]:
                results.append({
                    "name": item.get("title", "Unknown"),
                    "source": "Web Search",
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "daily_rate": None
                })

    return {
        "status": "ok" if results else "no_results",
        "search_type": "cars",
        "result_count": len(results),
        "results": results,
        "query": {"destination": destination, "start": start, "end": end}
    }


def search_events(args):
    query = args.query
    location = args.location

    results = []

    # ── Scrape SeatGeek ──────────────────────────────────────────────────
    log(f"Searching SeatGeek for: {query} in {location}")
    sg_url = seatgeek_search_url(query, location)

    sg_resp = firecrawl_scrape(
        sg_url,
        extract_schema=EVENT_SCHEMA,
        extract_prompt=f"Extract all event listings from this SeatGeek search page. For each event get the name, date, time, venue, minimum ticket price, maximum ticket price, category, and ticket URL."
    )
    sg_data = _extract_response(sg_resp)
    if sg_data and isinstance(sg_data, dict) and "events" in sg_data:
        for e in sg_data["events"][:10]:
            e["source"] = "SeatGeek"
            results.append(e)

    # ── Fallback: web search for events ──────────────────────────────────
    if not results:
        log("SeatGeek scrape failed. Trying web search...")
        search_query = f"{query} events {location} tickets prices"
        search_resp = firecrawl_search(search_query, limit=5)
        if search_resp and "data" in search_resp:
            for item in search_resp["data"]:
                results.append({
                    "name": item.get("title", "Unknown"),
                    "source": "Web Search",
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "price_min": None
                })

    return {
        "status": "ok" if results else "no_results",
        "search_type": "events",
        "result_count": len(results),
        "results": results,
        "query": {"query": query, "location": location}
    }


def search_advisories(args):
    country = getattr(args, "country", None) or "all"

    log(f"Fetching travel advisories for: {country}")
    query = f"US State Department travel advisory {country} 2026"
    search_resp = firecrawl_search(query, limit=3)

    results = []
    if search_resp and "data" in search_resp:
        for item in search_resp["data"]:
            url = item.get("url", "")
            if "travel.state.gov" in url or "state.gov" in url:
                # Scrape the official advisory page
                log(f"Scraping advisory: {url}")
                adv_resp = firecrawl_scrape(url)
                adv_data = adv_resp.get("data", {})
                results.append({
                    "title": item.get("title", ""),
                    "url": url,
                    "content": adv_data.get("markdown", adv_data.get("content", item.get("description", "")))[:2000],
                    "source": "travel.state.gov"
                })
            else:
                results.append({
                    "title": item.get("title", ""),
                    "url": url,
                    "content": item.get("description", ""),
                    "source": "Web Search"
                })

    return {
        "status": "ok" if results else "no_results",
        "search_type": "advisories",
        "results": results,
        "query": {"country": country}
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _extract_response(resp: dict):
    """Walk Firecrawl response to find extracted data."""
    if not resp or "error" in resp:
        return None
    data = resp.get("data", resp)
    if isinstance(data, dict):
        for key in ("extract", "json", "structured", "content"):
            if key in data and data[key]:
                return data[key]
    return data


def _domain_to_source(url: str) -> str:
    """Convert a URL to a human-readable source name."""
    domain_map = {
        "booking.com": "Booking.com",
        "vrbo.com": "Vrbo",
        "airbnb.com": "Airbnb",
        "hotels.com": "Hotels.com",
        "expedia.com": "Expedia",
        "tripadvisor.com": "TripAdvisor",
        "kayak.com": "Kayak",
        "skyscanner": "Skyscanner",
        "google.com": "Google",
        "turo.com": "Turo",
        "seatgeek.com": "SeatGeek",
    }
    for domain, name in domain_map.items():
        if domain in url:
            return name
    return "Web"


# Common airport codes for quick lookup
AIRPORT_CODES = {
    "kansas city": "MCI", "kc": "MCI",
    "los angeles": "LAX", "la": "LAX",
    "new york": "JFK", "nyc": "JFK",
    "chicago": "ORD",
    "san francisco": "SFO", "sf": "SFO",
    "dallas": "DFW",
    "denver": "DEN",
    "seattle": "SEA",
    "miami": "MIA",
    "atlanta": "ATL",
    "boston": "BOS",
    "washington": "DCA", "dc": "DCA",
    "las vegas": "LAS", "vegas": "LAS",
    "orlando": "MCO",
    "phoenix": "PHX",
    "minneapolis": "MSP",
    "detroit": "DTW",
    "honolulu": "HNL", "hawaii": "HNL",
    "tokyo": "NRT", "narita": "NRT", "haneda": "HND",
    "london": "LHR", "heathrow": "LHR",
    "paris": "CDG",
    "rome": "FCO",
    "cancun": "CUN",
    "mexico city": "MEX",
}


def _guess_airport_code(city: str) -> str | None:
    """Try to match a city name to an IATA code."""
    city_lower = city.lower().strip()
    # Direct match
    if city_lower in AIRPORT_CODES:
        return AIRPORT_CODES[city_lower]
    # Partial match
    for key, code in AIRPORT_CODES.items():
        if key in city_lower or city_lower in key:
            return code
    # If it looks like an airport code already (3 uppercase letters)
    if re.match(r'^[A-Z]{3}$', city.strip()):
        return city.strip()
    return None


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Real-time travel search via Firecrawl (free plan compatible)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 travel_search.py hotels --destination "Hermann, Missouri" --checkin 2026-11-15 --checkout 2026-11-17
  python3 travel_search.py flights --origin "Kansas City" --destination "Tokyo" --departure 2026-03-15
  python3 travel_search.py cars --destination "Hermann, Missouri" --start 2026-11-15 --end 2026-11-17
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

    # cars
    c = sub.add_parser("cars", help="Search rental cars")
    c.add_argument("--destination", required=True)
    c.add_argument("--start", required=True, help="YYYY-MM-DD")
    c.add_argument("--end", required=True, help="YYYY-MM-DD")

    # events
    e = sub.add_parser("events", help="Search events")
    e.add_argument("--query", required=True)
    e.add_argument("--location", required=True)

    # advisories
    a = sub.add_parser("advisories", help="Get travel advisories")
    a.add_argument("--country", default=None)

    args = parser.parse_args()

    dispatch = {
        "hotels": search_hotels,
        "flights": search_flights,
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
