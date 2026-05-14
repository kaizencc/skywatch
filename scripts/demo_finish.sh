#!/bin/bash
# Jump to final demo state (stage 3, AI working) and deploy
set -e
cd "$(dirname "$0")/.."

cp demo/stages/stack_stage3.py skywatch/stack.py
cp demo/stages/handler_after.py skywatch/lambdas/api/handler.py

cdk deploy --require-approval never
