# SkyWatch — PyCon 2026 Booth Demo

A live AI-narrated flight tracker for the airspace above PyCon, deployed with Python CDK.

## Demo Flow (5 minutes)

1. **The app** — Map is live, planes moving over Long Beach. AI "Spotted" callout flags interesting flights. "This is the sky above us right now."
2. **There's a bug** — The AI spotter never fires. Show the AccessDenied error in logs. "Missing IAM permission."
3. **Quick fix (wrong)** — Add `bedrock:InvokeModel` with `Resource: *`. Run `cdk deploy`. **Blocked by CDK Nag validation.** "CDK just stopped me from shipping a security issue."
4. **Fix it right** — Scope the resource to the specific Bedrock model ARN. `cdk deploy` again. Passes. Deploys.
5. **It works** — AI spotter lights up: "✨ Spotted: Qantas A380 to Sydney." "That was: find a bug, fix it, get stopped by a guardrail, fix it right, deploy. All in Python."
6. **Community** — QR code: "Add your city to the map."

## Architecture

```mermaid
graph LR
    subgraph Backend
        EB[EventBridge<br/>1 min schedule] --> Poller[Poller Lambda]
        Poller -->|write flights| DDB[(DynamoDB)]
        Poller -->|fetch ADS-B| OpenSky[OpenSky API]
        APIGW[API Gateway] --> API[API Lambda]
        API --> DDB
        API -->|enrich route| FA[FlightAware API]
        API -->|generate spotlight| Bedrock[Bedrock Claude]
        SM[Secrets Manager] -.->|API keys| API
        SM -.->|API keys| Poller
    end

    subgraph Frontend
        CF[CloudFront] --> S3[S3 Bucket]
        S3 --> Site[Mapbox GL map<br/>+ flight board<br/>+ AI spotlight]
    end

    Site -->|fetch data| APIGW

    style Backend fill:#1a1a2e,stroke:#00ff88,color:#00ff88
    style Frontend fill:#0f2027,stroke:#00ccff,color:#00ccff
    style EB fill:#ff9900,stroke:#ff9900,color:#000
    style Poller fill:#7b2ff7,stroke:#7b2ff7,color:#fff
    style API fill:#7b2ff7,stroke:#7b2ff7,color:#fff
    style DDB fill:#3b48cc,stroke:#3b48cc,color:#fff
    style APIGW fill:#ff4f8b,stroke:#ff4f8b,color:#fff
    style Bedrock fill:#00a67d,stroke:#00a67d,color:#fff
    style CF fill:#00ccff,stroke:#00ccff,color:#000
    style S3 fill:#3b48cc,stroke:#3b48cc,color:#fff
    style Site fill:#0a0a0f,stroke:#00ccff,color:#00ccff
    style OpenSky fill:#4a4a4a,stroke:#4a4a4a,color:#fff
    style FA fill:#4a4a4a,stroke:#4a4a4a,color:#fff
    style SM fill:#dd3522,stroke:#dd3522,color:#fff
```

## Setup

### Prerequisites

- AWS CDK CLI (`npm install -g aws-cdk`)
- Python 3.12+
- API keys:
  - [OpenSky Network](https://opensky-network.org/) — free account for ADS-B position data
  - [FlightAware AeroAPI](https://www.flightaware.com/aeroapi/signup/personal) — Personal tier ($5/mo free credit) for route enrichment
  - [Mapbox](https://account.mapbox.com/auth/signup/) — free tier for map rendering

### Deploy

```bash
cd skywatch
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cdk deploy
```

## Cost

- OpenSky: Free
- FlightAware: ~$20 for 3-day conference (Personal tier)
- Mapbox: Free (well under 50k map loads)
- AWS: Minimal (Lambda + DynamoDB + S3/CloudFront + Bedrock)
