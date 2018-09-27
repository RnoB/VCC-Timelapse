import cv2
import sqlite3
import numpy as np
import os
import threading
import time
import PIL.Image
import PIL.ExifTags
import datetime
from shutil import copyfile
import subprocess
from upload_video import upload_video
imagePath = '/timelapse/'
hdrPath = '/timelapse/hdr/'
weekTemp = '/timelapse/tmp/week/'
monthTemp = '/timelapse/tmp/month/'
weekVid = '/timelapse/video/week/'
monthVid = '/timelapse/video/month/'
vccDb = 'vccTimelapse.db'
running = True

evs = ['_ev_-10','_ev_-5','','_ev_5','_ev_10']

ffmpegWeek = "ffmpeg -y -r 30 -i \""+weekTemp+"image%08d.png\" -format rgb32 -s 2875x2160 -vcodec libx264 "

day0 = datetime.date(2018,8,20)

def firstGenDb():

    conn = sqlite3.connect(vccDb)
    c = conn.cursor()
    c.execute('''CREATE TABLE images (year integer, month integer,
                                      day integer, hours integer, minutes integer,week integer,weekday integer,dayRec integer)''')
    c.execute('''CREATE TABLE video (youtube text, duration text,
                                      year integer, month integer,
                                      day integer,week integer)''')
    conn.commit()
    conn.close()
    



def pather(path,expId):
    if not os.path.exists(path):
        os.makedirs(path)
    path = path  + expId+ '\\'
    if not os.path.exists(path):
        os.makedirs(path)
    
    return path

def fileNamer(year,month,day,hours,minutes):
    return hdrPath+year+'-'+month+'-'+day+'_'+hours+minutes+'.jpg'




def dbFiller(today = False,tSleep = 7*60*60*24):
    while running:
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
                todayDate = datetime.date.today()
                day0 = datetime.date(int(year),int(month),int(day))
                if (day0 == todayDate and today) or (day0!=todayDate and not today):
                    hours = date[11:13]
                    minutes = date[13:15]
                    conn = sqlite3.connect(vccDb)
                    c = conn.cursor()
                    c.execute("Select * from images where year = ? and month = ? and day = ? and hours = ? and minutes = ?",(int(year),int(month),int(day),int(hours),int(minutes),))
                    F = c.fetchall()

                    if len(F) == 0:
                        images = []
                        times = []
                        for ev in evs:
                            imName = imagePath+year+'-'+month+'-'+day+'_'+hours+minutes+ev+'.jpg'
                            image = cv2.imread(imName)

                            
                            if image is not None and np.sum(image)>2500000000 :
                                img = PIL.Image.open(imName)
                                exif = {
                                    PIL.ExifTags.TAGS[k]: v
                                    for k, v in img._getexif().items()
                                    if k in PIL.ExifTags.TAGS
                                }
                                images.append(image)
                                times.append(exif['ExposureTime'][0]/exif['ExposureTime'][1])

                        if len(images)>0:
                            times = np.array(times).astype(np.float32)

                                

                            alignMTB = cv2.createAlignMTB()
                            alignMTB.process(images, images)
                            calibrateDebevec = cv2.createCalibrateDebevec()

                            responseDebevec = calibrateDebevec.process(images,times)
                            # Merge images into an HDR linear image
                            mergeDebevec = cv2.createMergeDebevec()
                            hdrDebevec = mergeDebevec.process(images, times, responseDebevec)

                            tonemap1 = cv2.createTonemapDurand(gamma=2.2)
                            res_debevec = tonemap1.process(hdrDebevec.copy())
                            # Save HDR image.
                            res_debevec_8bit = np.clip(res_debevec*255, 0, 255).astype('uint8')
                            final_image = cv2.resize(res_debevec_8bit,None,fx=2160.0/2464.0,fy=2160.0/2464.0)
                            cv2.imwrite(fileNamer(year,month,day,hours,minutes), final_image)
                                
                            iYear,week,weekday = datetime.date(int(year),int(month),int(day)).isocalendar()

                            
                            day1 = datetime.date(int(year),int(month),int(day))
                            dayRec = (day1-day0).days
                            week = np.floor((day1-day0).days/7.0).astype(int)
                            values = [year,month,day,hours,minutes,int(week),weekday,dayRec]

                            c.execute("INSERT INTO images VALUES (?,?,?,?,?,?,?,?)",values)
                            print(year+' '+month+' '+day+' '+hours+':'+minutes + ' week : '+str(week) + ' day : '+str(weekday) +' dayRec : '+str(dayRec))
                        
                            conn.commit()
                    conn.close()
        time.sleep(tSleep)
    print(fileDate)



def weeklyVideo():
    #tSleep = 25-dt.datetime.now().hour
    #print('sleeping for '+str(tSleep)+' hours')
    print('video')
    while running:
        currentWeek = np.floor((datetime.date.today()-day0).days/7.0).astype(int)
        conn = sqlite3.connect(vccDb)
        c = conn.cursor()
        c.execute("Select week from images")
        F = c.fetchall()
        weeks = np.unique(F)

        for week in weeks:
            c.execute("Select * from video where week = ? and duration = ?",(week,'week'))
            F = c.fetchall()
            print(F)
            if len(F) == 0 and week<currentWeek:
                step = 0
                try:
                    os.remove(weekVid+'*.jpg')
                    os.remove(weekVid+'*.mp4')
                except:
                    pass
                c.execute("Select dayRec from images where week = ?",(week,))
                F = c.fetchall()
                days = np.sort(np.unique(F))
                for day in days:
                    c.execute("Select hours from images where dayRec = ?",(day,))
                    F = c.fetchall()
                    hours = np.sort(np.unique(F))
                    c.execute("Select year from images where dayRec = ?",(day,))
                    year = c.fetchall()[0]
                    c.execute("Select month from images where dayRec = ?",(day,))
                    month = c.fetchall()[0]
                    for hour in hours:
                        c.execute("Select minutes from images where dayRec = ? and hour = ?",(day,hour))
                        F = c.fetchall()
                        minutes = np.sort(np.unique(F))
                        for minute in minutes:
                            path = fileNamer(year,month,day,hour,minute)

                            copyfile(path, weekTemp + 'image'+str(step).zfill(8)+'.jpg')
                            step = step+1
                videoName = 'week'+str(week).zfill(5)+'.mp4'
                videoLine = ffmpegWeek + weekTemp+videoName
                print(videoLine)
                subprocess.call(videoLine)
                copyfile(path,pather(weekVid,str(week).zfill(5)))
                videoId = upload_video(path,title = "Week "+str(week))
                values = [videoId,"week",year,month,dayRec,int(week)]

                c.execute("INSERT INTO images VALUES (?,?,?,?,?,?)",values)
                print(year+' '+month+' '+day+' '+hours+':'+minutes + ' week : '+str(week) + ' day : '+str(weekday) +' dayRec : '+str(dayRec))
            
                conn.commit()
        conn.close()
        time.sleep(24*3600)

def monthlyVideo():
    #tSleep = 26-dt.datetime.now().hour
    #print('sleeping for '+str(tSleep)+' hours')
    print('video')
    while running:
        currentMonth = datetime.date.today().month
        conn = sqlite3.connect(vccDb)
        c = conn.cursor()
        c.execute("Select month from images")
        F = c.fetchall()
        months = np.unique(F)

        for month in months:
            c.execute("Select * from video where month = ? and duration = ?",(month,'month'))
            F = c.fetchall()
            print(F)
            if len(F) == 0 and month<currentMonth:
                step = 0
                os.remove(monthVid+'*.jpg')
                os.remove(monthVid+'*.mp4')
                c.execute("Select dayRec from images where month = ?",(month,))
                F = c.fetchall()
                days = np.sort(np.unique(F))
                for day in days:
                    c.execute("Select hours from images where dayRec = ?",(day,))
                    F = c.fetchall()
                    hours = np.sort(np.unique(F))
                    c.execute("Select year from images where dayRec = ?",(day,))
                    year = c.fetchall()[0]
                    c.execute("Select month from images where dayRec = ?",(day,))
                    month = c.fetchall()[0]
                    for hour in hours:
                        c.execute("Select minutes from images where dayRec = ? and hour = ?",(day,hour))
                        F = c.fetchall()
                        minutes = np.sort(np.unique(F))
                        for minute in minutes:
                            path = fileNamer(year,month,day,hour,minute)

                            copyfile(path, monthTemp + 'image'+str(step).zfill(8)+'.jpg')
                            step = step+1
                videoName = 'month'+str(month).zfill(5)+'.mp4'
                videoLine = ffmpeg + monthTemp+videoName
                print(videoLine)
                subprocess.call(videoLine)
                copyfile(path,pather(monthVid,str(month).zfill(5)))
                videoId = upload_video(path,title = "Month "+str(month))
                values = [videoId,"month",year,month,dayRec,int(week)]

                c.execute("INSERT INTO images VALUES (?,?,?,?,?,?)",values)
                print(year+' '+month+' '+day+' '+hours+':'+minutes + ' week : '+str(week) + ' day : '+str(weekday) +' dayRec : '+str(dayRec))
            
                conn.commit()
        conn.close()
        time.sleep(24*3600)


def everythingVideo():
    #tSleep = 27-dt.datetime.now().hour
    #print('sleeping for '+str(tSleep)+' hours')
    print('video')
    while running:
        currentWeek = np.floor((datetime.date.today()-day0).days/7.0).astype(int)
        conn = sqlite3.connect(vccDb)
        c = conn.cursor()
        c.execute("Select month from images")
        F = c.fetchall()
        months = np.unique(F)

        for month in months:
            c.execute("Select * from video where month = ? and duration = ?",(month,'everything'))
            F = c.fetchall()
            print(F)
            if len(F) == 0 and month<currentMonth:
                step = 0
                os.remove(monthVid+'*.jpg')
                os.remove(monthVid+'*.mp4')
                c.execute("Select dayRec from images where month = ?",(month,))
                F = c.fetchall()
                days = np.sort(np.unique(F))
                for day in days:
                    c.execute("Select hours from images where dayRec = ?",(day,))
                    F = c.fetchall()
                    hours = np.sort(np.unique(F))
                    c.execute("Select year from images where dayRec = ?",(day,))
                    year = c.fetchall()[0]
                    c.execute("Select month from images where dayRec = ?",(day,))
                    month = c.fetchall()[0]
                    for hour in hours:
                        c.execute("Select minutes from images where dayRec = ? and hour = ?",(day,hour))
                        F = c.fetchall()
                        minutes = np.sort(np.unique(F))
                        for minute in minutes:
                            path = fileNamer(year,month,day,hour,minute)

                            copyfile(path, monthTemp + 'image'+str(step).zfill(8)+'.jpg')
                            step = step+1
                videoName = 'month'+str(month).zfill(5)+'.mp4'
                videoLine = ffmpeg + monthTemp+videoName
                print(videoLine)
                subprocess.call(videoLine)
                copyfile(path,pather(monthVid,str(month).zfill(5)))
                videoId = upload_video(path,title = "Everything up to Month "+str(month))
                values = [videoId,"everything",year,month,dayRec,int(week)]

                c.execute("INSERT INTO images VALUES (?,?,?,?,?,?)",values)
                print(year+' '+month+' '+day+' '+hours+':'+minutes + ' week : '+str(week) + ' day : '+str(weekday) +' dayRec : '+str(dayRec))
            
                conn.commit()
        conn.close()
        time.sleep(24*3600)










def main():
    if not os.path.isfile(vccDb): 
        firstGenDb()
    checkFilesThread = threading.Thread(target=dbFiller,args = (False,7*24*60*60))
    checkFilesThread.daemon = True
    checkFilesThread.start()
    checkFilesThread = threading.Thread(target=dbFiller,args = (True,5*60))
    checkFilesThread.daemon = True
    checkFilesThread.start()
    weekThread = threading.Thread(target=weeklyVideo)
    weekThread.daemon = True
    weekThread.start()
    # monthThread = threading.Thread(target=monthlyVideo)
    # monthThread.daemon = True
    # monthThread.start()
    # everythingThread = threading.Thread(target=everythingVideo)
    # everythingThread.daemon = True
    # everythingThread.start()
    
    print('nothing')
    t0 =time.time()
    while running:
        time.sleep(60*60)
        print(' -----> Making Timelapses since '+str(int((time.time()-t0)/3600)) +' hours')



if __name__ == '__main__':
    main()

