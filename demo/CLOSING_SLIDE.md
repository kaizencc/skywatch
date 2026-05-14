# AWS CDK — Key Takeaways

## What We Did Today

1. **Walked the CDK code** — ~100 lines of Python defining 8 AWS services
2. **`cdk synth`** — Compiled Python into 1000+ lines of CloudFormation locally
3. **Loaded the aws-cdk skill** — Gave Claude Code CDK domain expertise
4. **Live-coded a Bedrock feature** — AI agent wrote the Lambda handler + CDK infrastructure
5. **CDK Nag blocked us** — Caught `Resource: *` on the Bedrock IAM policy at synth time
6. **Fixed with least privilege** — Scoped the ARN to the exact model we need
7. **`cdk deploy`** — One command deployed the working AI feature to AWS

---

## Why CDK?

- **Real programming languages** — Python, TypeScript, Java, Go. Loops, conditionals, type safety.
- **L2/L3 constructs** — High-level abstractions that encode AWS best practices (e.g., `grant_read_write_data()` handles IAM for you)
- **CDK Nag** — Best-practice validation at synth time, before anything deploys
- **aws-cdk skill** — AI agents understand CDK patterns natively
- **One command deploys** — `cdk deploy` handles ordering, dependencies, rollbacks
- **Escape hatches** — Drop to L1 (raw CloudFormation) when you need full control

```
~100 lines of Python  ──cdk synth──▶  1000+ lines of CloudFormation
```

---

## Get Started

- **CDK docs**: https://docs.aws.amazon.com/cdk/
- **Agent Toolkit**: https://github.com/aws/agent-toolkit-for-aws
- **This demo**: https://github.com/kaizencc/skywatch
- **CDK Nag**: `pip install cdk-nag`
- **Install the skill**: `/plugin install aws-core@claude-plugins-official`
