#!/bin/bash
TMP_DIR="$1"

mkdir -p "$TMP_DIR"
cp -R original_files/* "$TMP_DIR"

cd "$TMP_DIR"
