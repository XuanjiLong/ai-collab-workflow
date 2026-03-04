#!/bin/bash
# Install ai-collab-workflow into your project

set -e

TARGET_DIR="${1:-.workflow}"

echo "Installing ai-collab-workflow to $TARGET_DIR..."

mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

# Download from GitHub
if command -v curl &> /dev/null; then
    curl -sL https://github.com/XuanjiLong/ai-collab-workflow/archive/main.tar.gz | tar xz --strip-components=1 ai-collab-workflow-main/{docs,schemas,scripts,AGENTS.md}
elif command -v wget &> /dev/null; then
    wget -qO- https://github.com/XuanjiLong/ai-collab-workflow/archive/main.tar.gz | tar xz --strip-components=1 ai-collab-workflow-main/{docs,schemas,scripts,AGENTS.md}
else
    echo "Error: curl or wget required"
    exit 1
fi

echo "✓ Installed to $TARGET_DIR"
echo ""
echo "Next steps:"
echo "1. Add to your CLAUDE.md or .cursorrules:"
echo "   ## Workflow Protocol"
echo "   Follow $TARGET_DIR/AGENTS.md for coding tasks"
echo ""
echo "2. Read $TARGET_DIR/docs/DISPATCH.md for usage"
