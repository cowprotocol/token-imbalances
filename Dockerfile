FROM python:3.12
WORKDIR /app
COPY . /app
RUN python -m pip install -r requirements.txt
ENV PYTHONBUFFERED=1 
CMD ["python", "-m", "src.daemon"]
