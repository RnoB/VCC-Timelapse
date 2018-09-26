#import cv2
import sqlite3
import numpy as np
import os

imagePath = '/timelapse'



def dbFiller():
    files = os.listdirs(imagePath)
    fileDate = []
    for file  in files:
        fileDate.append(file[0:15])
    fileDate = np.unique(fileDate)
    print(fileDate)


def main():
    dbFiller()
    print('nothing')

if __name__ == '__main__':
    main()

