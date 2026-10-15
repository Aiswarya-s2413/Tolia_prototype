#!/bin/bash
# Script to connect local Mac Ollama (Qwen 3.8) to the hosted Tolia site

echo "Checking local Ollama..."
if ! curl -s http://127.0.0.1:11434/api/tags > /dev/null; then
    echo "Starting Ollama..."
    ollama serve > /dev/null 2>&1 &
    sleep 2
fi

echo "Setting up reverse tunnel to hosted site..."
pkill -f "11435:127.0.0.1:11434" 2>/dev/null || true

ssh -N -f -R 11435:127.0.0.1:11434 \
    -i /Users/aiswarya/Downloads/flashnetdevkey \
    -o StrictHostKeyChecking=no \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=3 \
    -o ExitOnForwardFailure=yes \
    mohit@168.144.27.187

echo "✅ Mac Tunnel is active! Hosted site (https://tolia.168.144.27.187.sslip.io/) is now running on local Mac Qwen 3.8."
