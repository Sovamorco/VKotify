FROM python:3.10-alpine

RUN apk add --no-cache git

COPY requirements.txt .
RUN python -m pip install -r requirements.txt

COPY . /vkotify
WORKDIR /vkotify

ENTRYPOINT ["python", "-u", "main.py"]
