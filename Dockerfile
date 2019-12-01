FROM python:alpine3.7
COPY ./app /app
WORKDIR /app
RUN pip install -r requirements.txt
EXPOSE 7654
CMD python ./udp2influx.py
