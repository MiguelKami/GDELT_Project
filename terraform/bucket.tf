
resource "google_storage_bucket" "raw" {
  name     = "${var.project_id}-rawgdelt-${var.environment}"
  location = "US"

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
}

resource "google_storage_bucket" "code" {
  name     = "${var.project_id}-codegdelt-${var.environment}"
  location = "US"

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
}