#!/usr/bin/env python
# MISE description="Downgrade Alembic to the specified migration"
# USAGE arg "<revision>" help="If a number, the number of migrations to revert. Otherwise, the identifier of the migration." default="1"

import os
import subprocess

revision = os.getenv("usage_revision") or "1"
if revision.isdecimal():
    subprocess.run(["uv", "run", "alembic", "downgrade", f"-{revision}"])
else:
    subprocess.run(["uv", "run", "alembic", "downgrade", revision])
