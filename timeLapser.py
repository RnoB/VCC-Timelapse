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
everythingTemp = '/timelapse/tmp/everything/'
weekVid = '/timelapse/video/week/'
monthVid = '/timelapse/video/month/'
everythingVid = '/timelapse/video/everything/'
vccDb = '/home/timelapse/VCC-Timelapse/vccTimelapse.db'
running = True

evs = ['_ev_-10','_ev_-5','','_ev_5','_ev_10']
ffmpegBegin ="ffmpeg -y -r 60 -i \""
ffmpegEnd = "image%08d.jpg\" -format rgb32 -s 2874x2160  -vcodec libx264 " 
ffmpegWeek = ffmpegBegin+weekTemp+ffmpegEnd
ffmpegMonth = ffmpegBegin+monthTemp+ffmpegEnd
ffmpegEverything = ffmpegBegin+everythingTemp+ffmpegEnd

day0 = datetime.date(2018,3,8)

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
    path = path  + expId+ '/'
    if not os.path.exists(path):
        os.makedirs(path)
    
    return path

def fileNamer(year,month,day,hours,minutes):
    year = str(year)
    month = str(month).zfill(2)
    day = str(day).zfill(2)
    hours = str(hours).zfill(2)
    minutes = str(minutes).zfill(2)
    return hdrPath+year+'-'+month+'-'+day+'_'+hours+minutes+'.jpg'




def dbFiller(today = False,tSleep = 7*60*60*24):
    print( ' -- Image Cropper Started -- ')

    while running:
        files = os.listdir(imagePath)
        fileDate = []
        for file  in files:
            fileDate.append(file[0:15])
        fileDate = np.unique(fileDate)

        for date in fileDate:

            if len(date) == 15 and date[0] == '2':
                year = date[0:4]
                month = date[5:7]
                day = date[8:10]
                todayDate = datetime.date.today()
                day1 = datetime.date(int(year),int(month),int(day))
                if (day1 == todayDate and today) or (day1!=todayDate and not today):
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
                            final_image = cv2.resize(res_debevec_8bit,None,fx=2874.0/3280.0,fy=2160.0/2464.0)
                            cv2.imwrite(fileNamer(year,month,day,hours,minutes), final_image)
                                
                            iYear,week,weekday = datetime.date(int(year),int(month),int(day)).isocalendar()

                            
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
    print( ' -- Weekly Video Started -- ')
    while running:
        currentWeek = np.floor((datetime.date.today()-day0).days/7.0).astype(int)
        conn = sqlite3.connect(vccDb)
        c = conn.cursor()
        c.execute("Select week from images")
        F = c.fetchall()
        weeks = np.unique(F)
        for week in weeks:
            c.execute("Select * from video where week = ? and duration = ?",(int(week),'week'))
            F = c.fetchall()
            
            if len(F) == 0 and week<currentWeek:

                step = 0
                for f in os.listdir(weekTemp):
                    os.remove(os.path.join(weekTemp, f))
                c.execute("Select dayRec from images where week = ?",(int(week),))
                F = c.fetchall()

                days = np.sort(np.unique(F))
         
                for day in days:
                    c.execute("Select hours from images where dayRec = ?",(int(day),))
                    F = c.fetchall()

                    hours = np.sort(np.unique(F))

                    c.execute("Select year,month,day from images where dayRec = ?",(int(day),))
                    year,month,dayPic = c.fetchall()[0]

                    for hour in hours:

                        c.execute("Select minutes from images where dayRec = ? and hours = ?",(int(day),int(hour)))
                        F = c.fetchall()
                        minutes = np.sort(np.unique(F))
                        for minute in minutes:
                            path = fileNamer(year,month,dayPic,hour,minute)
                            
                            copyfile(path, weekTemp + 'image'+str(step).zfill(8)+'.jpg')
                            step = step+1
                videoName = 'week'+str(week).zfill(5)+'.mp4'
                videoLine = ffmpegWeek + weekTemp+videoName
                print(videoLine)
                subprocess.call(videoLine,shell=True)
                copyfile(weekTemp+videoName,pather(weekVid,str(week).zfill(5))+videoName)
                print(weekTemp+videoName)
                videoId = upload_video(weekTemp+videoName,title = "Week "+str(week))
                videoId =''
                values = [videoId,"week",year,month,int(day),int(week)]

                c.execute("INSERT INTO video VALUES (?,?,?,?,?,?)",values)
            
                conn.commit()
                for f in os.listdir(weekTemp):
                    os.remove(os.path.join(weekTemp, f))
        conn.close()
        tSleep = 25-datetime.datetime.now().hour
        print('sleeping for '+str(tSleep)+' hours')
        try:
            os.remove(weekTemp+'*.jpg')
            os.remove(weekTemp+'*.mp4')
        except:
            pass
        time.sleep(3600*tSleep)
        

def monthlyVideo():
    print( ' -- Monthly Video Started -- ')

    stepMonth = 2

    while running:
        currentMonth = datetime.date.today().month
        currentYear = datetime.date.today().year
        conn = sqlite3.connect(vccDb)
        c = conn.cursor()
        c.execute("Select year,month from images")
        F = c.fetchall()
        months = list(set(F))
        print(months)
        for month in months:
            c.execute("Select * from video where year = ? and month = ? and duration = ?",(int(month[0]),int(month[1]),'month'))
            F = c.fetchall()

            if len(F) == 0 and month != (currentYear,currentMonth):
                step = 0
                image = 0   
                
                for f in os.listdir(monthTemp):
                    os.remove(os.path.join(monthTemp, f))
                c.execute("Select dayRec from images where  year = ? and month = ?",month)
                F = c.fetchall()
                days = np.sort(np.unique(F))
                for day in days:
                    c.execute("Select hours from images where dayRec = ?",(int(day),))
                    F = c.fetchall()
                    hours = np.sort(np.unique(F))
                    c.execute("Select day from images where dayRec = ?",(int(day),))
                    dayPic = c.fetchall()[0][0]

                    for hour in hours:
                        c.execute("Select minutes from images where dayRec = ? and hours = ?",(int(day),int(hour)))
                        F = c.fetchall()
                        minutes = np.sort(np.unique(F))
                        for minute in minutes:
                            if image%stepMonth == 0:
                                path = fileNamer(int(month[0]),int(month[1]),dayPic,hour,minute)

                                copyfile(path, monthTemp + 'image'+str(step).zfill(8)+'.jpg')
                                step = step+1
                            image=image+1
                videoName = 'month_'+str(month[0])+'_'+str(month[1]).zfill(2)+'.mp4'
                videoLine = ffmpegMonth + monthTemp+videoName
                print(videoLine)
                subprocess.call(videoLine,shell=True)
                copyfile(monthTemp+videoName,pather(monthVid,str(month[0])+'_'+str(month[1]).zfill(2))+videoName)
                videoId = upload_video(monthTemp+videoName,title = "Month "+str(month))
                values = [videoId,"month",int(month[0]),int(month[1]),day,0]

                c.execute("INSERT INTO video VALUES (?,?,?,?,?,?)",values)
            
                conn.commit()
                for f in os.listdir(monthTemp):
                    os.remove(os.path.join(monthTemp, f))
        conn.close()   
        try:
            os.remove(monthTemp+'*.jpg')
            os.remove(monthTemp+'*.mp4')
        except:
            pass
        tSleep = 26-datetime.datetime.now().hour
        time.sleep(3600*tSleep)



def everythingVideo():
    #tSleep = 27-dt.datetime.now().hour
    #print('sleeping for '+str(tSleep)+' hours')
    print( ' -- Everything Video Started -- ')
    while running:
        image = 0
        step = 0
        todayDate = datetime.date.today()
        dayRecToday = (todayDate-day0).days
        conn = sqlite3.connect(vccDb)
        c = conn.cursor()
        c.execute("Select dayRec from images")
        F = c.fetchall()
        days = np.sort(np.unique(F))
        for f in os.listdir(everythingTemp):
            os.remove(os.path.join(everythingTemp, f))

        stepEverything = int(np.ceil(len(days)/30.0))

        for day in days:
            if day !=dayRecToday:
                c.execute("Select hours from images where dayRec = ?",(int(day),))
                F = c.fetchall()
                hours = np.sort(np.unique(F))
                c.execute("Select year,month,day from images where dayRec = ?",(int(day),))
                year,month,dayPic = c.fetchall()[0]

                for hour in hours:
                    c.execute("Select minutes from images where dayRec = ? and hours = ?",(int(day),int(hour)))
                    F = c.fetchall()
                    minutes = np.sort(np.unique(F))
                    for minute in minutes:
                        if image%stepEverything == 0:
                            path = fileNamer(year,month,dayPic,hour,minute)

                            copyfile(path, everythingTemp + 'image'+str(step).zfill(8)+'.jpg')
                            step = step+1
                        image=image+1
        videoName = 'everything_'+str(todayDate.year)+'-'+str(todayDate.month).zfill(4)+'-'+str(todayDate.day).zfill(4)+'.mp4'
        videoLine = ffmpegEverything + everythingTemp+videoName
        print(videoLine)
        subprocess.call(videoLine,shell = True)
        copyfile(everythingTemp+videoName,pather(everythingVid,str(todayDate.year)+'-'+str(todayDate.month).zfill(4)+'-'+str(todayDate.day).zfill(4))+videoName)
        videoId = upload_video(everythingTemp+videoName,title = "Everything up to "+str(todayDate))
        values = [videoId,"everything",todayDate.year,todayDate.month,todayDate.day,0]

        c.execute("INSERT INTO video VALUES (?,?,?,?,?,?)",values)
    
        conn.commit()
        conn.close()
        for f in os.listdir(everythingTemp):
            os.remove(os.path.join(everythingTemp, f))
        tSleep = 27-datetime.datetime.now().hour+2*24
        print('sleeping for '+str(tSleep)+' hours')
        time.sleep(tSleep*3600)










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
    monthThread = threading.Thread(target=monthlyVideo)
    monthThread.daemon = True
    monthThread.start()
    everythingThread = threading.Thread(target=everythingVideo)
    everythingThread.daemon = True
    everythingThread.start()
    
    t0 =time.time()
    while running:
        time.sleep(60*60)
        print(' -----> Making Timelapses since '+str(int((time.time()-t0)/3600)) +' hours')



if __name__ == '__main__':
    main()

