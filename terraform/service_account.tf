
resource "google_service_account" "gdelt_build" {
  project      = var.project_id
  account_id   = "gdelt-build-${var.environment}"
  display_name = "GDELT Build"
}

resource "google_storage_bucket_iam_member" "runtime_creator" {
  bucket = google_storage_bucket.raw.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.gdelt_build.email}"
}

resource "google_storage_bucket_iam_member" "runtime_viewer" {
  bucket = google_storage_bucket.raw.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.gdelt_build.email}"
}

resource "google_service_account_iam_member" "github_runtime_user" {
  service_account_id = google_service_account.gdelt_build.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:gdelt-project@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "gdelt_build_permissions" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/storage.objectViewer",
    "roles/artifactregistry.writer"
  ])

  project = var.project_id
  role    = each.value

  member = "serviceAccount:${google_service_account.gdelt_build.email}"
}

resource "google_service_account_iam_member" "github_build_user" {
  service_account_id = google_service_account.gdelt_build.name
  role               = "roles/iam.serviceAccountUser"

  member = "serviceAccount:gdelt-project@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_cloud_run_service_iam_member" "workflow_invoker" {
  project  = var.project_id
  location = google_cloudfunctions2_function.gdelt_ingestion.location
  service  = google_cloudfunctions2_function.gdelt_ingestion.name

  role   = "roles/run.invoker"
  member = "serviceAccount:${google_service_account.gdelt_build.email}"
}