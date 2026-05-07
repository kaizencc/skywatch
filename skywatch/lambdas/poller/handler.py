"""Polls OpenSky Network for live flights near the configured location.

NOTE: OpenSky blocks TCP connections from AWS IP ranges, so this Lambda
is currently a no-op. Flight data is pushed by the local proxy script
(scripts/poll_opensky.py) running on a developer laptop.
"""
import json


def handler(event, context):
    return {"statusCode": 200, "body": "Polling handled by local proxy"}
