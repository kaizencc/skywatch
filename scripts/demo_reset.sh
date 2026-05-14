#!/bin/bash
# Reset to demo start state (stage 1, no AI) and deploy
set -e
cd "$(dirname "$0")/.."

cp demo/stages/stack_stage1.py skywatch/stack.py
cp demo/stages/handler_before.py skywatch/lambdas/api/handler.py

cdk deploy --require-approval never
