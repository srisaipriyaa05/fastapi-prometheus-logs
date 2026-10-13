# FastAPI Prometheus + Structured JSON Logs

## Endpoints
- `GET /work?n=K` → `{"email":"...","done":K}`
- `GET /metrics` → live Prometheus exposition, including `http_requests_total`
- `GET /healthz` → `{"status":"ok","uptime_s":...}`
- `GET /logs/tail?limit=N` → recent structured JSON request logs

Every HTTP request is counted by middleware, including requests to `/metrics`, `/healthz`, `/work`, and `/logs/tail`. Each request creates a JSON log entry with `level`, `ts`, `path`, and `request_id`. The last 1,000 entries are retained in process memory.

Default email: `24f2007077@ds.study.iitm.ac.in`. Set `USER_EMAIL` in deployment environment if needed.

## Recommended deployment: Railway
Use this Dockerfile-backed project on Railway for a continuously running service:
1. Upload these files to a new GitHub repository: `Dockerfile`, `api/index.py`, `requirements.txt`, and `README.md`.
2. Create a Railway service from that repo. Railway will detect and build the Dockerfile.
3. Generate a public domain under service Settings → Networking.
4. Test `/healthz`, `/work?n=5`, `/metrics`, and `/logs/tail?limit=10`.
5. Submit the base URL without a path.

## Alternative: Vercel
`vercel.json` is included for convenience. However, Vercel serverless functions may run on different instances, and process-local counters/log tails can reset or vary by instance. Since this assignment explicitly checks that live counters and request logs reflect sequential traffic, a continuously running single-instance service is the safer deployment choice.

## Smoke tests
```bash
curl -i 'https://YOUR-DOMAIN/healthz'
curl -i 'https://YOUR-DOMAIN/work?n=5'
curl 'https://YOUR-DOMAIN/metrics'
curl 'https://YOUR-DOMAIN/logs/tail?limit=10'
```
