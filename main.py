#!/usr/bin/python3

import picamera2 #camera module for RPi camera
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
from libcamera import Transform
import io

from flask import Flask, render_template, Response, request, send_from_directory

# Code from: https://github.com/raspberrypi/picamera2/issues/366
# Code from: https://github.com/EbenKouao/pi-camera-stream-flask

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

#defines the function that generates our frames
def genFrames():
    #buffer = StreamingOutput()
    with picamera2.Picamera2() as camera:
        output = StreamingOutput()
        camera.configure(camera.create_video_configuration(main={"size": (640, 480)}, transform=Transform(180)))
        output = StreamingOutput()
        camera.start_recording(JpegEncoder(), FileOutput(output))
        while True:
            with output.condition:
                output.condition.wait()
                frame = output.frame
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# App Globals (do not edit)
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html') #you can customze index.html here

#defines the route that will access the video feed and call the feed function
@app.route('/video_feed')
def video_feed():
    return Response(genFrames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
