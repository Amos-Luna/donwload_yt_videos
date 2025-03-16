# SIMPLE AND MONOLITHIC CODE

Proof of Concept TY_URL to MP4 or WAV

# INSTALL STEPS

1. Build Image:
   `docker build -t youtube_downloader .`

2. Execute Container:
   `docker run --name youtube_downloader_webapp -p 8000:8000 youtube_downloader`

3. Open this URL in Google Chrome:
   `http://localhost:8000`
