#!/bin/bash

# Run preprocessing on the css files by replacing desired colors with colors
# from the specified color palette
./css-process.sh

# Run the server normally
echo "running server..."
python classify.py
