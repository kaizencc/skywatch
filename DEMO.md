# SkyWatch Demo Script (10 minutes)

## Pre-Demo Setup

- `python scripts/poll_opensky.py` running in a hidden terminal
- Browser open to https://d2d8g1kdqdl9kt.cloudfront.net (map loaded, planes moving)
- VS Code open to the project root
- Terminal ready with `source .venv/bin/activate`

---

## Act 1: The Hook (2 min)

**[Show the live map]**

> "This is the sky above us right now. Every plane you see is real — live ADS-B transponder data from OpenSky Network, updating every 30 seconds."

Click on an interesting flight (airline, not a private N-number). Wait for the popup and AI spotlight.

> "When I click a flight, two things happen: FlightAware tells us the route, and Claude writes a one-liner about why it's interesting. All of this is running on AWS — Lambda, DynamoDB, Bedrock — deployed with Python CDK."

Click a few more flights. Let the audience see the spotlight update.

---

## Act 2: The Code (3 min)

**[Switch to VS Code — show `skywatch/stack.py`]**

> "The entire infrastructure is ~170 lines of Python. Let me walk you through it."

Scroll through and highlight:
- **DynamoDB table** — single table design, TTL for auto-cleanup
- **Poller Lambda** — fetches flights on a schedule
- **API Lambda** — serves data to the frontend, calls FlightAware and Bedrock
- **Secrets Manager** — no API keys in code, ever
- **S3 + CloudFront** — static frontend, deployed automatically

> "This is infrastructure as code. I describe what I want, CDK figures out the IAM policies, the networking, the permissions. I never write a CloudFormation template."

---

## Act 3: The Bug (3 min)

**[In `stack.py`, comment out the Bedrock IAM policy block]**

```python
# spotter.add_to_role_policy(iam.PolicyStatement(
#     actions=["bedrock:InvokeModel"],
#     resources=[...],
# ))
```

> "Let's say I accidentally remove this permission. Watch what happens."

**[Run `cdk deploy`]**

Deploy succeeds (it's removing a permission, not adding one). Click a flight — spotlight fails silently or shows fallback text.

> "The AI stopped working. In production, this is a 3am page. But let's say I try to fix it the lazy way..."

**[Uncomment with `Resource: *`]**

```python
spotter.add_to_role_policy(iam.PolicyStatement(
    actions=["bedrock:InvokeModel"],
    resources=["*"],  # <-- too broad
))
```

**[Run `cdk deploy` — CDK Nag blocks it]**

> "CDK Nag just stopped me from deploying an overly-permissive IAM policy. This is a guardrail built into the pipeline. It caught a security issue before it reached production."

**[Fix with scoped ARN]**

```python
resources=[
    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
]
```

**[Run `cdk deploy` — succeeds]**

> "Scoped to the exact model. Deploys clean. That's the CDK workflow: write Python, get guardrails for free."

Click a flight — spotlight works again.

---

## Act 4: Community + Wrap (2 min)

**[Show the community section on the map]**

> "One more thing. See these arcs? PyCon attendees adding their home cities to the map."

**[Show QR code or type a city name]**

> "Add yours. It geocodes your city and draws an arc to Long Beach."

**[Back to the map, full screen]**

> "To recap: live data from three APIs, AI narration from Claude, infrastructure guardrails from CDK Nag, all deployed with `cdk deploy`. The whole thing is open source."

Point to the GitHub URL.

> "Questions?"

---

## Talking Points for Q&A

- **"How much does this cost?"** — Under $5/day. Lambda + DynamoDB + Bedrock Haiku. FlightAware is the biggest cost at ~$7/day during active use.
- **"Why not just use Terraform?"** — CDK gives you loops, conditionals, type safety, and constructs. The Nag guardrail demo wouldn't work the same way.
- **"Is the AI useful or just a gimmick?"** — It's a hook. But the pattern (Lambda → Bedrock → store result) is the same pattern you'd use for summarization, classification, or any GenAI feature.
- **"How do you handle secrets?"** — Secrets Manager. The Mapbox token is injected at deploy time into a `config.js` file. Nothing in source code.
