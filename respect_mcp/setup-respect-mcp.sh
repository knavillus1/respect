#!/bin/bash

# ReSpecT MCP Server Setup and Launch Script
# Usage: ./setup-respect-mcp.sh [DOC_REPO_ROOT] [PROVISIONAL_DOC_STORE] [DEBUG_MODE]
#
# This script sets up the virtual environment, installs dependencies,
# configures environment variables, and starts the ReSpecT MCP server.
#
# Arguments:
#   DOC_REPO_ROOT: Path to the document repository root (required)
#   PROVISIONAL_DOC_STORE: Path to the provisional document store (required)
#   DEBUG_MODE: Debug mode flag (optional, defaults to "false")
#
# Example usage for Codex configuration:
# [mcp_servers.respect_manager]
# command = "/path/to/setup-respect-mcp.sh"
# args = ["/path/to/doc/repo", "/path/to/provisional/store", "false"]

set -e  # Exit on any error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Parse command line arguments
DOC_REPO_ROOT="${1:-}"
PROVISIONAL_DOC_STORE="${2:-}"
DEBUG_MODE="${3:-false}"

# Validate required arguments
if [ -z "$DOC_REPO_ROOT" ]; then
    echo "Error: DOC_REPO_ROOT argument is required" >&2
    echo "Usage: $0 <DOC_REPO_ROOT> <PROVISIONAL_DOC_STORE> [DEBUG_MODE]" >&2
    exit 1
fi

if [ -z "$PROVISIONAL_DOC_STORE" ]; then
    echo "Error: PROVISIONAL_DOC_STORE argument is required" >&2
    echo "Usage: $0 <DOC_REPO_ROOT> <PROVISIONAL_DOC_STORE> [DEBUG_MODE]" >&2
    exit 1
fi

# Validate that the paths exist or can be created
if [ ! -d "$DOC_REPO_ROOT" ]; then
    echo "Error: DOC_REPO_ROOT directory does not exist: $DOC_REPO_ROOT" >&2
    exit 1
fi

if [ ! -d "$PROVISIONAL_DOC_STORE" ]; then
    echo "Warning: PROVISIONAL_DOC_STORE directory does not exist, creating: $PROVISIONAL_DOC_STORE" >&2
    mkdir -p "$PROVISIONAL_DOC_STORE"
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install uv first." >&2
    echo "Visit: https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
fi

# Setup virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

# Install dependencies
echo "Installing dependencies..."
uv sync

# Set environment variables
export RESPECT_DOC_REPO_ROOT="$DOC_REPO_ROOT"
export RESPECT_PROVISIONAL_DOC_STORE="$PROVISIONAL_DOC_STORE"
export DEBUG_MODE="$DEBUG_MODE"

# Log the configuration being used
echo "Starting ReSpecT MCP Server with configuration:" >&2
echo "  RESPECT_DOC_REPO_ROOT=$RESPECT_DOC_REPO_ROOT" >&2
echo "  RESPECT_PROVISIONAL_DOC_STORE=$RESPECT_PROVISIONAL_DOC_STORE" >&2
echo "  DEBUG_MODE=$DEBUG_MODE" >&2

# Start the MCP server
echo "Starting ReSpecT MCP Server..." >&2
exec uv run python -m respect_mcp_server.server
