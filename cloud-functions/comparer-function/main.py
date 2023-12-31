import cv2
import numpy as np
import os

import youtube_dl
from google.cloud import storage
from google.cloud import pubsub_v1


import functions_framework

@functions_framework.http
def handle(request):
    """handle a request to the function"""

    url = request.get_json().get('video_url', None)
    if url is None:
        return 'No url provided', 400

    print("calling get_frame function")
    latest_frame_path = get_frame(url)
    if latest_frame_path is None:
        return 'No frame retrieved', 400

    bucket_name = os.environ.get('BUCKET_NAME', None)
    if bucket_name is None:
        return 'No bucket name set', 400

    previous_frame_path = download_blob(bucket_name, 'previous_frame.jpg')
    if previous_frame_path is not None:

        percentage = compare(latest_frame_path, previous_frame_path)
        if percentage > float(os.environ.get('PERCENTAGE_DIFF', 10)):
            project_id=os.getenv('GCP_PROJECT')
            topic=os.getenv('ANNOTATION_TOPIC')
            publish_message(project_id, topic, url)

        else:
            print("no annotation needed")

    print("uploading latest frame")
    upload_blob(bucket_name, latest_frame_path, 'previous_frame.jpg')

    return "ok", 200


def get_frame(url):
    """get the latest frame from the yt video"""

    ydl_opts = {
         'nocheckcertificate': True
    }

    ydl = youtube_dl.YoutubeDL(ydl_opts)
    info_dict = ydl.extract_info(url, download=False)
    formats = info_dict.get('formats', None)

    # Find specific URL for 1920x1080 if available to keep things consistent
    media_url = ''
    for f in formats:
        if '1920x1080' in f.get('format', None):
            media_url = f.get('url', None)
    
    if media_url == '':
        print('video format not supported')
        return None
    
    if media_url is None:
        print('Media URL not found')
        return None
    
    cap = cv2.VideoCapture(media_url)

    if not cap.isOpened():
        print('video not opened')
        return None

    while True:
        # read frame
        ret, latest_frame = cap.read()

        # check if frame is empty
        if not ret:
            return None

        # save frame as image
        cv2.imwrite('/tmp/latest_frame.jpg', latest_frame)

        # break to only capture 1 frame, else keep looping
        break

    # release VideoCapture
    cap.release()
    cv2.destroyAllWindows()
    return '/tmp/latest_frame.jpg'

def download_blob(bucket_name, source_blob_name):
    """Downloads a blob from the bucket."""

    # Initialize the client
    storage_client = storage.Client()

    # Get the bucket and blob
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)

    # check if blob exists
    if not blob.exists():
        return None

    # Download the blob
    blob_path = "/tmp/" + source_blob_name
    blob.download_to_filename(blob_path)

    print("Blob {} downloaded to {}.".format(source_blob_name, blob_path))

    return blob_path

def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    
    # Initialize the client
    storage_client = storage.Client()

    # Get the bucket
    bucket = storage_client.bucket(bucket_name)

    # Create a blob (which represents a GCS file object)
    blob = bucket.blob(destination_blob_name)

    # Upload the local file to GCS
    blob.upload_from_filename(source_file_name)
    print("File uploaded to {}.".format(destination_blob_name))


def publish_message(project_id, topic_name, message):
    publisher = pubsub_v1.PublisherClient()
    topic_name = 'projects/{project_id}/topics/{topic}'.format(
        project_id=project_id,
        topic=topic_name,
    )
    future = publisher.publish(topic_name, message.encode("utf-8"))
    future.result()


def compare(image_a, image_b):
    """compare two images and return the percentage of difference"""

    image_a_data = cv2.imread(image_a, 0)
    image_b_data = cv2.imread(image_b, 0)

    diff = cv2.absdiff(image_a_data, image_b_data)
    diff_int = diff.astype(np.uint8)
    percentage = (np.count_nonzero(diff_int) * 100) / diff_int.size
    print("percentage difference: " + str(percentage))
    return percentage
