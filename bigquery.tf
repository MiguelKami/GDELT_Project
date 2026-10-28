
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

  deletion_protection = local.isprod

  time_partitioning {
    type  = "DAY"
    field = "source_minute"
  }

  schema = file("${path.module}/schema/event.json")
}

resource "google_bigquery_table" "mention" {
  dataset_id = google_bigquery_dataset.prep.dataset_id
  table_id   = "mention"

  deletion_protection = local.isprod

  time_partitioning {
    type  = "DAY"
    field = "source_minute"
  }

  schema = file("${path.module}/schema/mention.json")
}

resource "google_bigquery_table" "gkg" {
  dataset_id = google_bigquery_dataset.prep.dataset_id
  table_id   = "gkg"

  deletion_protection = local.isprod

  time_partitioning {
    type  = "DAY"
    field = "source_minute"
  }

  schema = file("${path.module}/schema/gkg.json")
}
