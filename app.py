import telegram
import datetime
import time
import cv2
import os
import queue 
import threading
import numpy as np

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
        self.cap = cv2.VideoCapture(self.name)
        self.q = queue.Queue()
        t = threading.Thread(target=self._reader)
        t.daemon = True
        t.start()

    def _reader(self):
        while self.cap.isOpened() :
            ret, frame = self.cap.read()
            if not ret :
                self.cap.release()
                print("[INFO] Invalid image!") 
                
                print("[INFO] Restart camera in 2 seconds!")
                time.sleep(2)
                
                print("[INFO] Initialize new camera!") 
                self.cap = None
                while self.cap == None :
                    try :
                        self.cap = cv2.VideoCapture(self.name)
                    except Exception as e:
                        print("[ERROR] 'error when initialize camera,' ", e)
                        time.sleep(1)
                continue
            if not self.q.empty():
                try:
                    self.q.get_nowait() 
                except queue.Empty:
                    pass
            self.q.put(frame)

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

class CameraStream():
    def __init__(self, cap_source):
        self.cap_source = cap_source
        self.cap = CustomVideoCapture(self.cap_source) 
        self.cam_bot = HomeCamBot()
        self.detector = Detector()
        self.lastFaceSent = 0

    def run(self): 
        while self.cap.isOpened() :
            ret, img = self.cap.read()
            try :
                HasObject, detected_objects, img = self.detector.detect(img)
                
                if HasObject and (time.time() - self.lastFaceSent) > 5:
                    self.lastFaceSent = time.time()
                    TimeStr = datetime.datetime.now().strftime("%H:%M:%S")
                    object_str =  " ".join(["%d %s," % (i.get('count'), i.get('name')) for i in detected_objects])
                    msg = "Detected %s in image at %s" % (object_str, TimeStr)
                    imgPath = "image/photo_%s.jpg" % TimeStr
                    cv2.imwrite(imgPath, img)
                    try :
                        message = self.cam_bot.SendPhoto(open(imgPath, 'rb'), msg)
                        print("[INFO] Detecting object, send image to Telegram with message :\n%s\n" % message)
                    except Exception as e:
                        print("[ERROR] 'error when send to telegram,' ", e)

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
    print("Object Detection service starting!\n")
    cap_source = os.environ['MJPEG_URL']
    i = 0
    while i < 7 :
        stream = CameraStream(cap_source)
        stream.run()
        time.sleep(5)
        
        print("\n\nRetry %d to open camera in %s \n\n" % (i, datetime.datetime.now().strftime("%H:%M:%S")))
        i += 1