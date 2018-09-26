import cv2
import sqlite3
import numpy as np
import os
import threading
import time

imagePath = '/timelapse'
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
                    image = []
                    for ev in evs:
                        imName = year+'-'+month+'-'+day+'_'+hours+minutes+ev+'.jpg'
                        images.append(cv2.imread(imName))
                    values = [year,month,day,hours,minutes]
                    c.execute("INSERT INTO images VALUES (?,?,?,?,?)",values)
                
        conn.commit()
        conn.close()
        time.sleep(15*60)
    print(fileDate)



def 

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

