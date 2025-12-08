#!/bin/bash

# Function to kill the backend when the script exits
cleanup() {
    echo "Shutting down backend..."
    kill $BACKEND_PID
}

# the trap to call cleanup on exit (Ctrl+C)
trap cleanup EXIT

echo "🚀 Starting AI Researcher..."

# Start the FastAPI backend in the background
python agent.py &
BACKEND_PID=$!

echo "⏳ Waiting for backend to start..."
sleep 5  # Give Uvicorn a few seconds to boot up

# 2. Start the Streamlit frontend
echo "🎨 Starting Frontend..."
streamlit run app.py