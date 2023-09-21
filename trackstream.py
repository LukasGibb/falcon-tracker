import os
from dotenv import load_dotenv
from distutils.util import strtobool
import youtube_dl
import cv2
from google.cloud import storage
from google.cloud import pubsub_v1
from google.cloud import videointelligence
import io
import base64

def main():

    load_dotenv()
    url=os.getenv('VIDEO_URL', None)
    annotate=bool(strtobool(os.getenv('ANNOTATE', 'False')))
            
    #print(url)

    # Do stuff here
    print("Annotation function called...")

    if url is None:
        print("URL not provided")
        exit()

    # Get latest clip
    print("calling get_clip function")
    capture_time=os.getenv('CAPTURE_TIME', 5)
    latest_clip_path = get_clip(url, capture_time)
    if latest_clip_path is None:
        print('No clip retrieved')
        exit()

    # Annotate
    if annotate:
        print("calling annotate_clip function")
        annotation = annotate_clip(latest_clip_path)
        if annotation is None:
            print('No annotation retrieved')
            exit


def publish_message(project_id, topic_name):
    publisher = pubsub_v1.PublisherClient()
    topic_name = 'projects/{project_id}/topics/{topic}'.format(
        project_id=project_id,
        topic=topic_name,
    )
    print("publishing message to topic: {}".format(topic_name))
    future = publisher.publish(topic_name, b'hello from annotation func')
    future.result()

def get_clip(url,time):
    """get the latest clip from the yt video"""
    draw_boxes=bool(strtobool(os.getenv('DRAW_BOXES', 'True')))
    draw_contours=bool(strtobool(os.getenv('DRAW_CONTOURS', 'True')))

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
    frames = float(time) * fps
    bg_history = int(os.getenv('BACKGROUND_HISTORY',100))
    bg_var_threshold = float(os.getenv('BG_VAR_THRESHOLD',30))
    object_detector = cv2.createBackgroundSubtractorMOG2(history=bg_history,varThreshold=bg_var_threshold)

    while True:
        while framecount < frames:
            # read frame
            ret, latest_frame = cap.read()
            # set region of interest
            roi_x = os.getenv('ROI_X', '0:1080').split(":")
            roi_y = os.getenv('ROI_Y', '0:1920').split(":")
            roi = latest_frame[slice(int(roi_x[0]),int(roi_x[1])),slice(int(roi_y[0]),int(roi_y[1]))]
            # apply background mask
            mask = object_detector.apply(roi)
            # find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                # calculate the area and remove small elements
                area = cv2.contourArea(cnt)
                if area > float(os.getenv('MIN_CONTOUR_AREA',500)):
                    if draw_contours:
                        # draw the contours
                        cv2.drawContours(roi, [cnt], -1, (0, 255, 0), 2)
                    if draw_boxes:
                        # draw the bounding boxes
                        x, y, w, h = cv2.boundingRect(cnt)
                        cv2.rectangle(roi, (x, y), (x + w, y + h), (0, 255, 0), 3)

            # check if frame is empty
            if not ret:
                return None

            img = cv2.cvtColor(latest_frame, cv2.COLOR_BGR2RGB)
            # show roi
            cv2.imshow('roi', roi)
            # show the mask
            cv2.imshow('mask', mask)
            # show the stream
            cv2.imshow('frame', img)

            key = cv2.waitKey(1)
            # Hit esc to stop video
            if key == 27:
                break
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

main()