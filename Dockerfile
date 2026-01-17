FROM python:latest

WORKDIR /usr/src/app

RUN python --version
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY telegram_crawler.py .
COPY config.ini .
CMD [ "python", "./telegram_crawler.py" ]