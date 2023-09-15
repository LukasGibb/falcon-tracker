from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import math
import cv2
import sys
import numpy

print("image Compare")

#print('Total arguments:', len(sys.argv))

readImage1 = sys.argv[1]
readImage2 = sys.argv[2]

img1 = cv2.imread(readImage1, 0)
img2 = cv2.imread(readImage2, 0)

#--- take the absolute difference of the images ---
res = cv2.absdiff(img1, img2)

#--- convert the result to integer type ---
res = res.astype(numpy.uint8)

#--- find  based on number of pixels that are not zero ---
percentage = (numpy.count_nonzero(res) * 100)/ res.size

print('Percentage:',percentage)
