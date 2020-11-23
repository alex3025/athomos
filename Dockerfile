FROM python:latest

WORKDIR .

COPY requirements.txt ./
RUN apt update && apt -y install ffmpeg
RUN pip install -r requirements.txt

COPY . .

CMD [ "python", "./bot.py" ]
