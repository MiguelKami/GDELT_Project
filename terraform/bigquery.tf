
resource "google_bigquery_dataset" "prep" {
  dataset_id  = "gdelt_prep_${var.environment}"
  description = "GDELT data preparation layer"
  location    = "US"

  labels = {
    environment = var.environment
    layer       = "prep"
  }

}


resource "google_bigquery_dataset" "raw" {
  dataset_id  = "gdelt_raw_${var.environment}"
  description = "GDELT data raw layer"
  location    = "US"

  labels = {
    environment = var.environment
    layer       = "raw"
  }

}

resource "google_bigquery_table" "event" {
  dataset_id = google_bigquery_dataset.prep.dataset_id
  table_id   = "event"

  time_partitioning {
    type = "DAY"
  }

  schema = file("${path.module}/schema/event.json")
}

resource "google_bigquery_table" "mention" {
  dataset_id = google_bigquery_dataset.prep.dataset_id
  table_id   = "mention"

  deletion_protection = local.isprod

  time_partitioning {
    type  = "DAY"
  }

  schema = file("${path.module}/schema/mention.json")

  depends_on = [
    google_bigquery_dataset.prep
  ]
}

resource "google_bigquery_table" "gkg" {
  dataset_id = google_bigquery_dataset.prep.dataset_id
  table_id   = "gkg"

  deletion_protection = local.isprod

  time_partitioning {
    type  = "DAY"
  }

  schema = file("${path.module}/schema/gkg.json")
  
  depends_on = [
    google_bigquery_dataset.prep
  ]
}


resource "google_bigquery_table" "events_external" {
  dataset_id = google_bigquery_dataset.raw.dataset_id
  table_id   = "events_external"

  external_data_configuration {
    autodetect    = true
    source_format = "PARQUET"

    source_uris = [
      "gs://${google_storage_bucket.raw.name}/data/events/*"
    ]

    hive_partitioning_options {
      mode = "CUSTOM"

      source_uri_prefix = "gs://${google_storage_bucket.raw.name}/data/events/{dt:STRING}"

      require_partition_filter = false
    }
  }

  depends_on = [google_bigquery_dataset.raw]
}

resource "google_bigquery_table" "gkg_external" {
  dataset_id = google_bigquery_dataset.raw.dataset_id
  table_id   = "gkg_external"

  external_data_configuration {
    autodetect    = true
    source_format = "PARQUET"

    source_uris = [
      "gs://${google_storage_bucket.raw.name}/data/gkg/*"
    ]

    hive_partitioning_options {
      mode = "CUSTOM"

      source_uri_prefix = "gs://${google_storage_bucket.raw.name}/data/gkg/{dt:STRING}"

      require_partition_filter = false
    }
  }

  depends_on = [google_bigquery_dataset.raw]
}

resource "google_bigquery_table" "mentions_external" {
  dataset_id = google_bigquery_dataset.raw.dataset_id
  table_id   = "mentions_external"

  external_data_configuration {
    autodetect    = true
    source_format = "PARQUET"

    source_uris = [
      "gs://${google_storage_bucket.raw.name}/data/mentions/*"
    ]

    hive_partitioning_options {
      mode = "CUSTOM"

      source_uri_prefix = "gs://${google_storage_bucket.raw.name}/data/mentions/{dt:STRING}"

      require_partition_filter = false
    }
  }

  depends_on = [google_bigquery_dataset.raw]
}