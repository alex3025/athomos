FROM python:latest

WORKDIR /home/alex3025/athomos

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./bot.py" ]
