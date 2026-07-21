variable "project_id" {
  description = "ID del progetto GCP di destinazione"
  type        = string
}

variable "region" {
  description = "Regione per Cloud Run e Artifact Registry"
  type        = string
  default     = "europe-west1"
}

variable "firestore_location" {
  description = "Location Firestore (multi-regione o regione, indipendente da var.region)"
  type        = string
  default     = "eur3"
}

variable "api_image" {
  description = "Immagine per il servizio api. Al primo apply un placeholder basta: Cloud Build aggiorna l'immagine reale nei deploy successivi (Terraform ignora i cambi a questo campo, vedi lifecycle)."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "worker_image" {
  description = "Immagine per il servizio worker. Stesso discorso di api_image."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}
