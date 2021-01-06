python3 main.py
while [ $? -ne 1 ]
do
git pull
python3 main.py
done