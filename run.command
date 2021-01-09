#!/bin/bash
python3 main.py

while [ $? -ne 1 ]
do
    git pull --no-commit --no-ff $1
    if [ $? -ne 0 ]; then
        echo "conflict occurred aborting"
        git merge --abort
    else
        echo "no conflict"
        git commit
    fi
    python3 main.py
done