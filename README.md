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
-e BOT_TOKEN='1786311895:AAFZtgMqbeP9Aysy_gD-LD0nCwrHk7qKbvc' \
-e CHAT_ID='-590868765' \
-e MJPEG_URL="https://192.168.0.103:8081/index.jpg" \
-e CAMERA_NAME="CAM-001" \
-e "TZ=Asia/Jakarta" \
cctv_yolo_telegram_bot:latest

```