# Emergency Restore

If live coding goes south, run this to redeploy the fully working app:

```bash
cp demo/stages/stack_stage3.py skywatch/stack.py
cp demo/stages/handler_after.py skywatch/lambdas/api/handler.py
cdk deploy --require-approval never
```

This deploys the complete app with AI spotlight, scoped Bedrock permissions, and CDK Nag passing clean. Takes ~90 seconds.

## Backup Files Reference

```bash
# Stack stages:
cp demo/stages/stack_stage1.py skywatch/stack.py  # Base app (no AI, Nag enabled)
cp demo/stages/stack_stage2.py skywatch/stack.py  # + AI with Resource:* (Nag BLOCKS)
cp demo/stages/stack_stage3.py skywatch/stack.py  # + AI with scoped ARN (Nag passes)

# Handler files:
cp demo/stages/handler_before.py skywatch/lambdas/api/handler.py  # Without AI
cp demo/stages/handler_after.py skywatch/lambdas/api/handler.py   # With AI
```
