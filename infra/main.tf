data "google_project" "current" {
  project_id = var.project_id
}

locals {
  required_services = [
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "firestore.googleapis.com",
    "pubsub.googleapis.com",
    "iam.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each           = toset(local.required_services)
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# --- Artifact Registry: destinazione delle immagini Docker (build/push gestiti da Cloud Build) ---

resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = "akaion-lifeos"
  format        = "DOCKER"
  description   = "Immagini Docker per akaion-api e akaion-worker"

  depends_on = [google_project_service.apis]
}

# --- Firestore: persistenza dei workflow ---

resource "google_firestore_database" "default" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.firestore_location
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.apis]
}

# --- Pub/Sub: canale workflow.created tra api e worker ---

resource "google_pubsub_topic" "workflow_created" {
  name = "workflow-created"

  depends_on = [google_project_service.apis]
}

# Service account dedicato che la push subscription usa per autenticarsi verso il worker
resource "google_service_account" "pubsub_invoker" {
  account_id   = "akaion-pubsub-invoker"
  display_name = "SA push subscription -> akaion-worker"
}

# Pub/Sub deve poter generare token OIDC per conto di questa SA
resource "google_project_iam_member" "pubsub_token_creator" {
  project = var.project_id
  role    = "roles/iam.serviceAccountTokenCreator"
  member  = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# --- Cloud Run: servizio api (pubblico) ---

resource "google_cloud_run_v2_service" "api" {
  name                = "akaion-api"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    containers {
      image = var.api_image

      env {
        name  = "USE_PUBSUB"
        value = "true"
      }
      env {
        name  = "USE_FIRESTORE"
        value = "true"
      }
      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }
      env {
        name  = "PUBSUB_TOPIC"
        value = google_pubsub_topic.workflow_created.name
      }
      env {
        name  = "ENVIRONMENT"
        value = "prod"
      }
    }
  }

  # L'immagine viene aggiornata da Cloud Build ad ogni deploy applicativo;
  # Terraform continua a gestire il resto della configurazione del servizio
  # senza riportarla al placeholder ad ogni apply.
  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service_iam_member" "api_public" {
  location = google_cloud_run_v2_service.api.location
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# --- Cloud Run: servizio worker (privato, invocabile solo dalla push subscription) ---

resource "google_cloud_run_v2_service" "worker" {
  name                = "akaion-worker"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    containers {
      image = var.worker_image

      env {
        name  = "USE_PUBSUB"
        value = "true"
      }
      env {
        name  = "USE_FIRESTORE"
        value = "true"
      }
      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }
      env {
        name  = "ENVIRONMENT"
        value = "prod"
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service_iam_member" "worker_invoker" {
  location = google_cloud_run_v2_service.worker.location
  name     = google_cloud_run_v2_service.worker.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.pubsub_invoker.email}"
}

# --- Push subscription: consegna workflow.created al worker con auth OIDC ---

resource "google_pubsub_subscription" "workflow_created_sub" {
  name  = "workflow-created-sub"
  topic = google_pubsub_topic.workflow_created.name

  ack_deadline_seconds = 60

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.worker.uri}/pubsub/push"

    oidc_token {
      service_account_email = google_service_account.pubsub_invoker.email
    }
  }

  depends_on = [
    google_cloud_run_v2_service_iam_member.worker_invoker,
    google_project_iam_member.pubsub_token_creator,
  ]
}
