# SkyWatch Demo Script (10 minutes)

## Overview

Build an AI feature live on stage, get blocked by a security guardrail, fix it, deploy it.

**Stages:**
1. Show the live app (planes on a map)
2. Walk through the CDK code — `cdk synth`
3. Add CDK Nag for best practices
4. Build an AI spotlight feature (connect to Bedrock)
5. Get blocked by CDK Nag (overly permissive IAM)
6. Fix it, deploy, see it work

**Backup files:** If you get stuck at any stage, copy the corresponding file from `demo/stages/` into `skywatch/stack.py`:
```bash
cp demo/stages/stack_stage1.py skywatch/stack.py  # Base app
cp demo/stages/stack_stage2.py skywatch/stack.py  # + CDK Nag
cp demo/stages/stack_stage3.py skywatch/stack.py  # + AI (blocked)
cp demo/stages/stack_stage4.py skywatch/stack.py  # + AI (fixed)
```

---

## Pre-Demo Setup

- `python scripts/poll_opensky.py` running in a hidden terminal
- Browser open to https://d2d8g1kdqdl9kt.cloudfront.net
- VS Code open to the project root
- Terminal ready with `source .venv/bin/activate`
- Start with `demo/stages/stack_stage1.py` as your `skywatch/stack.py`
- CDK Nag **disabled** in `app.py` (comment out the two lines)

---

## Stage 1: Here's an App with Planes (2 min)

**[Show the live map in the browser]**

> "This is the sky above us right now. Real planes, real transponder data, updating live. Built with Python CDK and deployed to AWS."

Click around — show the flight list, click a plane, show the popup with FlightAware data.

> "We've got Lambda polling OpenSky for ADS-B data, DynamoDB storing it, API Gateway serving it, and a static frontend on CloudFront. All defined in one Python file."

---

## Stage 2: Walk the Code — `cdk synth` (2 min)

**[Switch to VS Code — open `skywatch/stack.py`]**

> "This is the entire infrastructure. ~100 lines of Python."

Highlight:
- DynamoDB table (5 lines)
- Lambda functions (10 lines each)
- API Gateway with routes (10 lines)
- S3 + CloudFront (15 lines)

**[Run `cdk synth` in terminal]**

> "CDK synthesizes this into CloudFormation — over 1000 lines of YAML that I never have to write or maintain. Let me show you."

Optionally open `cdk.out/SkyWatch.template.json` and scroll to show the volume.

---

## Stage 3: Add CDK Nag for Best Practices (2 min)

**[In `app.py`, uncomment the CDK Nag lines]**

```python
from cdk_nag import AwsSolutionsChecks
# ...
cdk.Aspects.of(app).add(AwsSolutionsChecks())
```

**[Run `cdk synth`]**

> "CDK Nag checks your infrastructure against AWS best practices — the same rules AWS Solutions Architects use in reviews. Let's see if our app passes."

It passes (because Stage 2 has suppressions for the non-AI stuff).

> "Clean. Every finding is either fixed or explicitly suppressed with a reason. Now let's add a feature."

---

## Stage 4: Build the AI Feature (2 min)

**[Explain what we're adding]**

> "I want Claude to narrate the flights — click a plane, get an AI-generated blurb. We need: Bedrock access from our API Lambda, and a MODEL_ID environment variable."

**[Add to the API Lambda environment]**

```python
environment={
    **lambda_env,
    "MODEL_ID": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
},
```

**[Add the IAM permission — intentionally too broad]**

```python
api_handler.add_to_role_policy(iam.PolicyStatement(
    actions=["bedrock:InvokeModel"],
    resources=["*"],
))
```

> "Quick and dirty — give it access to all Bedrock models. Ship it."

**[Run `cdk synth`]**

💥 **CDK Nag ERROR:**
```
AwsSolutions-IAM5[Resource::*]: The IAM entity contains wildcard permissions
```

> "Blocked. CDK Nag caught that `Resource: *` gives this Lambda access to every model in Bedrock — not just the one we need. This is the guardrail working."

---

## Stage 5: Fix It Right (1 min)

**[Replace `resources=["*"]` with the scoped ARN]**

```python
api_handler.add_to_role_policy(iam.PolicyStatement(
    actions=["bedrock:InvokeModel"],
    resources=[
        f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
        f"arn:aws:bedrock:{self.region}:{self.account}:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0",
    ],
))
```

**[Run `cdk synth`]**

> "Clean. Scoped to exactly the model we need."

---

## Stage 6: Deploy and See It Work (1 min)

**[Run `cdk deploy`]**

> "Deploying the AI feature..."

Wait for deploy (~90s). Once done, switch to browser, hard refresh, click a flight.

> "There it is — Claude narrating the sky above PyCon. We went from idea to deployed AI feature in under 10 minutes, and a security guardrail stopped us from shipping a bad IAM policy along the way."

---

## Wrap

> "That's CDK: Python infrastructure, best-practice guardrails, and a deploy command. Questions?"

---

## Talking Points for Q&A

- **"How much does this cost?"** — Under $5/day. Lambda + DynamoDB + Bedrock Haiku.
- **"Why CDK over Terraform?"** — Loops, conditionals, type safety, constructs, and Nag. All in the language you already write your app in.
- **"What's CDK Nag checking?"** — AWS Solutions Architect best practices. IAM least privilege, encryption, logging, network security. ~100 rules.
- **"Can I add my own rules?"** — Yes. Custom Nag packs for your org's policies.
- **"How do you handle secrets?"** — Secrets Manager. Nothing in source code. Token injected at deploy time.
