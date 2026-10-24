
resource "google_storage_bucket" "raw" {
  name     = "${var.project_id}-rawGDELT-${var.environment}"
  location = "US"

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
}
