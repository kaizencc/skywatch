#!/usr/bin/env python3
import os
from pathlib import Path

# Load .env file if present (no external dependency needed)
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks

from skywatch.stack import SkywatchStack

app = cdk.App()
SkywatchStack(app, "SkyWatch")

cdk.Aspects.of(app).add(AwsSolutionsChecks())

app.synth()
