#!/usr/bin/env python3
"""Seed DynamoDB with realistic flight data when OpenSky is down.

Usage:
    source .venv/bin/activate
    python scripts/seed_flights.py

Refreshes positions every 30s with slight drift to simulate movement.
"""
import json
import random
import time
from decimal import Decimal

import boto3

TABLE_NAME = "SkyWatch-Flights80E3986D-T8BJLAQX52QX"
REGION = "us-east-1"

# Realistic flights near Long Beach
FLIGHTS = [
    {"icao24": "a44168", "callsign": "UAL1979", "country": "United States", "lat": 33.947, "lng": -118.307, "alt": 411, "vel": 89, "hdg": 261, "vr": -3.9},
    {"icao24": "71be21", "callsign": "KAL011", "country": "Republic of Korea", "lat": 33.953, "lng": -118.397, "alt": 61, "vel": 65, "hdg": 263, "vr": -2.9},
    {"icao24": "394a18", "callsign": "AFR021", "country": "France", "lat": 33.932, "lng": -118.573, "alt": 1181, "vel": 133, "hdg": 262, "vr": 13.0},
    {"icao24": "a542d7", "callsign": "SWA1547", "country": "United States", "lat": 33.633, "lng": -118.389, "alt": 10805, "vel": 222, "hdg": 315, "vr": -5.2},
    {"icao24": "a445b0", "callsign": "DAL2533", "country": "United States", "lat": 33.782, "lng": -118.440, "alt": 9655, "vel": 237, "hdg": 316, "vr": 9.1},
    {"icao24": "a74505", "callsign": "DAL38", "country": "United States", "lat": 33.966, "lng": -118.261, "alt": 724, "vel": 91, "hdg": 264, "vr": -4.6},
    {"icao24": "a668ee", "callsign": "ASA760", "country": "United States", "lat": 33.530, "lng": -117.948, "alt": 1821, "vel": 142, "hdg": 223, "vr": 15.0},
    {"icao24": "ac0f93", "callsign": "SWA577", "country": "United States", "lat": 33.882, "lng": -118.366, "alt": 9784, "vel": 213, "hdg": 133, "vr": -8.5},
    {"icao24": "a12a80", "callsign": "UAL1001", "country": "United States", "lat": 33.940, "lng": -118.381, "alt": 38, "vel": 74, "hdg": 263, "vr": -3.6},
    {"icao24": "a403b3", "callsign": "DAL946", "country": "United States", "lat": 33.952, "lng": -118.400, "alt": 46, "vel": 64, "hdg": 263, "vr": -3.3},
    {"icao24": "a11380", "callsign": "DAL395", "country": "United States", "lat": 33.945, "lng": -118.451, "alt": 549, "vel": 87, "hdg": 264, "vr": 10.4},
    {"icao24": "aa4c87", "callsign": "UAL547", "country": "United States", "lat": 33.605, "lng": -117.988, "alt": 2492, "vel": 144, "hdg": 340, "vr": -7.8},
    {"icao24": "a2be06", "callsign": "AAY3210", "country": "United States", "lat": 33.640, "lng": -118.048, "alt": 1509, "vel": 117, "hdg": 57, "vr": 0},
    {"icao24": "899014", "callsign": "CAL5116", "country": "Taiwan", "lat": 33.953, "lng": -118.398, "alt": 53, "vel": 74, "hdg": 263, "vr": -3.9},
    {"icao24": "781a1f", "callsign": "CKK222", "country": "China", "lat": 33.918, "lng": -118.661, "alt": 2088, "vel": 141, "hdg": 270, "vr": 11.4},
    {"icao24": "a316f3", "callsign": "N299AK", "country": "United States", "lat": 34.066, "lng": -117.923, "alt": 1821, "vel": 82, "hdg": 284, "vr": 0},
    {"icao24": "a7816a", "callsign": "DAL2974", "country": "United States", "lat": 33.985, "lng": -118.073, "alt": 1623, "vel": 117, "hdg": 263, "vr": -5.9},
    {"icao24": "a577d4", "callsign": "SWA3335", "country": "United States", "lat": 33.624, "lng": -117.892, "alt": 762, "vel": 80, "hdg": 188, "vr": 9.4},
]

ddb = boto3.resource("dynamodb", region_name=REGION)
table = ddb.Table(TABLE_NAME)


def seed():
    now = int(time.time())
    ttl = now + 300

    with table.batch_writer() as batch:
        for f in FLIGHTS:
            # Add slight random drift to simulate movement
            lat = f["lat"] + random.uniform(-0.002, 0.002)
            lng = f["lng"] + random.uniform(-0.003, 0.003)
            alt = f["alt"] + random.uniform(-20, 20) if f["alt"] else None

            batch.put_item(Item={
                "pk": "FLIGHT",
                "sk": f["icao24"],
                "icao24": f["icao24"],
                "callsign": f["callsign"],
                "country": f["country"],
                "longitude": Decimal(str(round(lng, 4))),
                "latitude": Decimal(str(round(lat, 4))),
                "altitude": Decimal(str(round(alt, 2))) if alt else None,
                "velocity": Decimal(str(f["vel"])) if f["vel"] else None,
                "heading": Decimal(str(f["hdg"])),
                "vertical_rate": Decimal(str(f["vr"])) if f["vr"] else None,
                "on_ground": f["alt"] is None or f["alt"] < 50,
                "updated": now,
                "ttl": ttl,
            })

    return len(FLIGHTS)


def main():
    print(f"Seeding {len(FLIGHTS)} flights every 30s → DynamoDB ({TABLE_NAME})")
    print("Ctrl-C to stop\n")

    while True:
        try:
            count = seed()
            print(f"[{time.strftime('%H:%M:%S')}] {count} flights seeded")
        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Error: {e}")
        time.sleep(30)


if __name__ == "__main__":
    main()
