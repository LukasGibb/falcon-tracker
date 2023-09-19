output "comparer_environment_variables" {
  value = google_cloudfunctions_function.comparer_function.environment_variables
}
output "comparer_bucket_name" {
  value = google_storage_bucket.comparer_bucket.name
}

output "annotation_bucket" {
  value = google_storage_bucket.annotation_bucket.name
}

output "annotation_topic" {
  value = google_pubsub_topic.annotation_event_topic.name
}
