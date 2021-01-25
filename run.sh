#!/bin/bash
runbot="python3 main.py"
usebash=false

if [ "$#" -gt  0 ]; then
    if [ "$1" -eq "-g"]; then
        usebash=true
    else
        runbot='python3 main.py "$1"'
    fi

    if [ "$#" -gt  1 ]; then
        if [ "$2" -eq "-g"]; then
            usebash=true
        else
            runbot='python3 main.py "$2"'
        fi
    fi
fi

eval "$runbot"

while [ $? -ne 1 ] do
    if [ $usebash = true ] && [ $? -eq 2 ]; then
        git pull --no-commit --no-ff
        if [ $? -ne 0 ]; then
            echo "conflict occurred, aborting"
            git merge --abort
        else
            echo "no conflict, merging"
            git commit
        fi
    fi
    eval "$runbot"
done
