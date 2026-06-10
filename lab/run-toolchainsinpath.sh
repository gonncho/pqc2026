#!/bin/sh

# Save the original PATH
ORIGINAL_PATH=${PATH}

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
OPTEE_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/../optee" && pwd)"

# Add custom toolchain paths to PATH
export PATH="$OPTEE_DIR/toolchains/aarch32/bin:$PATH"
export PATH="$OPTEE_DIR/toolchains/aarch64/bin:$PATH"

# Check if a command is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <command>"
    export PATH=${ORIGINAL_PATH}
    exit 1
fi

# Execute the command passed as an argument
eval "$@"

# Restore the original PATH
export PATH=${ORIGINAL_PATH}
