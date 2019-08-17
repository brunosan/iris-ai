FROM python:3.6-slim-stretch

RUN apt update && apt install --no-install-recommends -y python3-dev gcc build-essential

ADD requirements.txt requirements.txt
RUN pip install --no-cache-dir spacy -r requirements.txt

COPY app app/

RUN python app/server.py

EXPOSE 8080

CMD ["python", "app/server.py", "serve"]
