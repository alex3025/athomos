FROM python:3.10-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PIP_NO_CACHE_DIR=1

WORKDIR /athomos

RUN apk add --no-cache git

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

VOLUME ["/athomos/logs"]

CMD ["python", "bot.py"]
