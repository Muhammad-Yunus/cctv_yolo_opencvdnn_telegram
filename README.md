# CCTV Yolo OpenCV DNN send to Telegram 

- Clone repository,

```
cd ~
mkdir Github
cd Github
git clone https://github.com/Muhammad-Yunus/cctv_facedetection_telegram.git
```
- Build docker image,

```
cd ~
docker build --pull --rm -f "Github/cctv_yolo_opencvdnn_telegram/Dockerfile" -t cctv_yolo_telegram_bot:latest "Github/cctv_yolo_opencvdnn_telegram"
```
- Run Image, 
```
docker run --rm -d --name cctv_yolo_telegram_bot  -p 8080:8080/tcp \
-e BOT_TOKEN='TELEGRAM_BOT_TOKEN' \
-e CHAT_ID='TELEGRAM_CHAT_ID' \
-e MJPEG_URL="MJPEG_URL_CAMERA" \
-e CAMERA_NAME="CAM-001" \
-e "TZ=Asia/Jakarta" \
cctv_yolo_telegram_bot:latest

```
