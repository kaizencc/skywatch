# SkyWatch Demo Script (10 minutes)

## Overview

Build an AI feature live on stage, get blocked by a security guardrail, fix it, deploy it.

**Backup files:** If you get stuck at any stage, copy the corresponding file:
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

Highlight: DynamoDB table, Lambda functions, API Gateway, S3 + CloudFront.

**[Run in terminal:]**
```bash
cdk synth
```

> "CDK synthesizes this into CloudFormation — over 1000 lines of YAML that I never have to write. Let me show you."

Optionally open `cdk.out/SkyWatch.template.json` and scroll to show the volume.

---

## Stage 3: Add CDK Nag for Best Practices (2 min)

**[In `app.py`, uncomment these two lines:]**

```python
from cdk_nag import AwsSolutionsChecks
```

```python
cdk.Aspects.of(app).add(AwsSolutionsChecks())
```

**[Then add this block at the bottom of `skywatch/stack.py` (inside the `__init__`)]:**

```python
        # --- CDK Nag Suppressions ---
        NagSuppressions.add_stack_suppressions(self, [
            {"id": "AwsSolutions-IAM4", "reason": "AWS managed Lambda execution role is acceptable"},
            {"id": "AwsSolutions-IAM5", "reason": "Wildcard permissions required for CDK bucket deployment"},
            {"id": "AwsSolutions-L1", "reason": "Python 3.12 is the latest supported by CDK constructs"},
            {"id": "AwsSolutions-DDB3", "reason": "Point-in-time recovery not needed for ephemeral flight data"},
            {"id": "AwsSolutions-S1", "reason": "Access logs not needed for demo"},
            {"id": "AwsSolutions-S10", "reason": "Bucket only accessed via CloudFront OAC (HTTPS)"},
            {"id": "AwsSolutions-CFR1", "reason": "No geo restrictions needed for demo"},
            {"id": "AwsSolutions-CFR2", "reason": "WAF not needed for demo"},
            {"id": "AwsSolutions-CFR3", "reason": "Access logging not needed for demo"},
            {"id": "AwsSolutions-CFR4", "reason": "Default CloudFront TLS policy acceptable for demo"},
            {"id": "AwsSolutions-APIG1", "reason": "API access logging not needed for demo"},
            {"id": "AwsSolutions-APIG4", "reason": "Public API — no auth needed for flight data"},
        ])
```

**[Also add the import at the top of `stack.py`:]**

```python
from cdk_nag import NagSuppressions
```

**[Run:]**
```bash
cdk synth
```

> "CDK Nag checks your infrastructure against AWS best practices — the same rules Solutions Architects use. Our app passes clean. Every finding is either fixed or explicitly suppressed with a reason. Now let's add a feature."

---

## Stage 4: Build the AI Feature — Gets Blocked (2 min)

> "I want Claude to narrate the flights — click a plane, get an AI-generated blurb. We need Bedrock access from our API Lambda."

**[Add `MODEL_ID` to the API Lambda's environment dict:]**

```python
            environment={
                **lambda_env,
                "MODEL_ID": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
            },
```

**[Add this IAM policy right after `secret.grant_read(api_handler)`:]**

```python
        # Give the Lambda permission to call Bedrock
        api_handler.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=["*"],
        ))
```

> "Quick and dirty — give it access to all Bedrock models. Ship it."

**[Run:]**
```bash
cdk synth
```

💥 **CDK Nag ERROR:**
```
[Error at /SkyWatch/Api/ServiceRole/DefaultPolicy/Resource]
AwsSolutions-IAM5[Resource::*]: The IAM entity contains wildcard permissions
and does not have a cdk-nag rule suppression with evidence for those permission.
```

> "Blocked. CDK Nag caught that `Resource: *` gives this Lambda access to every model in Bedrock — not just the one we need. This is the guardrail working. It won't let me deploy an overly permissive policy."

---

## Stage 5: Fix It Right (1 min)

**[Replace the `resources=["*"]` block with:]**

```python
        # Give the Lambda permission to call Bedrock
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

> "Clean. Scoped to exactly the model we need — Claude Haiku. Least privilege."

---

## Stage 6: Deploy and See It Work (1 min)

**[Run:]**
```bash
cdk deploy
```

> "Deploying the AI feature..."

Wait for deploy (~90s). Once done, switch to browser, hard refresh (Cmd+Shift+R), click a flight.

The spotlight panel updates with an AI-generated blurb about the flight.

> "There it is — Claude narrating the sky above PyCon. We went from idea to deployed AI feature in under 10 minutes, and a security guardrail stopped us from shipping a bad IAM policy along the way. That's CDK."

---

## Wrap

> "Python infrastructure, best-practice guardrails, one deploy command. Questions?"

---

## Q&A Cheat Sheet

| Question | Answer |
|----------|--------|
| How much does this cost? | Under $5/day. Lambda + DynamoDB + Bedrock Haiku. |
| Why CDK over Terraform? | Loops, conditionals, type safety, constructs, Nag. All in Python. |
| What's CDK Nag checking? | ~100 AWS Solutions Architect best-practice rules. IAM, encryption, logging, network. |
| Can I add my own rules? | Yes. Custom Nag packs for your org's policies. |
| How do you handle secrets? | Secrets Manager. Nothing in source code. |
