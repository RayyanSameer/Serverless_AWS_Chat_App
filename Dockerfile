FROM python:3.11-slim
WORKDIR /src
COPY . .
RUN apt-get update 
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["python", "app.py"]