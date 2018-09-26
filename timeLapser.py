import cv2
import sqlite3
import numpy as np
import os
import threading
import time
import PIL.Image
import PIL.ExifTags

imagePath = '/timelapse/'
hdrPath = '/timelapse/hdr/'
vccDb = 'vccTimelapse.db'
running = True

evs = ['_ev_-10','_ev_-5','','_ev_5','_ev_10']

def firstGenDb():

    conn = sqlite3.connect(vccDb)
    c = conn.cursor()
    c.execute('''CREATE TABLE images (year integer, month integer,
                                      day integer, hours integer, minutes integer)''')
    c.execute('''CREATE TABLE video (youtube text, duration text,
                                      year integer, month integer,
                                      day integer)''')
    conn.commit()
    conn.close()
    



def dbFiller():
    while running:
        files = os.listdir(imagePath)
        fileDate = []
        for file  in files:
            fileDate.append(file[0:15])
        fileDate = np.unique(fileDate)
        conn = sqlite3.connect(vccDb)
        c = conn.cursor()
        for date in fileDate:
            if len(date) == 15:
                year = date[0:4]
                month = date[5:7]
                day = date[8:10]
                hours = date[11:13]
                minutes = date[13:15]
                c.execute("Select * from images where year = ? and month = ? and day = ? and hours = ? and minutes = ?",(year,month,day,hours,minutes,))
                if len(c.fetchall()) == 0:
                    images = []
                    times = []
                    for ev in evs:
                        imName = imagePath+year+'-'+month+'-'+day+'_'+hours+minutes+ev+'.jpg'
                        image = cv2.imread(imName)
                        img = PIL.Image.open(imName)
                        exif = {
                            PIL.ExifTags.TAGS[k]: v
                            for k, v in img._getexif().items()
                            if k in PIL.ExifTags.TAGS
                        }
                        print(exif['ExposureTime'])
                        print(exif['ExposureTime'][1]/exif['ExposureTime'][0])
                        if image is not None:
                            images.append(image)
                            times.append(len(images)-1)
                    times = np.array(times)
                        

                    alignMTB = cv2.createAlignMTB()
                    alignMTB.process(images, images)
                    calibrateDebevec = cv2.createCalibrateDebevec()
                    print(times)
                    responseDebevec = calibrateDebevec.process(images,times)
                    # Merge images into an HDR linear image
                    mergeDebevec = cv2.createMergeDebevec()
                    hdrDebevec = mergeDebevec.process(images, times, responseDebevec)
                    # Save HDR image.
                    cv2.imwrite(hdrPath+year+'-'+month+'-'+day+'_'+hours+minutes+'.jpg', hdrDebevec)
                    values = [year,month,day,hours,minutes]
                    c.execute("INSERT INTO images VALUES (?,?,?,?,?)",values)
                
        conn.commit()
        conn.close()
        time.sleep(15*60)
    print(fileDate)




def main():
    if not os.path.isfile(vccDb): 
        firstGenDb()
    checkFilesThread = threading.Thread(target=dbFiller)
    checkFilesThread.daemon = True
    checkFilesThread.start()
    
    print('nothing')
    t0 =time.time()
    while running:
        time.sleep(60*60)
        print(' -----> Making Timelapses since')



if __name__ == '__main__':
    main()

