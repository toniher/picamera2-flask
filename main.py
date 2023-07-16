#!/usr/bin/env python

from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
from libcamera import Transform
import io
from threading import Condition
import time
import os

from flask import Flask, jsonify, redirect, render_template, Response
# from flask_login import LoginManager, UserMixin
# from flask_wtf import FlaskForm
# from werkzeug.urls import url_parse
#
# Code from: https://github.com/raspberrypi/picamera2/issues/366
# Code from: https://github.com/EbenKouao/pi-camera-stream-flask

# Dir path where to save
dirpath = "/tmp"


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


class Camera:

    def __init__(self):
        self.interface = Picamera2()
        self.is_stopped = False

    def stop(self):
        if self.interface.encoder is not None:
            self.interface.stop_encoder()
        self.interface.close()
        self.is_stopped = True


# class User(UserMixin):
#     def __init__(self, name, password):
#         self.name = name
#         self.password = password
#
#     def check_password(self, password):
#         if password == self.password:
#             return True
#         return False
#
#     def __repr__(self):
#         return '<User>'.format(self.name)
#
#
# class LoginForm(FlaskForm):
#     password = PasswordField('Password', validators=[DataRequired()])
#     remember_me = BooleanField('Submit')
#     submit = SubmitField('Login')
#

# App Globals
app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'secret_key_for_flask'
# login_manager = LoginManager(app)

camera = None


def open_camera():
    camera = Camera()
    return camera


def close_camera():
    global camera
    if camera is not None:
        camera.stop()
        print(camera)
        camera = None
        print(camera)
    return camera


def get_camera():
    return camera


def genFrames(camera):
    # buffer = StreamingOutput()
    output = StreamingOutput()
    video_config = camera.interface.create_video_configuration(main={
                "size": (640, 480)}, transform=Transform(180))
    camera.interface.configure(video_config)
    output = StreamingOutput()
    camera.interface.start_recording(JpegEncoder(), FileOutput(output))
    while True:
        stopped = camera.is_stopped
        if stopped:
            camera.interface.stop_recording()
            break
        else:
            with output.condition:
                output.condition.wait()
                frame = output.frame
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


def captureImage(camera):
    status = "failed"
    try:
        camera_config = camera.interface.create_still_configuration(main={
                "size": (640, 480)}, transform=Transform(180))
        filename = time.strftime("%Y%m%d-%H%M%S") + '.jpg'
        savepath = os.path.join(dirpath, filename)
        camera.interface.start()
        camera.interface.switch_mode_and_capture_file(camera_config, savepath)
        status = "success"
    finally:
        close_camera()
        # camera.interface.stop()
        # camera.interface.close()
    return {'status': status}


@app.route('/index.html')
def indexhtml():
    return redirect('/')


@app.route('/')
def index():
    return render_template('index.html')  # you can customze index.html here


@app.route('/capture')
def capture():
    global camera
    status = get_camera()
    print(status)
    if status is None:
        camera = open_camera()
    else:
        camera = close_camera()
        camera = open_camera()
    outcome = captureImage(camera)
    return jsonify(outcome)


# defines the route that will access the video feed and call the feed function
@app.route('/video_feed')
def video_feed():
    global camera
    status = get_camera()
    print(status)
    if status is None:
        camera = open_camera()
    else:
        camera = close_camera()
        camera = open_camera()
    return Response(genFrames(camera),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/stop')
def stop():
    global camera
    status = get_camera()
    if status is not None:
        camera = close_camera()
    print(camera)
    outcome = {'status': 'stopped'}
    return jsonify(outcome)


@app.route('/start')
def start():
    status = get_camera()
    print(status)
    if status is None:
        print("Open Camera")
        global camera
        camera = open_camera()
    outcome = {'status': 'started'}
    return jsonify(outcome)


# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if current_user.is_authenticated:
#         return redirect(url_for('index'))
#     form = LoginForm()
#     if form.validate_on_submit():
#         user = User()
#         if user is not None and user.check_password(form.password.data):
#             login_user(user, remember=form.remember_me.data)
#             next_page = request.args.get('next')
#             if not next_page or url_parse(next_page).netloc != '':
#                 next_page = url_for('index')
#             return redirect(next_page)
#     return render_template('login_form.html', form=form)
#
#
# @app.route('/logout')
# def logout():
#     logout_user()
#     return redirect(url_for('index'))
#
#
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
