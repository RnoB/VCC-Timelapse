#import cv2
import sqlite3
import numpy as np
import os

imagePath = '/timelapse'



def dbFiller():
    files = os.listdir(imagePath)
    fileDate = []
    for file  in files:
        fileDate.append(file[0:15])
    fileDate = np.unique(fileDate)
    for date in fileDate:
        if len(date) == 15:
            year = date[0:4]
            month = date[5:7]
            day = date[8:10]
            time = date[11:15]
            print(year,month,day,time)
    print(fileDate)


def main():
    dbFiller()
    print('nothing')

if __name__ == '__main__':
    main()

