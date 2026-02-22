#!/bin/sh
# Run from repo root to install local git hooks.
cp .githooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
echo "Git hooks installed."
