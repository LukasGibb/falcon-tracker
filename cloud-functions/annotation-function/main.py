import os
import youtube_dl
import cv2
from google.cloud import storage
from google.cloud import pubsub_v1
from google.cloud import videointelligence
import io
import base64

import functions_framework

@functions_framework.http
def handle(request):
    # This function should call the Google Vision/Video API and return
    """handle a request to the function"""

    message = request.get_json().get('message', None)

    if message is None:
        # No pub/sub message provided, check if triggered via http
        url = request.get_json().get('video_url', None)
        if url is None:
            print ("No URL provided")
            return 'No URL provided', 400
    else:
        #print(message)
        # Get URL from pub/sub message
        url = base64.b64decode(message['data']).decode('utf-8')
        
    #print(url)

    # Do stuff here
    print("Annotation function called...")
    
    # Get latest clip
    print("calling get_clip function")
    latest_clip_path = get_clip(url, 300)
    if latest_clip_path is None:
        return 'No clip retrieved', 400
    
    # Annotate
    print("calling annotate_clip function")
    annotation = annotate_clip(latest_clip_path)
    if annotation is None:
        return 'No annotation retrieved', 400

    # Save latest annotation to bucket

    # Compare with previous annotation

    # Notify
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

def get_clip(url,frames):
    """get the latest clip from the yt video"""

    ydl_opts = {
         'nocheckcertificate': True
    }

    ydl = youtube_dl.YoutubeDL(ydl_opts)
    info_dict = ydl.extract_info(url, download=False)
    formats = info_dict.get('formats', None)

    for f in formats:
        if '1920x1080' in f.get('format', None):
            url = f.get('url', None)
            fps = f.get('fps', None)
            ext = f.get('ext', None)
            width = f.get('width', None)
            height = f.get('height', None)
            vcodec = f.get('vcodec', None)
            vcodec_short = vcodec.split('.')[0]
            # opencv-python doesn't support h264 due to licensing issues
            #fourcc = cv2.VideoWriter_fourcc(*vcodec_short)
            # using mp4v instead
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            filename = '/tmp/latest_clip.' + ext


    cap = cv2.VideoCapture(url)

    if not cap.isOpened():
        print('video not opened')
        return None
    
    file = cv2.VideoWriter(filename,fourcc,fps,(width, height))
    framecount = 0

    while True:
        while framecount < frames:
            # read frame
            ret, latest_frame = cap.read()

            # check if frame is empty
            if not ret:
                return None

            img = cv2.cvtColor(latest_frame, cv2.COLOR_BGR2RGB)
            #cv2.imshow('frame', img)
            file.write(img)
            framecount += 1
        break

    # release VideoCapture
    cap.release()
    file.release()
    cv2.destroyAllWindows()
    return filename

def annotate_clip(path):
    video_client = videointelligence.VideoIntelligenceServiceClient()
    features = [videointelligence.Feature.OBJECT_TRACKING]

    with io.open(path,"rb") as file:
        input_content = file.read()

    operation = video_client.annotate_video(
        request={"features": features, "input_content": input_content}
    )
    print("\nProcessing video for object annotations.")

    result = operation.result(timeout=500)
    print("\nFinished processing.\n")

    # The first result is retrieved because a single video was processed.
    object_annotations = result.annotation_results[0].object_annotations

    # Loop through the annotations
    for object_annotation in object_annotations:
        print("Entity description: {}".format(object_annotation.entity.description))
        if object_annotation.entity.entity_id:
            print("Entity id: {}".format(object_annotation.entity.entity_id))

        print(
            "Segment: {}s to {}s".format(
                object_annotation.segment.start_time_offset.seconds
                + object_annotation.segment.start_time_offset.microseconds / 1e6,
                object_annotation.segment.end_time_offset.seconds
                + object_annotation.segment.end_time_offset.microseconds / 1e6,
            )
        )

        print("Confidence: {}".format(object_annotation.confidence))

        # Here we print only the bounding box of the first frame in this segment
        frame = object_annotation.frames[0]
        box = frame.normalized_bounding_box
        print(
            "Time offset of the first frame: {}s".format(
                frame.time_offset.seconds + frame.time_offset.microseconds / 1e6
            )
        )
        print("Bounding box position:")
        print("\tleft  : {}".format(box.left))
        print("\ttop   : {}".format(box.top))
        print("\tright : {}".format(box.right))
        print("\tbottom: {}".format(box.bottom))
        print("\n")
    
    return object_annotations