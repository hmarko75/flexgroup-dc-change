#!/usr/bin/python3
import sys,shutil,os,time

inputfile = './input.txt'
cpsfx = '.copy_to_other_dc_flexgroup'
mvsfx = '.temp_move_to_other_dc_flexgroup'

MAX_FGINDEX = 1000
def REVERSE32(i):
    flip4 = [
        0x0,0x8,0x4,0xC,0x2,0xA,0x6,0xE,0x1,0x9,0x5,0xD,0x3,0xB,0x7,0xF
    ]
    return (
        flip4[ i & 0xF ] << 28) | \
        (flip4[ (i>>4) & 0xF ] << 24) | \
        (flip4[ (i>>8) & 0xF ] << 20) | \
        (flip4[ (i>>12) & 0xF ] << 16) | \
        (flip4[ (i>>16) & 0xF ] << 12) | \
        (flip4[ (i>>20) & 0xF ] << 8) | \
        (flip4[ (i>>24) & 0xF ] << 4) | \
        (flip4[ (i>>28) & 0xF ]
    )

def fileid_to_msid(fileid):
    if ((fileid >> 32) == 0):
        return REVERSE32(fileid) & 0x0FFF
    return (fileid >> 32) & 0x0FFF

def fgid(fileid,rootfileid):
    if not fileid or not rootfileid:
        return 0

    base_msid = fileid_to_msid(rootfileid)
    msid = fileid_to_msid(fileid)
    if msid > base_msid:
        return min(msid - base_msid + 1, MAX_FGINDEX)
    if msid < base_msid:
        return min(base_msid - msid + 1, MAX_FGINDEX)
    return 1

def find_mount_point(path):
    path = os.path.abspath(path)
    while not os.path.ismount(path):
        path = os.path.dirname(path)
    return path


# 
file1 = open(inputfile, 'r')
lines = file1.readlines()

for line in lines:

    log = ''

    line = line.rstrip()
    line = line.split(',')[0].split("\t")[0]

    nfsserver,filepath = line.split(":")
    filename = os.path.basename(filepath)
    dirname = os.path.dirname(filepath)
    dirs = filepath.split('/')
        
    if os.path.isfile(filepath):
        filesizeb = os.path.getsize(filepath)
        filesize = round(filesizeb/1024/1024,2)
        filemodified = os.path.getmtime(filepath)
        fileagesec  = time.time() - filemodified
        fileinode = os.stat(filepath).st_ino
        rootinode = os.stat(find_mount_point(filepath)).st_ino
        filefgid = fgid(fileinode,rootinode)

        log = "file:"+filepath+" size:"+str(filesize)+"MB modified:"+str(round(fileagesec/60/60,2))+"h fgid:"+str(filefgid)+" :"

        #print ("file:"+filepath+" found with size "+str(filesize)+"MB, modified time:"+str(round(fileagesec/60/60,2))+"h fgid:"+str(filefgid))

        #copy file with metadata from between mounts 
        cpsrc = filepath
        cpdst = filepath+cpsfx

        if os.path.isfile(cpdst):
            #print ("temp destfile:"+cpdst+" already exists. deleting")
            try:
                os.remove(cpdst)
            except Exception as e:
                print (log+"could not delete file:"+cpdst+" error:"+e)
                continue 

        try:
            #print ("recreating file:"+cpsrc)
            copyresult = shutil.copy2(cpsrc,cpdst)
        except Exception as e:
            print (log+"could not copy file:"+cpsrc+" to:"+cpdst+" error:"+e)
            continue             

        tempfilesizeb = os.path.getsize(cpdst)
        tempfileinode = os.stat(cpdst).st_ino
        tempfilefgid = fgid(tempfileinode,rootinode)

        if tempfilesizeb != filesizeb:
            print (log+"source file:"+cpsrc+" changed during copy, skipping")
            os.remove(cpdst)
            continue   
        if tempfilefgid == filefgid:
            print (log+"destination file fgid wasn't changed, skipping")
            os.remove(cpdst)
            continue                   

        mvsrc = filepath 
        mvdst = filepath+mvsfx
        try:
            #print ("rename file:"+mvsrc+" to:"+mvdst)
            moveresult = shutil.move(mvsrc,mvdst)
        except Exception as e:
            print (log+"could not rename file:"+mvsrc+" to:"+mvdst+" error:"+e)
            continue             

        mvsrc = filepath+cpsfx
        mvdst = filepath
        try:
            #print ("rename file:"+mvsrc+" to:"+mvdst)
            moveresult = shutil.move(mvsrc,mvdst)
        except  Exception as e:
            print (log+"MAUAL INTERVENTION REQUIRED could not rename production file:"+mvsrc+" to:"+mvdst+" error:"+e)
            exit(1)

        newfilesize = round(os.path.getsize(filepath)/1024/1024,2)
        newfilemodified = os.path.getmtime(filepath)
        newfileagesec  = time.time() - filemodified
        newfileinode = os.stat(filepath).st_ino
        newfilefgid = fgid(newfileinode,rootinode)
        print (log+" new fgid:"+str(newfilefgid))

        delfile = filepath+mvsfx
        try :
            #print("delete original file:"+delfile)
            os.remove(delfile)
        except Exception as e:
            print("could not delete temp file:"+delfile+" error:"+e)


        
    else:
        print ("could not find file:"+filepath+". skipping")

