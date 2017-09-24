FROM python:3.6

RUN mkdir -p /usr/src/app

WORKDIR /usr/src/app

COPY . .
RUN pip install -e .
EXPOSE 8085
CMD ["python", "-m swamp", "--port", "8080"]

