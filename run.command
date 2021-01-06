python main.py
while [ $? -ne 1 ]
do
git pull
python main.py
done