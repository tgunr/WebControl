# main.py
from app import app, socketio
from gevent import monkey
import webbrowser
import socket
import math
import os


#monkey.patch_all(thread = False, threading = False) 
monkey.patch_all()
    
import schedule
import time
import threading
import json

from flask import Flask, jsonify, render_template, current_app, request, flash, Response, send_file, send_from_directory
from flask_mobility.decorators import mobile_template
from werkzeug import secure_filename
from Background.UIProcessor import UIProcessor  # do this after socketio is declared
from Background.LogStreamer import LogStreamer  # do this after socketio is declared
from Background.WebMCPProcessor import WebMCPProcessor
from Background.WebMCPProcessor import ConsoleProcessor
from DataStructures.data import Data
from Connection.nonVisibleWidgets import NonVisibleWidgets
from WebPageProcessor.webPageProcessor import WebPageProcessor

from os import listdir
from os.path import isfile, join


app.data = Data()
app.nonVisibleWidgets = NonVisibleWidgets()
app.nonVisibleWidgets.setUpData(app.data)
app.data.config.computeSettings(None, None, None, True)
app.data.config.parseFirmwareVersions()
app.data.units = app.data.config.getValue("Computed Settings", "units")
app.data.tolerance = app.data.config.getValue("Computed Settings", "tolerance")
app.data.distToMove = app.data.config.getValue("Computed Settings", "distToMove")
app.data.distToMoveZ = app.data.config.getValue("Computed Settings", "distToMoveZ")
app.data.unitsZ = app.data.config.getValue("Computed Settings", "unitsZ")
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
app.LogStreamer = LogStreamer()

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

## this runs the thread that sends debugging messages to the terminal and webmcp (if active)
app.th2 = threading.Thread(target=app.data.consoleProcessor.start)
app.th2.daemon = True
app.th2.start()

## uithread set to None.. will be activated upon first websocket connection from browser
app.uithread = None

## uithread set to None.. will be activated upon first websocket connection from webmcp
app.mcpthread = None

## logstreamerthread set to None.. will be activated upon first websocket connection from log streamer browser
app.logstreamerthread = None


@app.route("/")
@mobile_template("{mobile/}")
def index(template):
    app.data.logger.resetIdler()
    if template == "mobile/":
        return render_template("frontpage3d_mobile.html", modalStyle="modal-lg")
    else:
        return render_template("frontpage3d.html", modalStyle="mw-100 w-75")

@app.route('/GPIO', methods=['PUT', 'GET'])
def remote_function_call():
    if (request.method == "PUT"):
        print ("remote function call")
        result = request.data
        result = result.decode('utf-8')
        resultlist = result.split(':')
        print ('resultlist', resultlist)
        if ('system' in resultlist):
            print ('system selected')
            if ('exit' in resultlist):
              print ('shutdown')
              app.nonVisibleWidgets.actions.shutdown()
        if ('gcode' in resultlist):
            print ('gcode selected')
            if ('startRun' in resultlist):
              print ('start gcode requested')
              app.nonVisibleWidgets.actions.startRun()
              return ("run")
            if ('pauseRun' in resultlist):
              print ('pause gcode requested')
              app.nonVisibleWidgets.actions.pauseRun()
              return ("pause")
            if (resultlist[1] == 'resumeRun'):
              print ('continue gcode requested')
              app.nonVisibleWidgets.actions.resumeRun()
              return ("resume")
            if (resultlist[1] == 'stopRun'):
              print ('stop gcode requested')
              app.nonVisibleWidgets.actions.stopRun()
              return ("stopped")
        if ('system' in resultlist):
            print ('system selected')
            if ('exit' in resultlist):
                print("system shutdown requested")
                os._exit(0)
        if ('GPIO' in resultlist):
            setValues = app.data.config.getJSONSettingSection("GPIO Settings")
            return(setValues)
        return ('data:125')
    if (request.method == "GET"):
        dataout = 'index:' + str(app.data.gcodeIndex), 'flag:'+ str(app.data.uploadFlag)
        return jsonify(dataout)
    
@app.route('/pendant', methods=['PUT', 'GET'])
def WiiMoteInput():
    print ("remote function call")
    result = request.data
    result = result.decode('utf-8')
    resultlist = result.split(':')
    print ('resultlist', resultlist)
    if (len(resultlist) > 2):
        distance = resultlist[2]
    if ('move' in resultlist):
        print ('move selected')
        if('up' in resultlist):
            print ('move', distance, 'up')
            app.nonVisibleWidgets.actions.move("up", distance)
        if('down' in resultlist):
            print ('move', distance, 'down')
            app.nonVisibleWidgets.actions.move("down", distance)
        if('left' in resultlist):
            print ('move', distance, 'left')
            app.nonVisibleWidgets.actions.move("left", distance)
        if('right' in resultlist):
            print ('move', distance, 'right')
            app.nonVisibleWidgets.actions.move("right", distance)
    if ('zAxis' in resultlist):
        print ('zaxis selected')
        if('raise' in resultlist):
            print ('zaxis', distance, 'raise')
            app.nonVisibleWidgets.actions.moveZ("raise", distance)
        if('lower' in resultlist):
            print ('zaxis', distance, 'lower')
            app.nonVisibleWidgets.actions.moveZ("lower", distance)
        if('stopZ' in resultlist):
            print ('zaxis stop')
            app.nonVisibleWidgets.actions.stopZ()
        if('defineZ0' in resultlist):
            print ('new Z axis zero point')
            app.nonVisibleWidgets.actions.defineZ0()
    if ('sled' in resultlist):
        if('home' in resultlist):
            print ('go home')
            app.nonVisibleWidgets.actions.home()
        if('defineHome' in resultlist):
            print ('new home set')
            app.nonVisibleWidgets.actions.defineHome()
    if ('system' in resultlist):
        print ('system selected')
        if ('exit' in resultlist):
            print("system shutdown requested")
            os._exit(0)
        if ('connected' in resultlist):
            print("wiimote connected")
            app.data.wiiPendantConnected = True
        if ('disconnect' in resultlist):
            print("wiimote disconnect")
            app.data.wiiPendantConnected = False    
        return ('data:125')
           

@app.route("/controls")
@mobile_template("/controls/{mobile/}")
def controls(template):
    app.data.logger.resetIdler()
    if template == "/controls/mobile/":
        return render_template("frontpage3d_mobilecontrols.html", modalStyle="modal-lg", isControls=True)
    else:
        return render_template("frontpage3d.html", modalStyle="mw-100 w-75")

@app.route("/logs")
@mobile_template("/logs/{mobile/}")
def logs(template):
    print("here")
    app.data.logger.resetIdler()
    if template == "/logs/mobile/":
        return render_template("logs.html")
    else:
        return render_template("logs.html")


@app.route("/maslowSettings", methods=["POST"])
def maslowSettings():
    app.data.logger.resetIdler()
    if request.method == "POST":
        result = request.form
        app.data.config.updateSettings("Maslow Settings", result)
        message = {"status": 200}
        resp = jsonify(message)
        resp.status_code = 200
        return resp


@app.route("/advancedSettings", methods=["POST"])
def advancedSettings():
    app.data.logger.resetIdler()
    if request.method == "POST":
        result = request.form
        app.data.config.updateSettings("Advanced Settings", result)
        message = {"status": 200}
        resp = jsonify(message)
        resp.status_code = 200
        return resp


@app.route("/webControlSettings", methods=["POST"])
def webControlSettings():
    app.data.logger.resetIdler()
    if request.method == "POST":
        result = request.form
        app.data.config.updateSettings("WebControl Settings", result)
        message = {"status": 200}
        resp = jsonify(message)
        resp.status_code = 200
        return resp


@app.route("/cameraSettings", methods=["POST"])
def cameraSettings():
    app.data.logger.resetIdler()
    if request.method == "POST":
        result = request.form
        app.data.config.updateSettings("Camera Settings", result)
        message = {"status": 200}
        resp = jsonify(message)
        resp.status_code = 200
        return resp

@app.route("/gpioSettings", methods=["POST"])
def gpioSettings():
    app.data.logger.resetIdler()
    if request.method == "POST":
        result = request.form
        app.data.config.updateSettings("GPIO Settings", result)
        message = {"status": 200}
        resp = jsonify(message)
        resp.status_code = 200
        return resp
        
@app.route("/uploadGCode", methods=["POST"])
def uploadGCode():
    app.data.logger.resetIdler()
    if request.method == "POST":
        result = request.form
        directory = result["selectedDirectory"]
        #print(directory)
        f = request.files["file"]
        home = app.data.config.getHome()
        app.data.config.setValue("Computed Settings", "lastSelectedDirectory", directory)
        app.data.gcodeFile.filename = home+"/.WebControl/gcode/" + directory+"/"+secure_filename(f.filename)
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
    app.data.logger.resetIdler()
    if request.method == "POST":
        f = request.form["selectedGCode"]
        app.data.console_queue.put("selectedGcode="+str(f))
        tDir = f.split("/")
        app.data.config.setValue("Computed Settings","lastSelectedDirectory",tDir[0])
        home = app.data.config.getHome()
        app.data.gcodeFile.filename = home+"/.WebControl/gcode/" + f
        app.data.config.setValue("Maslow Settings", "openFile", tDir[1])
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

@app.route("/saveGCode", methods=["POST"])
def saveGCode():
    app.data.logger.resetIdler()
    if request.method == "POST":
        print(request.form)
        f = request.form["fileName"]
        d = request.form["selectedDirectory"]
        app.data.console_queue.put("selectedGcode="+f)
        app.data.config.setValue("Computed Settings", "lastSelectedDirectory",d)
        home = app.data.config.getHome()
        returnVal = app.data.gcodeFile.saveFile(f, home+"/.WebControl/gcode/"+d)
        '''
        tDir = f.split("/")
        app.data.config.setValue("Computed Settings","lastSelectedDirectory",tDir[0])
        home = app.data.config.getHome()
        app.data.gcodeFile.filename = home+"/.WebControl/gcode/" + f
        app.data.config.setValue("Maslow Settings", "openFile", tDir[1])
        returnVal = app.data.gcodeFile.loadUpdateFile()
        '''
        if returnVal:
            app.data.config.setValue("Maslow Settings", "openFile", f)
            message = {"status": 200}
            resp = jsonify(message)
            resp.status_code = 200
            return resp
        else:
            message = {"status": 500}
            resp = jsonify(message)
            resp.status_code = 500
            return resp

@app.route("/openBoard", methods=["POST"])
def openBoard():
    app.data.logger.resetIdler()
    if request.method == "POST":
        f = request.form["selectedBoard"]
        app.data.console_queue.put("selectedBoard="+str(f))
        tDir = f.split("/")
        app.data.config.setValue("Computed Settings","lastSelectedBoardDirectory",tDir[0])
        home = app.data.config.getHome()
        app.data.gcodeFile.filename = home+"/.WebControl/boards/" + f
        app.data.config.setValue("Maslow Settings", "openBoardFile", tDir[1])
        returnVal = app.data.boardManager.loadBoard(home+"/.WebControl/boards/"+f)
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

@app.route("/saveBoard", methods=["POST"])
def saveBoard():
    app.data.logger.resetIdler()
    if request.method == "POST":
        print(request.form)
        f = request.form["fileName"]
        d = request.form["selectedDirectory"]
        app.data.console_queue.put("selectedBoard="+f)
        app.data.config.setValue("Computed Settings", "lastSelectedBoardDirectory",d)
        home = app.data.config.getHome()
        returnVal = app.data.boardManager.saveBoard(f, home+"/.WebControl/boards/"+d)
        app.data.config.setValue("Maslow Settings", "openBoardFile", f)
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
    app.data.logger.resetIdler()
    if request.method == "POST":
        f = request.files["file"]
        home = app.data.config.getHome()
        secureFilename = home+"/.WebControl/imports/" + secure_filename(f.filename)
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

@app.route("/importFileWCJSON", methods=["POST"])
def importFileJSON():
    app.data.logger.resetIdler()
    if request.method == "POST":
        f = request.files["file"]
        home = app.data.config.getHome()
        secureFilename = home + "/.WebControl/imports/" + secure_filename(f.filename)
        f.save(secureFilename)
        returnVal = app.data.importFile.importWebControlJSON(secureFilename)
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

@app.route("/importRestoreWebControl", methods=["POST"])
def importRestoreWebControl():
    app.data.logger.resetIdler()
    if request.method == "POST":
        f = request.files["file"]
        home = app.data.config.getHome()
        secureFilename = home + "/" + secure_filename(f.filename)
        f.save(secureFilename)
        returnVal = app.data.actions.restoreWebControl(secureFilename)
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

@app.route("/sendGCode", methods=["POST"])
def sendGcode():
    app.data.logger.resetIdler()
    #print(request.form)#["gcodeInput"])
    if request.method == "POST":
        returnVal = app.data.actions.sendGCode(request.form["gcode"])
        if returnVal:
            message = {"status": 200}
            resp = jsonify("success")
            resp.status_code = 200
            return resp
        else:
            message = {"status": 500}
            resp = jsonify("failed")
            resp.status_code = 500
            return resp


@app.route("/triangularCalibration", methods=["POST"])
def triangularCalibration():
    app.data.logger.resetIdler()
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

@app.route("/holeyCalibration", methods=["POST"])
def holeyCalibration():
    app.data.logger.resetIdler()
    if request.method == "POST":
        result = request.form
        motorYoffsetEst, distanceBetweenMotors, leftChainTolerance, rightChainTolerance, calibrationError = app.data.actions.holeyCalibrate(
            result
        )
        # print(returnVal)
        if motorYoffsetEst:
            message = {
                "status": 200,
                "data": {
                    "motorYoffset": motorYoffsetEst,
                    "distanceBetweenMotors": distanceBetweenMotors,
                    "leftChainTolerance": leftChainTolerance,
                    "rightChainTolerance": rightChainTolerance,
                    "calibrationError": calibrationError
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
    app.data.logger.resetIdler()
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
    app.data.logger.resetIdler()
    if request.method == "POST":
        result = request.form
        app.data.config.updateQuickConfigure(result)
        message = {"status": 200}
        resp = jsonify(message)
        resp.status_code = 200
        return resp

@app.route("/editGCode", methods=["POST"])
def editGCode():
    app.data.logger.resetIdler()
    #print(request.form["gcode"])
    if request.method == "POST":
        returnVal = app.data.actions.updateGCode(request.form["gcode"])
        if returnVal:
            message = {"status": 200}
            resp = jsonify("success")
            resp.status_code = 200
            return resp
        else:
            message = {"status": 500}
            resp = jsonify("failed")
            resp.status_code = 500
            return resp

@app.route("/downloadDiagnostics", methods=["GET"])
def downloadDiagnostics():
    app.data.logger.resetIdler()
    if request.method == "GET":
        returnVal = app.data.actions.downloadDiagnostics()
        if  returnVal != False:
            print(returnVal)
            return send_file(returnVal, as_attachment=True)
        else:
            resp = jsonify("failed")
            resp.status_code = 500
            return resp

@app.route("/backupWebControl", methods=["GET"])
def backupWebControl():
    app.data.logger.resetIdler()
    if request.method == "GET":
        returnVal = app.data.actions.backupWebControl()
        if returnVal != False:
            print(returnVal)
            return send_file(returnVal)
        else:
            resp = jsonify("failed")
            resp.status_code = 500
            return resp


@app.route("/editBoard", methods=["POST"])
def editBoard():
    app.data.logger.resetIdler()
    if request.method == "POST":
        returnVal = app.data.boardManager.editBoard(request.form)
        if returnVal:
            resp = jsonify("success")
            resp.status_code = 200
            return resp
        else:
            resp = jsonify("failed")
            resp.status_code = 500
            return resp

@app.route("/trimBoard", methods=["POST"])
def trimBoard():
    app.data.logger.resetIdler()
    if request.method == "POST":
        returnVal = app.data.boardManager.trimBoard(request.form)
        if returnVal:
            resp = jsonify("success")
            resp.status_code = 200
            return resp
        else:
            resp = jsonify("failed")
            resp.status_code = 500
            return resp

@app.route("/assets/<path:path>")
def sendDocs(path):
    print(path)
    return send_from_directory('docs/assets/', path)


@socketio.on("checkInRequested", namespace="/WebMCP")
def checkInRequested():
    socketio.emit("checkIn", namespace="/WebMCP")


@socketio.on("connect", namespace="/WebMCP")
def watchdog_connect():
    app.data.console_queue.put("watchdog connected")
    app.data.console_queue.put(request.sid)
    socketio.emit("connect", namespace="/WebMCP")
    if app.mcpthread == None:
        app.data.console_queue.put("going to start mcp thread")
        app.mcpthread = socketio.start_background_task(
            app.data.mcpProcessor.start, current_app._get_current_object()
        )
        app.data.console_queue.put("created mcp thread")
        app.mcpthread.start()
        app.data.console_queue.put("started mcp thread")


@socketio.on("my event", namespace="/MaslowCNC")
def my_event(msg):
    app.data.console_queue.put(msg["data"])


@socketio.on("modalClosed", namespace="/MaslowCNC")
def modalClosed(msg):
    app.data.logger.resetIdler()
    data = json.dumps({"title": msg["data"]})
    socketio.emit("message", {"command": "closeModals", "data": data, "dataFormat": "json"},
                  namespace="/MaslowCNC", )


@socketio.on("contentModalClosed", namespace="/MaslowCNC")
def contentModalClosed(msg):
    #Note, this shouldn't be called anymore
    #todo: cleanup
    app.data.logger.resetIdler()
    data = json.dumps({"title": msg["data"]})
    print(data)
    #socketio.emit("message", {"command": "closeContentModals", "data": data, "dataFormat": "json"},
    #              namespace="/MaslowCNC", )

'''
todo: cleanup
not used
@socketio.on("actionModalClosed", namespace="/MaslowCNC")
def actionModalClosed(msg):
    app.data.logger.resetIdler()
    data = json.dumps({"title": msg["data"]})
    socketio.emit("message", {"command": "closeActionModals", "data": data, "dataFormat": "json"},
                  namespace="/MaslowCNC", )
'''

@socketio.on("alertModalClosed", namespace="/MaslowCNC")
def alertModalClosed(msg):
    app.data.logger.resetIdler()
    data = json.dumps({"title": msg["data"]})
    socketio.emit("message", {"command": "closeAlertModals", "data": data, "dataFormat": "json"},
                  namespace="/MaslowCNC", )


@socketio.on("requestPage", namespace="/MaslowCNC")
def requestPage(msg):
    app.data.logger.resetIdler()
    app.data.console_queue.put(request.sid)
    client = request.sid
    try:
        page, title, isStatic, modalSize, modalType, resume = app.webPageProcessor.createWebPage(msg["data"]["page"],msg["data"]["isMobile"], msg["data"]["args"])
        #if msg["data"]["page"] != "help":
        #    client = "all"
        data = json.dumps({"title": title, "message": page, "isStatic": isStatic, "modalSize": modalSize, "modalType": modalType, "resume":resume, "client":client})
        socketio.emit("message", {"command": "activateModal", "data": data, "dataFormat": "json"},
            namespace="/MaslowCNC",
        )
    except Exception as e:
        app.data.console_queue.put(e)

@socketio.on("connect", namespace="/MaslowCNC")
def test_connect():
    app.data.console_queue.put("connected")
    app.data.console_queue.put(request.sid)
    if app.uithread == None:
        app.uithread = socketio.start_background_task(
            app.UIProcessor.start, current_app._get_current_object()
        )
        app.uithread.start()

    if not app.data.connectionStatus:
        app.data.console_queue.put("Attempting to re-establish connection to controller")
        app.data.serialPort.openConnection()

    socketio.emit("my response", {"data": "Connected", "count": 0})
    address = app.data.hostAddress
    data = json.dumps({"hostAddress": address})
    print(data)
    socketio.emit("message", {"command": "hostAddress", "data": data, "dataFormat":"json"}, namespace="/MaslowCNC",)
    if app.data.pyInstallUpdateAvailable:
        app.data.ui_queue1.put("Action", "pyinstallUpdate", "on")

@socketio.on("disconnect", namespace="/MaslowCNC")
def test_disconnect():
    app.data.console_queue.put("Client disconnected")


@socketio.on("action", namespace="/MaslowCNC")
def command(msg):
    app.data.logger.resetIdler()
    retval = app.data.actions.processAction(msg)
    if retval == "Shutdown":
        print("Shutting Down")
        socketio.stop()
        print("Shutdown")


@socketio.on("settingRequest", namespace="/MaslowCNC")
def settingRequest(msg):
    app.data.logger.resetIdler()
    # didn't move to actions.. this request is just to send it computed values.. keeping it here makes it faster than putting it through the UIProcessor
    setting, value = app.data.actions.processSettingRequest(msg["data"]["section"], msg["data"]["setting"])
    if setting is not None:
        data = json.dumps({"setting": setting, "value": value})
        socketio.emit("message", {"command": "requestedSetting", "data": data, "dataFormat": "json"}, namespace="/MaslowCNC",)

@socketio.on("updateSetting", namespace="/MaslowCNC")
def updateSetting(msg):
    app.data.logger.resetIdler()
    if not app.data.actions.updateSetting(msg["data"]["setting"], msg["data"]["value"]):
        app.data.ui_queue1.put("Alert", "Alert", "Error updating setting")


@socketio.on("checkForGCodeUpdate", namespace="/MaslowCNC")
def checkForGCodeUpdate(msg):
    app.data.logger.resetIdler()
    # this currently doesn't check for updated gcode, it just resends it..
    ## the gcode file might change the active units so we need to inform the UI of the change.
    app.data.ui_queue1.put("Action", "unitsUpdate", "")
    app.data.ui_queue1.put("Action", "gcodeUpdate", "")

@socketio.on("checkForBoardUpdate", namespace="/MaslowCNC")
def checkForBoardUpdate(msg):
    app.data.logger.resetIdler()
    # this currently doesn't check for updated board, it just resends it..
    app.data.ui_queue1.put("Action", "boardUpdate", "")

@socketio.on("connect", namespace="/MaslowCNCLogs")
def log_connect():
    app.data.console_queue.put("connected to log")
    app.data.console_queue.put(request.sid)
    if app.logstreamerthread == None:
        app.logstreamerthread = socketio.start_background_task(
            app.LogStreamer.start, current_app._get_current_object()
        )
        app.logstreamerthread.start()

    socketio.emit("my response", {"data": "Connected", "count": 0}, namespace="/MaslowCNCLog")

@socketio.on("disconnect", namespace="/MaslowCNCLogs")
def log_disconnect():
    app.data.console_queue.put("Client disconnected")


@app.template_filter('isnumber')
def isnumber(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
        
#def shutdown():
#    print("Shutdown")


if __name__ == "__main__":
    app.debug = False
    app.config["SECRET_KEY"] = "secret!"
    #look for touched file
    app.data.config.checkForTouchedPort()
    webPort = app.data.config.getValue("WebControl Settings", "webPort")
    webPortInt = 5000
    try:
        webPortInt = int(webPort)
        if webPortInt < 0 or webPortInt > 65535:
            webPortInt = 5000
    except Exception as e:
        app.data.console_queue.put(e)
        app.data.console_queue.put("Invalid port assignment found in webcontrol.json")

    print("-$$$$$-")
    print(os.path.abspath(__file__))
    app.data.releaseManager.processAbsolutePath(os.path.abspath(__file__))
    print("-$$$$$-")


    print("opening browser")
    webPortStr = str(webPortInt)
    webbrowser.open_new_tab("http://localhost:"+webPortStr)
    host_name = socket.gethostname()
    host_ip = socket.gethostbyname(host_name)
    app.data.hostAddress = host_ip + ":" + webPortStr
    
    #app.data.shutdown = shutdown
    socketio.run(app, use_reloader=False, host="0.0.0.0", port=webPortInt)
    # socketio.run(app, host='0.0.0.0')

