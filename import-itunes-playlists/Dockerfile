FROM python:3

COPY . /code
WORKDIR /code

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 32400

CMD [ "python", "import-itunes-playlist.py" ]
