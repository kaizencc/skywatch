# SkyWatch Architecture

## System Diagram

```
                                    ┌──────────────────────────────────────────┐
                                    │              USERS (Browser)              │
                                    └────────────────────┬─────────────────────┘
                                                         │
                                                         ▼
                              ┌───────────────────────────────────────────────────────┐
                              │                 Amazon CloudFront                       │
                              │              (Global CDN, HTTPS only)                   │
                              └──────────────┬────────────────────────┬────────────────┘
                                             │                        │
                                   static assets                  API calls
                                             │                        │
                                             ▼                        ▼
                    ┌─────────────────────────────────┐    ┌─────────────────────────┐
                    │          Amazon S3               │    │   Amazon API Gateway    │
                    │    (Static Site Hosting)         │    │       (HTTP API)        │
                    │                                  │    │                         │
                    │  index.html, map.js, board.js,   │    │  /flights    GET        │
                    │  style.css, config.js            │    │  /spotlight  GET, POST  │
                    └─────────────────────────────────┘    │  /community  GET, POST  │
                                                           │  /flight/:id GET        │
                                                           └────────────┬────────────┘
                                                                        │
                                                                        ▼
                                                           ┌────────────────────────┐
                                                           │  AWS Lambda — API Fn   │
                                                           │  (Python 3.12)         │
                                                           │                        │
                                                           │  Serves flight data,   │
                                                           │  FlightAware lookups,  │
                                                           │  community cities,     │
                                                           │  AI spotlight (Stage 3)│
                                                           └───┬──────┬─────────┬───┘
                                                               │      │         │
                                      ┌────────────────────────┘      │         └──────────────────┐
                                      │                               │                            │
                                      ▼                               ▼                            ▼
                         ┌────────────────────────┐      ┌───────────────────────┐    ┌────────────────────────┐
                         │    Amazon DynamoDB      │      │   AWS Secrets Mgr     │    │   Amazon Bedrock       │
                         │   (Single-table)        │      │                       │    │   (Claude Haiku)       │
                         │                         │      │  OpenSky credentials  │    │                        │
                         │  FLIGHT/{icao24}        │      │  FlightAware API key  │    │  Generates AI blurbs   │
                         │  SPOTLIGHT/current      │      │  Mapbox token         │    │  for spotted flights   │
                         │  COMMUNITY/{city}       │      │                       │    │  (added in demo)       │
                         │  FLIGHTINFO/{callsign}  │      └───────────────────────┘    └────────────────────────┘
                         │                         │
                         └──────────┬─────────────┘
                                    │
                                    │ also written by:
                                    │
                                    ▼
                       ┌────────────────────────┐
                       │ AWS Lambda — Poller Fn │
                       │ (Python 3.12)          │
                       │                        │
                       │ Fetches ADS-B data     │
                       │ from OpenSky Network   │
                       └────────────┬───────────┘
                                    │ triggered by
                                    ▼
                       ┌────────────────────────┐
                       │  Amazon EventBridge    │
                       │  (Scheduled Rule)      │
                       │                        │
                       │  rate(1 minute)        │
                       └────────────────────────┘
```

## AWS Services Used

| Service | Purpose | Why |
|---------|---------|-----|
| **CloudFront** | CDN | Global edge caching, HTTPS termination, Origin Access Control |
| **S3** | Static hosting | Frontend assets (HTML/JS/CSS), no public access |
| **API Gateway** | HTTP API | RESTful routes to Lambda, CORS, no auth needed |
| **Lambda** (x2) | Compute | Poller + API handler, Python 3.12, pay-per-invocation |
| **DynamoDB** | Database | Single-table, pay-per-request, TTL for auto-expiry |
| **EventBridge** | Scheduler | Triggers poller every minute |
| **Secrets Manager** | Secrets | API keys — nothing in source code |
| **Bedrock** | AI | Claude Haiku generates flight narration (added in demo) |

## Data Flow

1. **Ingest**: EventBridge (1 min) → Poller Lambda → OpenSky API → DynamoDB
2. **Serve**: Browser → CloudFront → API Gateway → API Lambda → DynamoDB
3. **AI Spotlight**: Browser POST → API Lambda → Bedrock Claude → DynamoDB → Browser
4. **Frontend**: Browser → CloudFront → S3 (static HTML/JS/CSS)

## What CDK Gives You

```
~100 lines of Python  ──cdk synth──▶  1000+ lines of CloudFormation
                                       (IAM roles, policies, resource configs,
                                        cross-references, outputs, metadata)
```

All 8 services above, fully wired with IAM permissions, are defined in a single `stack.py` file.
