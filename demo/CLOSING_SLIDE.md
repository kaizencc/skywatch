# AWS CDK — Key Takeaways

## What is CDK?

The AWS Cloud Development Kit lets you define cloud infrastructure in real programming languages — Python, TypeScript, Java, Go — instead of YAML/JSON templates. You get loops, conditionals, type safety, and abstractions.

```
~100 lines of Python  ──cdk synth──▶  1000+ lines of CloudFormation
```

---

## CDK Workflow

| Command | What it does |
|---------|-------------|
| `cdk synth` | Compiles your Python/TS into a CloudFormation template (locally) |
| `cdk diff` | Shows what would change in AWS before you deploy |
| `cdk deploy` | Deploys the stack to your AWS account |
| `cdk destroy` | Tears everything down |

---

## CDK Nag — Best Practice Validation

- Runs ~100 AWS Solutions Architect rules at **synth time** (before deploy)
- Catches: overly permissive IAM, missing encryption, unlogged APIs, open security groups
- Fails the build — bad infrastructure never leaves your laptop
- Suppressions require documented reasons (audit trail)
- Custom rule packs for your organization's policies

```python
from cdk_nag import AwsSolutionsChecks
cdk.Aspects.of(app).add(AwsSolutionsChecks())
```

---

## aws-cdk Skill — AI-Assisted Infrastructure

- Part of the open-source **Agent Toolkit for AWS**
- https://github.com/aws/agent-toolkit-for-aws
- Gives AI coding agents (Claude Code, Codex, Kiro) deep CDK expertise:
  - Construct patterns (L1, L2, L3)
  - IAM grants and least-privilege patterns
  - Deployment troubleshooting
  - Safe refactoring without resource replacement
  - Bootstrap, drift detection, importing resources
- Install: `/plugin install aws-core@claude-plugins-official`

---

## Why CDK?

- **Real programming languages** — Python, TypeScript, Java, Go. Loops, conditionals, type safety.
- **L2/L3 constructs** — High-level abstractions that encode AWS best practices (e.g., `grant_read_write_data()` handles IAM for you)
- **CDK Nag** — Best-practice validation at synth time, before anything deploys
- **aws-cdk skill** — AI agents understand CDK patterns natively
- **One command deploys** — `cdk deploy` handles ordering, dependencies, rollbacks
- **Escape hatches** — Drop to L1 (raw CloudFormation) when you need full control

---

## What We Did Today

1. **Walked the CDK code** — ~100 lines of Python defining 8 AWS services
2. **`cdk synth`** — Compiled Python into 1000+ lines of CloudFormation locally
3. **Loaded the aws-cdk skill** — Gave Claude Code CDK domain expertise
4. **Live-coded a Bedrock feature** — AI agent wrote the Lambda handler + CDK infrastructure
5. **CDK Nag blocked us** — Caught `Resource: *` on the Bedrock IAM policy at synth time
6. **Fixed with least privilege** — Scoped the ARN to the exact model we need
7. **`cdk deploy`** — One command deployed the working AI feature to AWS

---

## Get Started

- **CDK docs**: https://docs.aws.amazon.com/cdk/
- **Agent Toolkit**: https://github.com/aws/agent-toolkit-for-aws
- **This demo**: https://github.com/kaizencc/skywatch
- **CDK Nag**: `pip install cdk-nag`
- **Install the skill**: `/plugin install aws-core@claude-plugins-official`
