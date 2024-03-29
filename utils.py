import os
import cv2 
import numpy as np 

class Utils():
    def draw_ped(self, img, label, x0, y0, xt, yt, color=(255,127,0), text_color=(255,255,255)):

        y0, yt = max(y0 - 15, 0) , min(yt + 15, img.shape[0])
        x0, xt = max(x0 - 15, 0) , min(xt + 15, img.shape[1])

        (w, h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
        cv2.rectangle(img,
                        (x0, y0 + baseline),  
                        (max(xt, x0 + w), yt), 
                        color, 
                        2)
        cv2.rectangle(img,
                        (x0, y0 - h),  
                        (x0 + w, y0 + baseline), 
                        color, 
                        -1)  
        cv2.putText(img, 
                    label, 
                    (x0, y0),                   
                    cv2.FONT_HERSHEY_SIMPLEX,     
                    0.4,                          
                    text_color,                
                    1,
                    cv2.LINE_AA) 
        return img

    def postprocess(self, outs, frame, classes, include_objects, confThreshold = 0.4, nmsThreshold = 0.3):
        classId = np.argmax(outs[0][0][5:])

        frame_h, frame_w, frame_c = frame.shape
        classIds = []
        confidences = []
        boxes = []
        for out in outs:
            for detection in out:
                scores = detection[5:]
                classId = np.argmax(scores)
                confidence = scores[classId]
                c_x = int(detection[0] * frame_w)
                c_y = int(detection[1] * frame_h)
                w = int(detection[2] * frame_w)
                h = int(detection[3] * frame_h)
                x = int(c_x - w / 2)
                y = int(c_y - h / 2)
                classIds.append(classId)
                confidences.append(float(confidence))
                boxes.append([x, y, w, h])

        indices = cv2.dnn.NMSBoxes(boxes, confidences, confThreshold, nmsThreshold)
        labels_log = []
        coords_log = []
        objs_log = []
        for i in indices:
            i = i[0]
            box = boxes[i]
            x = box[0]
            y = box[1]
            w = box[2]
            h = box[3]

            if classes[classIds[i]] in include_objects :
                label = '%s: %.1f%%' % (classes[classIds[i]], (confidences[i]*100))
                labels_log.append(label)
                coords_log.append([x, y])
                frame = self.draw_ped(frame, label, x, y, x+w, y+h, color=(255,127,0), text_color=(255,255,255))
        
        if len(labels_log) > 0 :
            objs_log = [{"name" : item, "count" : labels_log.count(item), "pt" : coords_log[i]} for i, item in enumerate(set(labels_log))]
        return len(objs_log) > 0, objs_log, frame
