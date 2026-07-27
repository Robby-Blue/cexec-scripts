FROM alpine:3.24

WORKDIR /app

RUN apk add python3 py3-pip

RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"

COPY requirements.txt .

RUN pip install -r requirements.txt