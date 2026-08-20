# API examples

Assume the service is running with the default Compose mapping on `localhost:8001`.
Set `API_PORT=8000` in `.env` if port 8000 is available on your machine, then
replace `8001` below with `8000`.

## Health

```bash
curl http://localhost:8001/api/health
```

## Upload

```bash
curl -F "file=@input.mp4" http://localhost:8001/api/videos
```

Example response:

```json
{
  "id": "4d3c1c16-e03f-4b0e-8e59-cb84dd1fbc37",
  "original_name": "input.mp4",
  "status": "uploaded",
  "progress": 0.0,
  "bag_count": 0,
  "anomaly_count": 0
}
```

## Start

```bash
curl -X POST http://localhost:8001/api/jobs/4d3c1c16-e03f-4b0e-8e59-cb84dd1fbc37/start
```

The response is HTTP 202. Inference continues in the Celery worker after the request completes.

## Poll

```bash
curl http://localhost:8001/api/jobs/4d3c1c16-e03f-4b0e-8e59-cb84dd1fbc37
```

## Anomalies

```bash
curl http://localhost:8001/api/jobs/4d3c1c16-e03f-4b0e-8e59-cb84dd1fbc37/anomalies
```

## Download

```bash
curl -OJ http://localhost:8001/api/jobs/4d3c1c16-e03f-4b0e-8e59-cb84dd1fbc37/result
```
