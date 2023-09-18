import os
import youtube_dl
from google.cloud import storage
from google.cloud import pubsub_v1

import functions_framework

@functions_framework.http
def handle(request):
    # This function should call the Google Vision/Video API and return
    
    # Do stuff here
    print("Annotation function called...")
        # Annotate
        # Compare

    project_id=os.getenv('GCP_PROJECT')
    topic=os.getenv('NOTIFY_TOPIC')
    publish_message(project_id, topic)

    return "ok", 200

def publish_message(project_id, topic_name):
    publisher = pubsub_v1.PublisherClient()
    topic_name = 'projects/{project_id}/topics/{topic}'.format(
        project_id=project_id,
        topic=topic_name,
    )
    print("publishing message to topic: {}".format(topic_name))
    future = publisher.publish(topic_name, b'hello from annotation func')
    future.result()