
resource "google_service_account" "gdelt_build" {
  project      = var.project_id
  account_id   = "gdelt-build-${var.environment}"
  display_name = "GDELT Build"
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
