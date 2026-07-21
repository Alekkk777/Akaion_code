output "api_url" {
  description = "URL pubblico del servizio api"
  value       = google_cloud_run_v2_service.api.uri
}

output "worker_url" {
  description = "URL del servizio worker (privato, solo per riferimento/debug)"
  value       = google_cloud_run_v2_service.worker.uri
}

output "artifact_registry_repo" {
  description = "Path del repository Docker su Artifact Registry"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}
