FROM python:3.10

WORKDIR /app

COPY requirements.txt packages.txt ./


RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

COPY youtube_downloader_app.py ./

EXPOSE 8000

CMD ["streamlit", "run", "youtube_downloader_app.py", "--server.port=8000", "--server.address=0.0.0.0"]