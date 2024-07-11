FROM python:3.12

# Copy files and install dependencies
WORKDIR /app
COPY . .
RUN python -m pip install -r requirements.txt

# Disable log buffering
ENV PYTHONBUFFERED=1

# Set entrypoint with 'src.daemon' as the default argument
ENTRYPOINT ["python", "-m"]
CMD ["src.daemon"] 
