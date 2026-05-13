# SkyWatch Demo Script (10 minutes)

## Overview

SkyWatch is a live AI-narrated flight tracker showing real planes above PyCon Long Beach. The app pulls ADS-B transponder data, stores it in DynamoDB, serves it through API Gateway, and renders a live map on a CloudFront-hosted frontend. The entire infrastructure is defined in ~100 lines of Python CDK.

In this demo, we start with the base flight tracker (no AI), then live-code a Bedrock-powered spotlight feature using Claude Code with the `aws-cdk` skill. CDK Nag is already enabled — it will block our first attempt because of an overly permissive IAM policy, giving us a chance to explain what Nag is and why it matters. We fix it, deploy, and the feature works.

---

## Pre-Demo Setup

- `python scripts/poll_opensky.py` running in a hidden terminal (or `python scripts/seed_flights.py` if OpenSky is down)
- Browser open to https://d2d8g1kdqdl9kt.cloudfront.net
- Terminal with Claude Code open at project root, `source .venv/bin/activate`
- Start with stage 1 stack + handler_before (no AI):
  ```bash
  cp demo/stages/stack_stage1.py skywatch/stack.py
  cp demo/stages/handler_before.py skywatch/lambdas/api/handler.py
  ```
- CDK Nag **enabled** in `app.py` (these lines should be uncommented):
  ```python
  from cdk_nag import AwsSolutionsChecks
  cdk.Aspects.of(app).add(AwsSolutionsChecks())
  ```
- Nag suppressions already present in stage 1 stack (so baseline passes clean)

---

## Stage 1: Here's SkyWatch (2 min)

**[Show the live map in the browser]**

> "This is the sky above us right now. Real planes, real transponder data, updating live."

Click around — show the flight list, click a plane, show the popup with FlightAware data.

> "We've got Lambda pulling ADS-B data, DynamoDB storing it, API Gateway serving it, and a static frontend on CloudFront."

---

## Stage 2: The Python CDK Code (2 min)

**[Switch to terminal/editor — show `skywatch/stack.py`]**

> "Here's the entire infrastructure — about 100 lines of Python. DynamoDB table, two Lambdas, API Gateway, S3, CloudFront. That's it."

**[Run:]**
```bash
cdk synth
```

> "CDK takes those 100 lines and synthesizes over 1000 lines of CloudFormation that I never have to write or maintain. Python gives us loops, conditionals, type safety, and real abstractions — not YAML templating."

Optionally open `cdk.out/SkyWatch.template.json` and scroll to show the volume.

---

## Stage 3: Live-Code the AI Feature (3 min)

> "Now I want to add a feature — click a plane, get an AI-generated blurb from Claude on Bedrock. I'm going to use Claude Code with the aws-cdk skill to build this."

**[In Claude Code, prompt something like:]**

> "Add an AI spotlight feature. When a user POSTs to /spotlight with a flight's callsign and info, call Bedrock Claude Haiku to generate a one-sentence aviation spotter blurb, store the result in DynamoDB. The frontend sends FlightAware data along with the request since OpenSky only gives us position — we need the airline, route, and aircraft type from FlightAware to make the blurb interesting. I need both the handler code and the CDK infra — add the Bedrock IAM permission and MODEL_ID environment variable to the API Lambda."

**[Let Claude Code generate the code. It should:]**
1. Add the Bedrock client + MODEL_ID env var to `handler.py`
2. Add a `generate_spotlight` function and POST route
3. Add the Bedrock IAM policy to the API Lambda in `stack.py`
4. Add MODEL_ID to the Lambda environment

> "The aws-cdk skill gives Claude Code deep knowledge of CDK patterns — IAM grants, environment variables, construct architecture. Let's see if it deploys."

**[Before running synth, ensure the Bedrock IAM policy uses `resources=["*"]`. If Claude Code scoped it correctly, manually widen it:]**

```python
        api_handler.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=["*"],
        ))
```

> "Quick and dirty — access to all Bedrock models. Ship it."

**[Also remove the IAM5 suppression from the Nag suppressions list in `stack.py`:]**

Delete this line:
```python
            {"id": "AwsSolutions-IAM5", "reason": "Wildcard scoped to DynamoDB table and S3 bucket ARNs"},
```

> "We had a blanket suppression for wildcards on known resources. Now that we're adding a new IAM policy, let's remove it and let Nag check everything fresh."

**[Run:]**
```bash
cdk synth
```

**CDK Nag ERROR:**
```
[Error at /SkyWatch/Api/ServiceRole/DefaultPolicy/Resource]
AwsSolutions-IAM5[Resource::*]: The IAM entity contains wildcard permissions
and does not have a cdk-nag rule suppression with evidence for those permission.
```

**Backup if you need it:**
```bash
cp demo/stages/stack_stage2.py skywatch/stack.py
cp demo/stages/handler_after.py skywatch/lambdas/api/handler.py
```

---

## Stage 4: What Just Happened — CDK Nag (2 min)

> "We just got blocked. This is CDK Nag — it runs the same best-practice rules that AWS Solutions Architects use, directly in your synthesis pipeline. It caught that `Resource: *` gives this Lambda access to every model in Bedrock, not just the one we need."

> "CDK Nag checks about 100 rules: IAM least privilege, encryption at rest, logging, network security. You can write custom rule packs for your org's own policies. It runs at synth time — before anything touches AWS — so bad infrastructure never leaves your laptop."

> "The existing infrastructure passed clean because we suppress known findings with documented reasons. But our new code introduced an overly permissive policy, and Nag won't let us deploy it."

---

## Stage 5: Fix It — Least Privilege (1 min)

**[Replace `resources=["*"]` with a scoped ARN:]**

```python
        api_handler.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=[
                f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
                f"arn:aws:bedrock:{self.region}:{self.account}:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0",
            ],
        ))
```

**[Run:]**
```bash
cdk synth
```

> "Clean. Scoped to exactly the model we need. Least privilege. Nag is happy, and so is your security team."

---

## Stage 6: Deploy and See It Work (1 min)

**[Run:]**
```bash
cdk deploy --require-approval never
```

> "Deploying..."

Wait for deploy (~90s). Switch to browser, hard refresh (Cmd+Shift+R), click a flight.

The spotlight panel shows an AI-generated blurb.

> "There it is — Claude narrating the sky above PyCon. Idea to deployed feature in under 10 minutes."

---

## Wrap

> "Python CDK gave us the infrastructure in 100 lines. The aws-cdk skill let Claude Code write correct CDK patterns on the first try. And CDK Nag caught a bad IAM policy before it ever reached AWS. You build fast, but you ship safe. Questions?"

---

## Key Takeaways

1. **Python CDK** — ~100 lines of Python replaces 1000+ lines of CloudFormation. Real programming language, real abstractions.
2. **aws-cdk skill** — Claude Code understands CDK constructs, IAM grants, and deployment patterns. Part of the open-source Agent Toolkit for AWS.
3. **CDK Nag** — Automated guardrails at synth time. Catches overly permissive IAM, missing encryption, unlogged APIs — before anything deploys.

---

## Q&A Cheat Sheet

| Question | Answer |
|----------|--------|
| How much does this cost? | Under $5/day. Lambda + DynamoDB + Bedrock Haiku. |
| Why CDK over Terraform? | Loops, conditionals, type safety, constructs, Nag. All in Python. |
| What's CDK Nag checking? | ~100 AWS Solutions Architect best-practice rules. IAM, encryption, logging, network. |
| Can I add my own rules? | Yes. Custom Nag packs for your org's policies. |
| How do you handle secrets? | Secrets Manager. Nothing in source code. |
| What's the aws-cdk skill? | Part of the Agent Toolkit for AWS. Gives Claude Code deep knowledge of CDK patterns and troubleshooting. Open source on GitHub. |
| Does this work with other agents? | Yes — the toolkit supports Claude Code, Codex, Kiro, and any MCP-compatible agent. |
