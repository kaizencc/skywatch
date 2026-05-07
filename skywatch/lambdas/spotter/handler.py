"""AI spotter: picks the most interesting flight overhead and explains why."""
import json
import os
import time

import boto3

TABLE_NAME = os.environ["TABLE_NAME"]
MODEL_ID = os.environ["MODEL_ID"]

ddb = boto3.resource("dynamodb")
table = ddb.Table(TABLE_NAME)
bedrock = boto3.client("bedrock-runtime")


def handler(event, context):
    # Get current flights (same freshness filter as the API)
    cutoff = int(time.time()) - 90
    resp = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("pk").eq("FLIGHT"),
        FilterExpression=boto3.dynamodb.conditions.Attr("updated").gte(cutoff),
    )
    flights = resp.get("Items", [])

    if not flights:
        print("No flights to analyze")
        return {"statusCode": 200, "body": "No flights"}

    # Build a summary for Claude
    flight_lines = []
    icao_lookup = {}
    for f in flights[:50]:  # Cap at 50 to stay within token limits
        callsign = f.get('callsign', '???').strip() or '???'
        icao = f.get('icao24', '')
        icao_lookup[callsign] = icao
        line = (
            f"{callsign:8s} (icao24={icao}) | "
            f"alt={f.get('altitude', '?')}m | "
            f"speed={f.get('velocity', '?')}m/s | "
            f"heading={f.get('heading', '?')}° | "
            f"country={f.get('country', '?')} | "
            f"ground={'yes' if f.get('on_ground') else 'no'}"
        )
        flight_lines.append(line)

    flights_text = "\n".join(flight_lines)

    prompt = f"""You are an aviation enthusiast narrating a live flight tracker display.
Here are the flights currently overhead near Long Beach, California:

{flights_text}

Pick the single most interesting flight and explain why in exactly one sentence.
Consider: unusual aircraft, long-haul routes, military callsigns, extreme altitudes,
or anything a casual observer would find cool. Be specific and enthusiastic.
Respond with ONLY a JSON object: {{"icao24": "<the icao24 value>", "text": "✨ Spotted: [your one sentence]"}}
"""

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": prompt}],
    })

    response = bedrock.invoke_model(modelId=MODEL_ID, body=body)
    result = json.loads(response["body"].read())
    raw = result["content"][0]["text"].strip()

    # Parse the JSON response
    try:
        # Strip markdown code fences if present
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = json.loads(clean)
        spotlight_text = parsed.get("text", raw)
        spotted_icao = parsed.get("icao24", "")
    except (json.JSONDecodeError, KeyError):
        spotlight_text = raw
        spotted_icao = ""

    # Store the spotlight
    table.put_item(Item={
        "pk": "SPOTLIGHT",
        "sk": "current",
        "text": spotlight_text,
        "icao24": spotted_icao,
        "updated": int(time.time()),
        "ttl": int(time.time()) + 300,
    })

    print(f"Spotlight: {spotlight_text}")
    return {"statusCode": 200, "body": spotlight_text}
