# main.py
from app import app, socketio
from gevent import monkey

monkey.patch_all()

import schedule
import time
import threading
import json

from flask import Flask, jsonify, render_template, current_app, request, flash
from flask_mobility.decorators import mobile_template
from werkzeug import secure_filename
from Background.UIProcessor import UIProcessor  # do this after socketio is declared
from DataStructures.data import Data
from Connection.nonVisibleWidgets import NonVisibleWidgets
from WebPageProcessor.webPageProcessor import WebPageProcessor
from os import listdir
from os.path import isfile, join


app.data = Data()
app.nonVisibleWidgets = NonVisibleWidgets()
app.nonVisibleWidgets.setUpData(app.data)
app.data.config.computeSettings(None, None, None, True)
app.data.units = app.data.config.getValue("Computed Settings", "units")
app.data.comport = app.data.config.getValue("Maslow Settings", "COMport")
app.data.gcodeShift = [
    float(app.data.config.getValue("Advanced Settings", "homeX")),
    float(app.data.config.getValue("Advanced Settings", "homeY")),
]
app.data.firstRun = False
# app.previousPosX = 0.0
# app.previousPosY = 0.0

app.UIProcessor = UIProcessor()
app.webPageProcessor = WebPageProcessor(app.data)

## this defines the schedule for running the serial port open connection
def run_schedule():
    while 1:
        schedule.run_pending()
        time.sleep(1)

## this runs the scheduler to check for connections
app.th = threading.Thread(target=run_schedule)
app.th.daemon = True
app.th.start()

## this runs the thread that processes messages from the controller
app.th1 = threading.Thread(target=app.data.messageProcessor.start)
app.th1.daemon = True
app.th1.start()

## uithread set to None.. will be activated upon first websocket connection
app.uithread = None

@app.route("/")
@mobile_template("{mobile/}")
def index(template):
    current_app._get_current_object()
    if template == "mobile/":
        return render_template("frontpage_mobile.html")
    else:
        return render_template("frontpage.html")


@app.route("/maslowSettings", methods=["POST"])
def maslowSettings():
    if request.method == "POST":
        result = request.form
        app.data.config.updateSettings("Maslow Settings", result)
        message = {"status": 200}
        resp = jsonify(message)
        resp.status_code = 200
        return resp


@app.route("/advancedSettings", methods=["POST"])
def advancedSettings():
    if request.method == "POST":
        result = request.form
        app.data.config.updateSettings("Advanced Settings", result)
        message = {"status": 200}
        resp = jsonify(message)
        resp.status_code = 200
        return resp


@app.route("/webControlSettings", methods=["POST"])
def webControlSettings():
    if request.method == "POST":
        result = request.form
        app.data.config.updateSettings("WebControl Settings", result)
        message = {"status": 200}
        resp = jsonify(message)
        resp.status_code = 200
        return resp


@app.route("/uploadGCode", methods=["POST"])
def uploadGCode():
    if request.method == "POST":
        f = request.files["file"]
        app.data.gcodeFile.filename = "gcode/" + secure_filename(f.filename)
        f.save(app.data.gcodeFile.filename)
        returnVal = app.data.gcodeFile.loadUpdateFile()
        if returnVal:
            message = {"status": 200}
            resp = jsonify(message)
            resp.status_code = 200
            return resp
        else:
            message = {"status": 500}
            resp = jsonify(message)
            resp.status_code = 500
            return resp


@app.route("/openGCode", methods=["POST"])
def openGCode():
    if request.method == "POST":
        f = request.form["selectedGCode"]
        print("selectedGcode="+str(f))
        app.data.gcodeFile.filename = "gcode/" + f
        returnVal = app.data.gcodeFile.loadUpdateFile()
        if returnVal:
            message = {"status": 200}
            resp = jsonify(message)
            resp.status_code = 200
            return resp
        else:
            message = {"status": 500}
            resp = jsonify(message)
            resp.status_code = 500
            return resp


@app.route("/importFile", methods=["POST"])
def importFile():
    if request.method == "POST":
        f = request.files["file"]
        secureFilename = "imports\\" + secure_filename(f.filename)
        f.save(secureFilename)
        returnVal = app.data.importFile.importGCini(secureFilename)
        if returnVal:
            message = {"status": 200}
            resp = jsonify(message)
            resp.status_code = 200
            return resp
        else:
            message = {"status": 500}
            resp = jsonify(message)
            resp.status_code = 500
            return resp


@app.route("/triangularCalibration", methods=["POST"])
def triangularCalibration():
    if request.method == "POST":
        result = request.form
        motorYoffsetEst, rotationRadiusEst, chainSagCorrectionEst, cut34YoffsetEst = app.data.actions.calibrate(
            result
        )
        # print(returnVal)
        if motorYoffsetEst:
            message = {
                "status": 200,
                "data": {
                    "motorYoffset": motorYoffsetEst,
                    "rotationRadius": rotationRadiusEst,
                    "chainSagCorrection": chainSagCorrectionEst,
                    "calibrationError": cut34YoffsetEst,
                },
            }
            resp = jsonify(message)
            resp.status_code = 200
            return resp
        else:
            message = {"status": 500}
            resp = jsonify(message)
            resp.status_code = 500
            return resp


@app.route("/opticalCalibration", methods=["POST"])
def opticalCalibration():
    if request.method == "POST":
        result = request.form
        message = {"status": 200}
        resp = jsonify(message)
        resp.status_code = 200
        return resp
    else:
        message = {"status": 500}
        resp = jsonify(message)
        resp.status_code = 500
        return resp


@app.route("/quickConfigure", methods=["POST"])
def quickConfigure():
    if request.method == "POST":
        result = request.form
        app.data.config.updateQuickConfigure(result)
        message = {"status": 200}
        resp = jsonify(message)
        resp.status_code = 200
        return resp

#Watchdog socketio.. not working yet.
@socketio.on("checkInRequested", namespace="/WebMCP")
def checkInRequested(msg):
    socketio.emit("checkIn")

#Watchdog socketio.. not working yet.
@socketio.on("connect", namespace="/WebMCP")
def watchdog_connect():
    print("connected")
    print(request.sid)
    socketio.emit("my response")


@socketio.on("my event", namespace="/MaslowCNC")
def my_event(msg):
    print(msg["data"])


@socketio.on("modalClosed", namespace="/MaslowCNC")
def modalClosed(msg):
    socketio.emit("closeModals", {"data": {"title": msg["data"]}}, namespace="/MaslowCNC")


@socketio.on("requestPage", namespace="/MaslowCNC")
def requestPage(msg):
    try:
        page, title, isStatic = app.webPageProcessor.createWebPage(msg["data"]["page"],msg["data"]["isMobile"])
        socketio.emit(
            "activateModal",
            {"title": title, "message": page, "isStatic": isStatic},
            namespace="/MaslowCNC",
        )
    except Exception as e:
        print(e)

@socketio.on("connect", namespace="/MaslowCNC")
def test_connect():
    print("connected")
    print(request.sid)
    if app.uithread == None:
        app.uithread = socketio.start_background_task(
            app.UIProcessor.start, current_app._get_current_object()
        )
        app.uithread.start()

    if not app.data.connectionStatus:
        app.data.serialPort.openConnection()

    socketio.emit("my response", {"data": "Connected", "count": 0})


@socketio.on("disconnect", namespace="/MaslowCNC")
def test_disconnect():
    print("Client disconnected")


@socketio.on("action", namespace="/MaslowCNC")
def command(msg):
    app.data.actions.processAction(msg)


@socketio.on("settingRequest", namespace="/MaslowCNC")
def settingRequest(msg):
    # didn't move to actions.. this request is just to send it computed values.. keeping it here makes it faster than putting it through the UIProcessor
    setting, value = app.data.actions.processSettingRequest(msg["data"]["section"],msg["data"]["setting"])
    if setting is not None:
        socketio.emit(
            "requestedSetting",
            {"setting": setting, "value": value},
            namespace="/MaslowCNC",
        )

@socketio.on("updateSetting", namespace="/MaslowCNC")
def updateSetting(msg):
    if not app.data.actions.updateSetting(msg["data"]["setting"], msg["data"]["value"]):
        app.data.ui_queue.put("Message: Error updating setting")


@socketio.on("checkForGCodeUpdate", namespace="/MaslowCNC")
def checkForGCodeUpdate(msg):
    # this currently doesn't check for updated gcode, it just resends it..
    ## the gcode file might change the active units so we need to inform the UI of the change.
    units = app.data.config.getValue("Computed Settings", "units")
    socketio.emit(
        "requestedSetting", {"setting": "units", "value": units}, namespace="/MaslowCNC"
    )
    ## send updated gcode to UI
    socketio.emit(
        "gcodeUpdate",
        {"data": json.dumps([ob.__dict__ for ob in app.data.gcodeFile.line])},
        namespace="/MaslowCNC",
    )


@socketio.on_error_default
def default_error_handler(e):
    print(request.event["message"])  # "my error event"
    print(request.event["args"])  # (data,)1


if __name__ == "__main__":
    app.debug = False
    app.config["SECRET_KEY"] = "secret!"
    socketio.run(app, use_reloader=False, host="0.0.0.0")
    # socketio.run(app, host='0.0.0.0')
