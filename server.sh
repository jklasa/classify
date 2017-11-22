#!/bin/bash

# Run preprocessing on the css files by replacing desired colors with colors
# from the specified color palette

if [ $# -ge 1 ]; then
    PALETTE=$1
else
    PALETTE="default_palette.csv"
fi

./css-process.sh $PALETTE

# Run the server normally
echo "running server..."
python classify.py
