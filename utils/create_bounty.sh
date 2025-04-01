#!/bin/bash
# This script sets up the required file structure for a bounty in an existing directory.

set -e

# 1. Read the target directory from user input.
if [ -z "$1" ]; then
  echo "Usage: $0 <target_directory>"
  exit 1
fi

TARGET_DIR="$1"

# 2. Check if the target directory exists.
if [ ! -d "$TARGET_DIR" ]; then
  echo "Error: Directory '$TARGET_DIR' does not exist."
  echo "Please provide an existing directory."
  exit 1
fi

# 3. Check for metadata.json; if missing, create a new one.
METADATA_FILE="$TARGET_DIR/metadata.json"
if [ ! -f "$METADATA_FILE" ]; then
  echo "Creating new metadata.json..."
  cat <<EOF > "$METADATA_FILE"
{
    "target_host": ""
}
EOF
fi

# 5. Check for setup_repo_env.sh; if missing, create it.
SETUP_REPO_ENV="$TARGET_DIR/setup_repo_env.sh"
if [ ! -f "$SETUP_REPO_ENV" ]; then
  echo "Creating setup_repo_env.sh..."
  cat <<'EOF' > "$SETUP_REPO_ENV"
#!/bin/bash
EOF
  chmod +x "$SETUP_REPO_ENV"
fi

# 6. Check or create the 'bounties' folder.
BOUNTIES_DIR="$TARGET_DIR/bounties"
if [ ! -d "$BOUNTIES_DIR" ]; then
  echo "Creating bounties folder..."
  mkdir -p "$BOUNTIES_DIR"
fi

# 6. Determine the next bounty folder name.
#    We look for existing bounty_[x] folders and find the max.
NEXT_BOUNTY_NUM=0
if ls "$BOUNTIES_DIR" | grep -q "bounty_"; then
  MAX_BOUNTY=$(ls "$BOUNTIES_DIR" | grep "bounty_" | sed 's/bounty_//' | sort -n | tail -1)
  NEXT_BOUNTY_NUM=$((MAX_BOUNTY + 1))
fi
NEW_BOUNTY_FOLDER="bounty_${NEXT_BOUNTY_NUM}"

echo "Creating new bounty folder: $NEW_BOUNTY_FOLDER"
mkdir -p "$BOUNTIES_DIR/$NEW_BOUNTY_FOLDER"

# 7. Create the required files and directories in the new bounty folder.
#    7b. exploit_files (with exploit.sh)
EXPLOIT_DIR="$BOUNTIES_DIR/$NEW_BOUNTY_FOLDER/exploit_files"
mkdir -p "$EXPLOIT_DIR"
EXPLOIT_SCRIPT="$EXPLOIT_DIR/exploit.sh"
if [ ! -f "$EXPLOIT_SCRIPT" ]; then
  echo "Creating exploit_files/exploit.sh..."
  cat <<'EOF' > "$EXPLOIT_SCRIPT"
#!/bin/bash
EOF
  chmod +x "$EXPLOIT_SCRIPT"
fi

#    7c. patch_files folder (can be empty)
PATCH_DIR="$BOUNTIES_DIR/$NEW_BOUNTY_FOLDER/patch_files"
mkdir -p "$PATCH_DIR"

#    7d. setup_files with setup_bounty_env.sh
SETUP_BOUNTY_DIR="$BOUNTIES_DIR/$NEW_BOUNTY_FOLDER/setup_files"
mkdir -p "$SETUP_BOUNTY_DIR"
SETUP_BOUNTY_SCRIPT="$SETUP_BOUNTY_DIR/setup_bounty_env.sh"
if [ ! -f "$SETUP_BOUNTY_SCRIPT" ]; then
  echo "Creating setup_files/setup_bounty_env.sh..."
  cat <<'EOF' > "$SETUP_BOUNTY_SCRIPT"
#!/bin/bash
EOF
  chmod +x "$SETUP_BOUNTY_SCRIPT"
fi

#    7e. verify.sh
VERIFY_SCRIPT="$BOUNTIES_DIR/$NEW_BOUNTY_FOLDER/verify.sh"
if [ ! -f "$VERIFY_SCRIPT" ]; then
  echo "Creating verify.sh..."
  cat <<'EOF' > "$VERIFY_SCRIPT"
#!/bin/bash
EOF
  chmod +x "$VERIFY_SCRIPT"
fi

echo "Done! The directory '$TARGET_DIR' has been prepared, and bounty $NEXT_BOUNTY_NUM has been created."
