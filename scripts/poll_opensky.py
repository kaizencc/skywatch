#!/usr/bin/env python3
"""Local OpenSky poller — runs on your laptop, pushes flights to DynamoDB.

Usage:
    source .venv/bin/activate
    python scripts/poll_opensky.py

Fetches API keys from AWS Secrets Manager (skywatch/api-keys).
Polls every 60 seconds. Ctrl-C to stop.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.parse
from decimal import Decimal

import boto3

# Fetch secrets from Secrets Manager
secrets_client = boto3.client("secretsmanager", region_name="us-east-1")
_secrets = json.loads(
    secrets_client.get_secret_value(SecretId="skywatch/api-keys")["SecretString"]
)

TABLE_NAME = "SkyWatch-Flights80E3986D-T8BJLAQX52QX"
REGION = "us-east-1"
POLL_INTERVAL = 30  # seconds

CLIENT_ID = _secrets.get("OPENSKY_CLIENT_ID", "")
CLIENT_SECRET = _secrets.get("OPENSKY_CLIENT_SECRET", "")
TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"

# Long Beach, 50km radius
LAT, LON = 33.8177, -118.1514
DLAT = 50 / 111.0
DLON = 50 / 85.0

_cached_token = None
_token_expires_at = 0

ddb = boto3.resource("dynamodb", region_name=REGION)
table = ddb.Table(TABLE_NAME)


def get_access_token():
    global _cached_token, _token_expires_at
    now = time.time()
    if _cached_token and now < _token_expires_at:
        return _cached_token

    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded",
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        token_data = json.loads(resp.read())

    _cached_token = token_data["access_token"]
    _token_expires_at = now + token_data.get("expires_in", 1800) - 60
    return _cached_token


def poll():
    url = (
        f"https://opensky-network.org/api/states/all"
        f"?lamin={LAT - DLAT}&lamax={LAT + DLAT}"
        f"&lomin={LON - DLON}&lomax={LON + DLON}"
    )

    headers = {"User-Agent": "SkyWatch/1.0"}
    if CLIENT_ID:
        headers["Authorization"] = f"Bearer {get_access_token()}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())

    states = data.get("states") or []
    now = int(time.time())
    ttl = now + 300  # 5 minute TTL

    with table.batch_writer() as batch:
        for s in states:
            icao24 = s[0]
            if not icao24:
                continue
            batch.put_item(Item={
                "pk": "FLIGHT",
                "sk": icao24,
                "icao24": icao24,
                "callsign": (s[1] or "").strip(),
                "country": s[2] or "",
                "longitude": Decimal(str(s[5])) if s[5] else None,
                "latitude": Decimal(str(s[6])) if s[6] else None,
                "altitude": Decimal(str(s[7])) if s[7] else None,
                "velocity": Decimal(str(s[9])) if s[9] else None,
                "heading": Decimal(str(s[10])) if s[10] is not None else None,
                "vertical_rate": Decimal(str(s[11])) if s[11] else None,
                "on_ground": s[8] if s[8] is not None else False,
                "updated": now,
                "ttl": ttl,
            })

    return len(states)


def main():
    print(f"Polling OpenSky every {POLL_INTERVAL}s → DynamoDB ({TABLE_NAME})")
    print(f"Auth: {'OAuth2' if CLIENT_ID else 'anonymous'}")
    print("Ctrl-C to stop\n")

    while True:
        try:
            count = poll()
            print(f"[{time.strftime('%H:%M:%S')}] {count} flights")
        except KeyboardInterrupt:
            print("\nStopped.")
            sys.exit(0)
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Error: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
