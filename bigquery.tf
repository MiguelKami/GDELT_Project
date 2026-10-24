
resource "google_bigquery_dataset" "prep" {
  dataset_id  = "gdelt_prep_${var.environment}"
  description = "GDELT data preparation layer"
  location    = "US"

  labels = {
    environment = var.environment
    layer       = "prep"
  }
}

resource "google_bigquery_table" "event" {
  dataset_id = google_bigquery_dataset.prep.dataset_id
  table_id   = "event"

  time_partitioning {
    type  = "DAY"
    field = "source_minute"
  }

  schema = file("${path.module}/schemas/event.json")
}
