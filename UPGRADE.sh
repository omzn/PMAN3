#!/bin/bash

echo "Welcome to PMAN2 -> PMAN3 updater script."
echo "This script automatically converts old PMAN 2.x csv data to PMAN 3.x database."
echo
echo "Please input user-specific information."
echo
echo "(Step 1) Where is your 'bibdat.csv'?"
echo "Specify path to bibdat.csv. (ex. /path/to/pman2/data/bibdat.csv)"
echo
read PATH_BIBDAT
if [ -e $PATH_BIBDAT ]; then
    echo "[OK] file $PATH_BIBDAT exists."
else 
    echo "[NG] file $PATH_BIBDAT does not exist."
    exit
fi
echo
echo "(Step 2) Where is your 'category.txt'?"
echo "Specify path to category.txt. (ex. /path/to/pman2/data/category.txt)"
echo
read PATH_CATEGORY
if [ -e $PATH_CATEGORY ]; then
    echo "[OK] file $PATH_CATEGORY exists."
else 
    echo "[NG] file $PATH_CATEGORY does not exist."
    exit
fi
echo
echo "(Step 3) Which directory are your PDF files in?"
echo "Specify directory where your PDFs are in. (ex. /path/to/pman2/data/pdf)"
echo
read DIR_PDF
if [ -d $DIR_PDF ]; then
    echo "[OK] directory $DIR_PDF exists."
else 
    echo "[NG] directory $DIR_PDF does not exist."
    exit
fi
echo
echo "Inserting database ..."
perl ./convertDB.pl $PATH_BIBDAT $PATH_CATEGORY $DIR_PDF
echo
echo "Done."
