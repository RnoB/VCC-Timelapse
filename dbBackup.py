import threading
import time
import datetime as dt
import os
from shutil import copyfile
running = True

backupPath = "/timelapse/dbBackup/" 

def updateDatabase():

    today = dt.datetime.now()

    path = backupPath+ today.strftime('%y-%m-%d')+"/"
    if not os.path.exists(path):
            os.mkdir(path)
    projectDB = "vccTimelapse.db"
    copyfile('./'+projectDB, path+projectDB)


def main():
    global running
    updateDatabase()
    t0 = time.time()
    tSleep = 25-dt.datetime.now().hour
    print('sleeping for '+str(tSleep)+' hours')
    while running:
        time.sleep(3600*tSleep)
        updateDatabase()
        t = time.time()-t0
        print(">>>>>>>>>>>> MalkoFish <<<<<<<<<<")
        print("Backuping your database since " + str(int(t/3600)) +" hours")
        tSleep = 7*24



if __name__ == '__main__':
    main()
