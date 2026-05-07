"""API handler: serves flight data, spotlight, and community cities."""
import json
import os
import time
import urllib.request
from decimal import Decimal

import boto3

TABLE_NAME = os.environ["TABLE_NAME"]
SECRET_NAME = os.environ.get("SECRET_NAME", "skywatch/api-keys")
MODEL_ID = os.environ.get("MODEL_ID", "")
FLIGHTAWARE_URL = "https://aeroapi.flightaware.com/aeroapi"

ddb = boto3.resource("dynamodb")
table = ddb.Table(TABLE_NAME)
bedrock = boto3.client("bedrock-runtime")
secrets_client = boto3.client("secretsmanager")

# Cache secrets in memory for Lambda reuse
_secrets_cache = None


def get_secrets():
    global _secrets_cache
    if _secrets_cache is None:
        resp = secrets_client.get_secret_value(SecretId=SECRET_NAME)
        _secrets_cache = json.loads(resp["SecretString"])
    return _secrets_cache


def get_flightaware_key():
    return get_secrets().get("FLIGHTAWARE_API_KEY", "")


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def handler(event, context):
    path = event.get("rawPath", "")
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")

    if method == "OPTIONS":
        return response(200, {})

    if path == "/flights":
        return get_flights()
    elif path == "/spotlight" and method == "POST":
        return generate_spotlight(event)
    elif path == "/spotlight":
        return get_spotlight()
    elif path.startswith("/flight/"):
        callsign = event.get("pathParameters", {}).get("callsign", "")
        return get_flight_info(callsign)
    elif path == "/community" and method == "POST":
        return add_community_city(event)
    elif path == "/community" and method == "DELETE":
        return clear_community()
    elif path == "/community" and method == "GET":
        return get_community_cities()
    else:
        return response(404, {"error": "Not found"})


def get_flights():
    cutoff = int(time.time()) - 90  # Only flights updated in the last 90s
    resp = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("pk").eq("FLIGHT"),
        FilterExpression=boto3.dynamodb.conditions.Attr("updated").gte(cutoff),
    )
    flights = resp.get("Items", [])
    return response(200, {"flights": flights, "count": len(flights)})


def get_spotlight():
    try:
        resp = table.get_item(Key={"pk": "SPOTLIGHT", "sk": "current"})
        item = resp.get("Item", {})
        return response(200, {"text": item.get("text", ""), "icao24": item.get("icao24", ""), "updated": item.get("updated", 0)})
    except Exception:
        return response(200, {"text": "", "updated": 0})


def generate_spotlight(event):
    """Generate an AI blurb for a user-selected flight."""
    try:
        body = json.loads(event.get("body", "{}"))
    except (json.JSONDecodeError, TypeError):
        return response(400, {"error": "Invalid JSON"})

    callsign = body.get("callsign", "").strip()
    icao24 = body.get("icao24", "")
    flight_info = body.get("flight_info", {})

    if not callsign:
        return response(400, {"error": "callsign required"})

    # Build context for Claude
    details = []
    if flight_info.get("operator"):
        details.append(f"Operator: {flight_info['operator']}")
    if flight_info.get("route"):
        details.append(f"Route: {flight_info['route']}")
    if flight_info.get("aircraft_type"):
        details.append(f"Aircraft: {flight_info['aircraft_type']}")
    if flight_info.get("status"):
        details.append(f"Status: {flight_info['status']}")
    if body.get("altitude"):
        details.append(f"Altitude: {body['altitude']}m")
    if body.get("velocity"):
        details.append(f"Speed: {body['velocity']}m/s")
    if body.get("country"):
        details.append(f"Country: {body['country']}")

    details_text = "\n".join(details) if details else "No additional info available"

    prompt = f"""You are an enthusiastic aviation spotter narrating a live flight tracker at PyCon in Long Beach, California.
A viewer just clicked on this flight:

Callsign: {callsign}
{details_text}

Write exactly one punchy, fun sentence about this flight that would make a conference attendee say "cool!"
Be specific — mention the airline, destination, aircraft type, or any interesting fact.
Respond with ONLY the sentence, starting with "✨ Spotted:"
"""

    try:
        resp = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 150,
                "messages": [{"role": "user", "content": prompt}],
            }),
        )
        result = json.loads(resp["body"].read())
        text = result["content"][0]["text"].strip()
    except Exception as e:
        text = f"✨ Spotted: {callsign} — {flight_info.get('route', 'flying overhead')}!"

    # Store spotlight
    table.put_item(Item={
        "pk": "SPOTLIGHT",
        "sk": "current",
        "text": text,
        "icao24": icao24,
        "updated": int(time.time()),
        "ttl": int(time.time()) + 300,
    })

    return response(200, {"text": text, "icao24": icao24})


def add_community_city(event):
    try:
        body = json.loads(event.get("body", "{}"))
    except (json.JSONDecodeError, TypeError):
        return response(400, {"error": "Invalid JSON"})

    city = body.get("city", "").strip()
    lat = body.get("lat")
    lon = body.get("lon")

    if not city or lat is None or lon is None:
        return response(400, {"error": "city, lat, lon required"})

    table.put_item(Item={
        "pk": "COMMUNITY",
        "sk": city.lower().replace(" ", "-"),
        "city": city,
        "latitude": Decimal(str(lat)),
        "longitude": Decimal(str(lon)),
        "added": int(time.time()),
        "ttl": int(time.time()) + 604800,  # 7 day TTL
    })

    return response(200, {"message": f"Added {city}"})


def get_community_cities():
    resp = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("pk").eq("COMMUNITY"),
    )
    cities = resp.get("Items", [])
    return response(200, {"cities": cities, "count": len(cities)})


def clear_community():
    resp = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("pk").eq("COMMUNITY"),
    )
    with table.batch_writer() as batch:
        for item in resp.get("Items", []):
            batch.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})
    return response(200, {"message": "Community cleared"})


def get_flight_info(callsign):
    """Look up flight details from cache or FlightAware AeroAPI."""
    callsign = callsign.strip().upper()
    if not callsign:
        return response(400, {"error": "callsign required"})

    # Check cache first (1 hour TTL)
    try:
        cached = table.get_item(Key={"pk": "FLIGHTINFO", "sk": callsign})
        item = cached.get("Item")
        if item and item.get("ttl", 0) > int(time.time()):
            return response(200, json.loads(item["data"]))
    except Exception:
        pass

    # Call FlightAware AeroAPI
    api_key = get_flightaware_key()
    if not api_key:
        return response(200, {"callsign": callsign, "error": "FlightAware not configured"})

    try:
        url = f"{FLIGHTAWARE_URL}/flights/{callsign}"
        req = urllib.request.Request(url, headers={
            "x-apikey": api_key,
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=5) as resp_fa:
            fa_data = json.loads(resp_fa.read())
    except Exception as e:
        return response(200, {"callsign": callsign, "error": f"FlightAware lookup failed: {e}"})

    # Find the most relevant flight (in-progress or most recent)
    flights = fa_data.get("flights", [])
    if not flights:
        result = {"callsign": callsign, "error": "No flight data found"}
        return response(200, result)

    # Prefer en route flights, fall back to most recent
    flight = next((f for f in flights if f.get("status", "").startswith("En Route")), flights[0])

    origin = flight.get("origin") or {}
    destination = flight.get("destination") or {}
    origin_label = origin.get("code_iata") or origin.get("city") or "?"
    dest_label = destination.get("code_iata") or destination.get("city") or "?"

    result = {
        "callsign": callsign,
        "operator": flight.get("operator") or "",
        "flight_number": flight.get("flight_number") or "",
        "aircraft_type": flight.get("aircraft_type") or "",
        "origin": origin,
        "destination": destination,
        "status": flight.get("status") or "",
        "route": f"{origin_label} → {dest_label}",
    }

    # Cache for 1 hour
    table.put_item(Item={
        "pk": "FLIGHTINFO",
        "sk": callsign,
        "data": json.dumps(result),
        "ttl": int(time.time()) + 3600,
    })

    return response(200, result)


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
        "body": json.dumps(body, cls=DecimalEncoder),
    }
