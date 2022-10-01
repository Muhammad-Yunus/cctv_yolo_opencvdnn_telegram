import telegram
import datetime
import time
import math
import cv2
import os
import re
import queue 
import threading
import numpy as np
import socket

from utils import Utils


class HomeCamBot():
    def __init__(self):
        self.botToken = os.environ['BOT_TOKEN']
        self.chat_id = os.environ['CHAT_ID']
        self.bot = telegram.Bot(token=self.botToken)
        self.HeartBeatSent = False

    def SendPhoto(self, img, msg):
        message = self.bot.sendPhoto(photo=img, caption=msg, chat_id=self.chat_id)
        return message

    def SendMessage(self, message):
        self.bot.sendMessage(chat_id=self.chat_id, text=message)
        self.HeartBeatSent = True

class Detector():
    def __init__(self):
        self.modelConfiguration = "yolo/coco_yolov3-tiny.cfg"
        self.modelWeights = "yolo/coco_yolov3-tiny.weights"
        self.net = cv2.dnn.readNetFromDarknet(self.modelConfiguration, self.modelWeights)
        self.net.getLayerNames()
        self.layerOutput = self.net.getUnconnectedOutLayersNames()

        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

        self.target_w = 416
        self.target_h = 416

        self.classes = None
        self.classesFile = "yolo/coco.names"
        with open(self.classesFile, 'rt') as f:
            self.classes = f.read().rstrip('\n').split('\n')      

        self.include_objects = ["person", "laptop", "keyboard", "cell phone", "tvmonitor", "knife"]
        self.util_lib = Utils()

    def detect(self, frame):
        blob = cv2.dnn.blobFromImage(frame, 
                            1.0/255, 
                            (self.target_w, self.target_h), 
                            (0, 0, 0), swapRB=True, crop=False)

        # predict classess & box
        self.net.setInput(blob)
        output = self.net.forward(self.layerOutput)
        
        t, _ = self.net.getPerfProfile()
        print('inference time: %.2f s' % (t / cv2.getTickFrequency()))

        return self.util_lib.postprocess(output, frame, self.classes, self.include_objects)

class CustomVideoCapture():
    def __init__(self, name):
        self.name = name
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5)

        self.cap = None
        self.initializeVideoCapture()

        self.q = queue.Queue()
        t = threading.Thread(target=self._reader)
        t.daemon = True
        t.start()

    def urlParse(self, uri):
        p = '(?:http.*://)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*'
        m = re.search(p, uri)
        return m.group('host'), int(m.group('port'))

    def checkMjpeg(self):
        host, port = self.urlParse(self.name)
        result = self.sock.connect_ex((host, port))
        return result == 0 # true is open, otherwise is closed

    def initializeVideoCapture(self):
        self.cap = None
        retry_failed_counter = 0
        while self.cap == None :
            try :
                if not self.checkMjpeg() :
                    time.sleep(30)
                    retry_failed_counter += 1
                    raise Exception("MJPEG source is not available : ", self.name)
                self.cap = cv2.VideoCapture(self.name )
                print("[INFO] New camera started!") 
            except cv2.error as e:
                print("[ERROR] ' (cv error) error when initialize camera,' ", e)
                time.sleep(1)
            except Exception as e:
                print("[ERROR] 'error when initialize camera,' ", e)
                time.sleep(1)
                if retry_failed_counter > 3 :
                    print("[ERROR] 'retry_failed_counter' exceeded, throw an exeption and stop retrying.")
                    self.cap = DummyVideoCapture()            

    def _reader(self):
        while self.cap.isOpened() :
            try :
                ret, frame = self.cap.read()
                if not ret :
                    self.cap.release()
                    print("[INFO] Invalid image!") 
                    
                    print("[INFO] Restart camera in 30 seconds!")
                    time.sleep(30)
                    
                    print("[INFO] Initialize new camera!") 
                    self.initializeVideoCapture()
                    continue

                if not self.q.empty():
                    try:
                        self.q.get_nowait() 
                    except queue.Empty:
                        pass
                self.q.put(frame)
            except cv2.error as e:
                print("[ERROR] ' (cv error) error when read frame from camera,' ", e)
                time.sleep(1)
            except Exception as e:
                print("[ERROR] 'error when read frame from camera,' ", e)
                time.sleep(1)

    def read(self):
        try :
            return True, self.q.get()
        except Exception as e:
            print("[ERROR] Custom Video Capture read,", e)
            return False, None
    
    def isOpened(self):
        return self.cap.isOpened()

    def release(self):
        return self.cap.release()

class DummyVideoCapture():
    def isOpened(self):
        return False

class CameraStream():
    def __init__(self, cap_source):
        self.cap_source = cap_source
        self.cap = CustomVideoCapture(self.cap_source) 
        self.cam_bot = HomeCamBot()
        self.detector = Detector()
        self.lastFaceSent = 0
        self.lastDetectedPoint = [0, 0]
        self.minDetectedDist = 50 # less than this distance will be classified as same object and no longer be sent again to telegram

    def checkAboveDetectedDist(self, pt):
        aboveDetectedDist = math.dist(pt, self.lastDetectedPoint) >= self.minDetectedDist
        if (aboveDetectedDist) :
           self.lastDetectedPoint = pt 
        return aboveDetectedDist

    def run(self): 
        while self.cap.isOpened() :
            ret, img = self.cap.read()
            try :
                HasObject, detected_objects, img = self.detector.detect(img)
                
                if HasObject and (time.time() - self.lastFaceSent) > 5:
                    if (self.checkAboveDetectedDist(detected_objects[0].get('pt'))) :
                        self.lastFaceSent = time.time()
                        TimeStr = datetime.datetime.now().strftime("%H:%M:%S")
                        object_str =  " ".join(["%d %s," % (i.get('count'), i.get('name')) for i in detected_objects])
                        msg = "Detected %s in image at %s" % (object_str, TimeStr)
                        imgPath = "image/photo.jpg"
                        cv2.imwrite(imgPath, img)
                        try :
                            message = self.cam_bot.SendPhoto(open(imgPath, 'rb'), msg)
                            print("[INFO] Detecting object, send image to Telegram with message :\n%s\n" % message)
                        except Exception as e:
                            print("[ERROR] 'error when send to telegram,' ", e)
                    else : 
                       print("[INFO] 'detected object with no movement, image will not sent to telegram' ") 

                try : 
                    CurrTime = datetime.datetime.now()
                    if CurrTime.minute in {0, 30} : 
                        if not self.cam_bot.HeartBeatSent:
                            self.cam_bot.SendMessage("[INFO] heart beat msg, camera %s status : %r " % (os.environ['CAMERA_NAME'], self.cap.isOpened()))
                    else :
                        self.cam_bot.HeartBeatSent = False
                except Exception as e:
                    print("[ERROR] 'error when send to telegram,' ", e)

            except Exception as e:
                print("[ERROR] ", e)
        else : 
            self.cap.release()
            print("Camera Closed!")
            self.cam_bot.SendMessage("[INFO] heart beat msg, camera %s status : CAMERA CLOSED " % (os.environ['CAMERA_NAME']))

if __name__ == '__main__':
    print("\n\n---- Object Detection service starting! ----\n\n")
    cap_source = os.environ['MJPEG_URL']
    i = 0
    while i < 3 :
        stream = CameraStream(cap_source)
        stream.run()
        time.sleep(60)
        
        print("\n\n[INFO] Retry (%d) to open camera in %s \n\n" % (i, datetime.datetime.now().strftime("%H:%M:%S")))
        i += 1
