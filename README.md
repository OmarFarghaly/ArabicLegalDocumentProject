# Run the app with Docker Compose

## 1. Configure Hugging Face token

In PowerShell, create your local environment file:

```powershell
Copy-Item .env.example .env
```

Open `.env` and set your token:

```dotenv
HF_TOKEN=hf_your_token_here
```

Or set it in your terminal before starting Compose.

Windows PowerShell (current terminal session):

```powershell
$env:HF_TOKEN = "hf_your_token_here"
```

Linux/macOS (current terminal session):

```bash
export HF_TOKEN="hf_your_token_here"
```

Keep `.env` private; do not commit or share it. A token is optional for public
models, but can help if Hugging Face requires authentication or rate-limits
downloads.

## 2. Start the app

From the project directory:

```powershell
docker compose up --build -d
```

On first start, Docker downloads the images and models, then builds the Qdrant
index. This can take several minutes. Follow startup with:

```powershell
docker compose ps -a
docker compose logs -f indexer backend
```

When the backend is running, open
[http://localhost:4000/docs](http://localhost:4000/docs) to try the API.

Stop the app with:

```powershell
docker compose down
```
