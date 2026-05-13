# SkyWatch Session Context

## Project Overview

SkyWatch is a live AI-narrated flight tracker for the PyCon 2026 booth demo, deployed with Python CDK.

## Key URLs

- **Live site**: https://d2d8g1kdqdl9kt.cloudfront.net
- **API Gateway**: https://hpl9da2m4i.execute-api.us-east-1.amazonaws.com
- **GitHub**: https://github.com/kaizencc/skywatch

## AWS Resources

- **Stack name**: SkyWatch
- **Region**: us-east-1
- **Account**: 912331974472
- **DynamoDB table**: SkyWatch-Flights80E3986D-T8BJLAQX52QX
- **S3 bucket**: skywatch-sitebucket397a1860-mlq1rdu9kbgu
- **CloudFront distribution**: E2VLZ5XMJA0U0
- **Secrets Manager**: skywatch/api-keys (contains OPENSKY_CLIENT_ID, OPENSKY_CLIENT_SECRET, FLIGHTAWARE_API_KEY, MAPBOX_TOKEN)

## Architecture

- **EventBridge (1 min)** → Poller Lambda → DynamoDB (flights)
- **API Gateway** → API Lambda → DynamoDB, FlightAware, Bedrock Claude
- **CloudFront** → S3 → Static frontend (Mapbox GL + flight board + AI spotlight)
- **Secrets Manager** → all API keys (nothing in source code)
- **Mapbox token** injected at deploy time via `config.js` generated from Secrets Manager

## Project Structure

```
skywatch/
├── app.py                          # CDK app entry point (CDK Nag enabled)
├── skywatch/
│   ├── stack.py                    # CDK stack (full version with AI + Nag)
│   └── lambdas/
│       ├── api/handler.py          # API: flights, spotlight (Bedrock), FlightAware, community
│       ├── poller/handler.py       # No-op (OpenSky blocks AWS IPs)
│       └── spotter/handler.py      # Scheduled AI spotter (legacy, still deployed)
├── frontend/
│   ├── index.html
│   ├── map.js                      # Mapbox map, markers, popups, spotlight generation
│   ├── board.js                    # Community form, spotlight display
│   └── style.css
├── scripts/
│   ├── poll_opensky.py             # Local proxy: polls OpenSky → DynamoDB
│   └── seed_flights.py             # Backup: seeds fake flights when OpenSky is down
├── demo/
│   ├── EMERGENCY_RESTORE.md       # Panic button: restore full working app
│   └── stages/
│       ├── stack_stage1.py         # Base app (no AI, Nag enabled)
│       ├── stack_stage2.py         # + AI with Resource:* (Nag BLOCKS)
│       ├── stack_stage3.py         # + AI with scoped ARN (Nag passes)
│       ├── handler_before.py       # API handler without AI
│       └── handler_after.py        # API handler with AI
├── DEMO.md                         # 10-minute staged demo script
└── README.md                       # Architecture diagram + setup
```

## How the Demo Works

1. Start with stage 1 stack + handler_before (no AI, Nag enabled)
2. Show the live map, walk the Python CDK code, `cdk synth`
3. Live-code AI feature with Claude Code + aws-cdk skill, use `Resource: *` → Nag blocks it
4. Explain CDK Nag (what it is, why it matters)
5. Fix with scoped Bedrock ARN → Nag passes
6. `cdk deploy` → AI spotlight works

Backup: `cp demo/stages/stack_stageN.py skywatch/stack.py`

## Key Implementation Details

- **Single DynamoDB table** with pk/sk: FLIGHT/{icao24}, SPOTLIGHT/current, COMMUNITY/{city}, FLIGHTINFO/{callsign}
- **FlightAware data cached** in DynamoDB for 1 hour (FLIGHTINFO partition)
- **Spotlight is user-driven**: clicking a flight triggers POST /spotlight → Bedrock → DynamoDB
- **spottedIcao** (var in map.js) controls which plane is red/large — set on user click
- **CORS**: API Gateway preflight + Lambda response headers (both needed)
- **Frontend polling**: map.js fetches /flights every 5s, renders markers AND board (single source of truth)
- **OpenSky blocks AWS IPs**: poller Lambda is a no-op; local `poll_opensky.py` or `seed_flights.py` pushes data

## Deploy Commands

```bash
source .venv/bin/activate
cdk deploy --require-approval never

# Manual frontend deploy (bypasses CDK):
aws s3 sync frontend/ s3://skywatch-sitebucket397a1860-mlq1rdu9kbgu/ --delete
aws cloudfront create-invalidation --distribution-id E2VLZ5XMJA0U0 --paths "/*"
```

## Seeding Flights (when OpenSky is down)

```bash
python scripts/seed_flights.py
```

18 realistic flights near Long Beach with position drift every 30s.
