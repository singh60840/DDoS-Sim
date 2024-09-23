#!/bin/sh

# pip install flask psutil aiohttp

if sudo lsof -t -i:8080 > /dev/null; then
    echo "Killing process on port 8080..."
    sudo kill -9 $(sudo lsof -t -i:8080)
else
    echo "No process running on port 8080."
fi

python ddos-lite.py

python extract-data.py

python analysis.py