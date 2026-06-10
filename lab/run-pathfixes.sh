#!/bin/sh

# Unset LD_LIBRARY_PATH
unset LD_LIBRARY_PATH

# Save the original PATH
ORIGINAL_PATH=${PATH}

# Modify PATH to exclude certain directories
NEW_PATH=$(echo ${PATH} | sed -e "s-:/mnt.*--")
export PATH=${NEW_PATH}

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