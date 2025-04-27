FROM python:3.11

WORKDIR /code

COPY ./requirements.txt ./requirements.txt

RUN pip3 install --upgrade pip

RUN pip3 install -r requirements.txt

COPY . .

CMD ["python", "src/app.py"]
