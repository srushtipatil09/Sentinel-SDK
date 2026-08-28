# Deploying Sentinel AI to Google Cloud

This guide walks through enabling the required Google Cloud APIs, provisioning resources, and deploying via Cloud Build to Cloud Run.

## Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed and authenticated
- A GCP project with billing enabled
- The `gcloud` CLI configured: `gcloud config set project YOUR_PROJECT_ID`

## 1. Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  bigquery.googleapis.com \
  pubsub.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com
```

## 2. Create BigQuery Dataset

```bash
bq --location=us-central1 mk \
  --dataset \
  --description="Sentinel AI telemetry warehouse" \
  YOUR_PROJECT_ID:sentinelai
```

> The telemetry table and ARIMA+ model are created automatically on first startup when `BIGQUERY_ENABLED=true`.

## 3. Create Pub/Sub Topics

```bash
gcloud pubsub topics create telemetry-events
gcloud pubsub topics create incident-events
gcloud pubsub topics create ai-rca-events
```

> Topics are also auto-created on startup when `PUBSUB_ENABLED=true`, but pre-creating ensures IAM is ready.

## 4. Initialise Firestore (Native Mode)

```bash
gcloud firestore databases create --location=us-central1
```

## 5. Store Secrets in Secret Manager

```bash
echo -n "your-gemini-api-key" | gcloud secrets create GEMINI_API_KEY --data-file=-
echo -n "postgresql+asyncpg://..." | gcloud secrets create DATABASE_URL --data-file=-
echo -n "your-secret-key-32bytes" | gcloud secrets create SECRET_KEY --data-file=-
```

Grant the Cloud Run service account access:

```bash
SA=$(gcloud iam service-accounts list --filter="displayName:Compute Engine default" --format="value(email)")
for SECRET in GEMINI_API_KEY DATABASE_URL SECRET_KEY; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:$SA" \
    --role="roles/secretmanager.secretAccessor"
done
```

## 6. Deploy via Cloud Build

```bash
gcloud builds submit \
  --config cloudbuild.yaml \
  --substitutions=_REGION=us-central1,_SERVICE_NAME=sentinelai-backend
```

This will:
1. Build the Docker image
2. Push to Google Container Registry
3. Deploy to Cloud Run with all GCP toggles enabled

## 7. Verify Deployment

```bash
# Get the deployed URL
URL=$(gcloud run services describe sentinelai-backend --region=us-central1 --format="value(status.url)")

# Health check
curl "$URL/health"

# Root endpoint
curl "$URL/"
```

## Running Tests

```bash
# All GCP toggles default to false — tests work without credentials
cd "Sentinel AI"
pip install -r requirements.txt
pytest -q
```

## Environment Variables Reference

See [`.env.example`](../.env.example) for the full list of configuration variables including all GCP toggles.
