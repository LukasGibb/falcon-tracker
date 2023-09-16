from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import math
import cv2
import sys
import numpy as np

import youtube_dl

import functions_framework

@functions_framework.http
def handle(request):
    # get a frame from youtube stream
    # get a frame from the camera
    # compare the two frames
    # return the percentage of difference
    
    return request

def get_frame(url):

    ydl_opts = {
         'nocheckcertificate': True
    }

    # create youtube-dl object
    ydl = youtube_dl.YoutubeDL(ydl_opts)

    # set video url, extract video information
    info_dict = ydl.extract_info(url, download=False)

    # # get video formats available
    formats = info_dict.get('formats', None)

    for f in formats:

        # This is for STREAMS only
        # 'format_note' for regular videos
        # value for regular videos is 144p, 240p, 360p, 480p, 720p, 1080p, etc
        if f.get('format', None) == '96 - 1920x1080':

            url = f.get('url', None)
            cap = cv2.VideoCapture(url)

            if not cap.isOpened():
                print('video not opened')
                exit(-1)

            while True:
                # read frame
                ret, latest_frame = cap.read()

                # check if frame is empty
                if not ret:
                    break

                # save frame as image
                cv2.imwrite('latest_frame.jpg', latest_frame)

                # break to only capture 1 frame, else keep looping
                break

            # release VideoCapture
            cap.release()

    cv2.destroyAllWindows()


def compare(image_a, image_b):
    image_a_data = cv2.imread(image_a, 0)
    image_b_data = cv2.imread(image_b, 0)

    diff = cv2.absdiff(image_a_data, image_b_data)
    diff_int = diff.astype(np.uint8)
    percentage = (np.count_nonzero(res) * 100) / diff_int.size

    return percentage

if __name__ == "__main__":
    get_frame('https://www.youtube.com/watch?v=y3b2rKUPMsA')
