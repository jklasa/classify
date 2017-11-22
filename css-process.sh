#!/bin/bash

# Run preprocessing on the css files by replacing desired colors with colors
# from the specified color palette
echo -n "preprocessing css files... "

if [ $# -ge 1 ]; then
    PALETTE="color_palettes/${1}"
else
    PALETTE="color_palettes/default_palette.csv"
fi

DIR="static/css/"
TEMP_FILE=".processing.tmp"
PREFIX="post-"

# Process all files in the css directory
CSS_FILES=$(ls $DIR)
for FILE in $CSS_FILES; do

    # Ignore already processed files
    if echo $FILE | egrep "^${PREFIX}.*$" &> /dev/null; then
        continue
    fi

    # Iterate through all colors in the palette
    INPUT=$FILE
    while IFS=, read -r MACRO COLOR; do
        
        # Perform the replace
        cp ${DIR}${INPUT} ${DIR}${TEMP_FILE}
        sed "/[ :]${MACRO}[ ;,\n]/ { s/${MACRO}/${COLOR}/g; }" ${DIR}${TEMP_FILE} > ${DIR}${PREFIX}${FILE}

        # If the input file is still the original file, update it to be the
        # already partially-processed file
        if [ ${INPUT} == ${FILE} ]; then
            INPUT=${PREFIX}${INPUT}
        fi
    done < $PALETTE
done

rm ${DIR}${TEMP_FILE}
echo done
