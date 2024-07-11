FROM python:3.12
COPY requirements.txt .
RUN python -m pip install -r requirements.txt
COPY . .
ENV PYTHONBUFFERED=1
ENTRYPOINT ["python", "-m"]
