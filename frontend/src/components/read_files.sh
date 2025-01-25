#!/bin/bash

find . -type f -name "*.js*" -print0 | while IFS= read -r -d '' file; do
    echo "File: $file"
    echo "Contents:"
    cat "$file"
    echo "----------------------------------------"
done
