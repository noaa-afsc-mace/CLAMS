

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
import devices
from acquisition.SensorMonitor import SensorMonitor
from acquisition.SensorMonitor import selectWinPortDialog
from ui import ui_IcthystickSetup


class Ichthysetupdlg(QDialog, ui_IcthystickSetup.Ui_IchthystickSetup):

    def __init__(self, db=None, workstation=None, parent=None):
        super(Ichthysetupdlg, self).__init__(parent)
        self.setupUi(self)

        #  define some variables
        self.Serial_Baud = None
        self.Serial_Port = None
        self.restartingSerial = False
        self.isClosing = False
        self.serial_threads_finished = True
        self.db = db
        self.workStation = workstation
        self.schema = parent.schema

        #  restore the application state
        self.appSettings = QSettings('FIC', 'IchthyInit')
        size = self.appSettings.value('winsize', QSize(500,340))
        position = self.appSettings.value('winposition', QPoint(10,10))
        self.Serial_Port = self.appSettings.value('Serial_Port', '')
        self.Serial_Baud = self.appSettings.value('Serial_Baud', 9600)

        #  check the current position and size to make sure the app is on the screen
        position, size = self.checkWindowLocation(position, size)
        self.move(position)
        self.resize(size)

        #  set up the GUI
        self.fbSerialPort.setText(self.Serial_Port)
        self.fbBaudRate.setText(str(self.Serial_Baud))
        self.pbSetOutput.setEnabled(False)
        self.pbConnect.setEnabled(True)
        self.pbDisconnect.setEnabled(False)
        self.pbConfigure.setEnabled(True)
        self.pbStartCal.setEnabled(False)

        #  connect GUI signals
        self.pbSetOutput.clicked.connect(self.setOutputUnits)
        self.pbConnect.clicked.connect(self.startSerial)
        self.pbDisconnect.clicked.connect(self.stopSerial)
        self.pbConfigure.clicked.connect(self.setSerialPort)
        self.pbStartCal.clicked.connect(self.startCal)

        #  create a serial monitor object to handle serial IO
        self.smonitor = SensorMonitor.SensorMonitor()
        self.smonitor.SensorDataReceived.connect(self.SerialReceived)
        self.smonitor.SensorsStopped.connect(self.SerialStopped)
        self.smonitor.SensorError.connect(self.SerialError)

        initTimer = QTimer(self)
        initTimer.setSingleShot(True)
        initTimer.timeout.connect(self.queryDeviceConfig)
        initTimer.start(0)


    def queryDeviceConfig(self):

        #  if we have a database object, get the devices and this workstation
        #  and look for a device that can do length measurements
        if self.db:
            #  get all of the devices on this workstation
            deviceData = devices.getDevices(self.db, self.workStation, self.schema)

            #  find the length device on this workstation
            foundLength = False
            lengthDevice = None
            for deviceName in deviceData:
                for module in deviceData[deviceName]['measurements']:
                    for measurement in deviceData[deviceName]['measurements'][module]:
                        if 'length' in measurement.lower():
                            foundLength = True
                            lengthDevice = deviceName
                            break
                    if foundLength:
                        break
                if foundLength:
                   break

            if lengthDevice:
                #  try to get the configuration parameters for this device
                #  this will fail if a required parameter is missing.
                try:
                    deviceParams = devices.getDeviceParameters(self.db, self.schema, lengthDevice,
                            deviceData[lengthDevice]['id'],
                            deviceData[lengthDevice]['interface'])
                except Exception as e:
                    messageText = ("Error querying device parameters ::: " + str(e) +
                            '. Try configuring the serial connection manually.' )
                    QMessageBox.warning(self, "WARNING", "<font size = 13>" + messageText)
                    return

                self.Serial_Port = deviceParams['port']
                self.Serial_Baud = deviceParams['baud']
                self.fbSerialPort.setText(self.Serial_Port)
                self.fbBaudRate.setText(str(self.Serial_Baud))



                self.startSerial()


    def getFishboardStatus(self):

        self.smonitor.txData('Ichthy', '$GFSN\n')
        self.smonitor.txData('Ichthy', '$GCAL\n')
        self.smonitor.txData('Ichthy', '$GOFM\n')


    @pyqtSlot()
    def setOutputUnits(self):

        if self.rbRaw.isChecked():
            mode = '0'
        elif self.rbMM.isChecked():
            mode = '1'
        elif self.rbCM.isChecked():
            mode = '2'
        self.smonitor.txData('Ichthy', '$SOFM,' + mode + '\n')


    @pyqtSlot()
    def startCal(self):
        self.smonitor.txData('Ichthy', '$SCAL\n')


    @pyqtSlot()
    def startSerial(self):

        #  force the set gps port if none is set
        if (self.Serial_Port == ''):
            ok = self.setSerailPort()
            if (not ok):
                return

        if 'udp' in self.Serial_Port.lower():
            messageText = ("UDP device connections do not support writing data. You must "
                    "connect your Ichthystick using a TCP or Serial connection to configure it.")
            QMessageBox.warning(self, "Error", "<font size = 13>" + messageText)
            return

        #  add the fishboard device and start the serial monitor
        self.smonitor.addDevice('Ichthy', self.Serial_Port, self.Serial_Baud,
                'None',0,'', txRate=2)
        try:
            self.smonitor.startMonitoring()
            self.serial_threads_finished = False
        except Exception as e:
            msg = 'Unable to open serial port. ' + e.errText
            QMessageBox.error(self, 'Serial Port Error', msg)
            return

        #  update the GUI
        self.pbConnect.setEnabled(False)
        self.pbDisconnect.setEnabled(True)
        self.pbConfigure.setEnabled(False)
        self.pbSetOutput.setEnabled(True)
        self.pbStartCal.setEnabled(True)

        self.getFishboardStatus()


    def stopSerial(self):
        #  stop the serial device
        self.smonitor.removeDevice()

        #  update the GUI
        self.pbSetOutput.setEnabled(False)
        self.pbStartCal.setEnabled(False)


    @pyqtSlot()
    def SerialStopped(self):

        self.serial_threads_finished = True

        #  update the GUI
        self.pbConnect.setEnabled(True)
        self.pbDisconnect.setEnabled(False)
        self.pbConfigure.setEnabled(True)
        self.pbSetOutput.setEnabled(False)
        self.pbStartCal.setEnabled(False)

        #  if we're in the process of closing the app, call close() again
        if self.isClosing:
            self.close()


    @pyqtSlot()
    def setSerialPort(self):

        dialog = selectWinPortDialog.selectWinPortDialog(defaultPort=self.Serial_Port,
                    defaultBaud=self.Serial_Baud, enableBaud=False, checkStatus=False,
                    parent=self)
        ok = dialog.exec()
        if (ok):
            self.Serial_Port = dialog.port
            self.Serial_Baud = dialog.baud

            #  update the application settings
            self.appSettings.setValue('Serial_Port', self.Serial_Port)
            self.appSettings.setValue('Serial_Baud', self.Serial_Baud)

            #  update the GUI
            self.fbSerialPort.setText(self.Serial_Port)
            self.fbBaudRate.setText(str(self.Serial_Baud))

        return ok


    @pyqtSlot(str, str, object)
    def SerialReceived(self, sensor, data, err):
        '''
        '''

        #  parse the command response string
        parts = data.split(',')

        if (parts[0] == "$GOFM"):
            if len(parts) > 1:
                mode = parts[1]
                if mode == '0':
                    self.rbRaw.setChecked(True)
                elif mode == '1':
                    self.rbMM.setChecked(True)
                elif mode == '2':
                    self.rbCM.setChecked(True)

        elif (parts[0] == "$GFSN"):
            if len(parts) > 1:
                self.fishboardSerial.setText(parts[1].strip())

        elif (parts[0] == "$GCAL"):
            if len(parts) > 3:

                slope = parts[1]
                offset = parts[2]
                ref_mag_loc = parts[3]
                cal_location = int(int(parts[4]) / 10)

                self.calSlope.setText(slope)
                self.calOffset.setText(offset)
                self.refMagnetLoc.setText(ref_mag_loc)
                self.sbCalLocation.setValue(cal_location)


    @pyqtSlot(str, object)
    def SerialError(self, device, error_obj):

        self.stopSerial()
        QMessageBox.warning(self, 'Serial Error', error_obj.errText)


    def closeEvent(self, event):

        #  check if we have serial threads running
        if not self.serial_threads_finished:
            self.isClosing = True
            self.smonitor.stopMonitoring()
            event.ignore()
        else:
            self.appSettings.setValue('winposition', self.pos())
            self.appSettings.setValue('winsize', self.size())
            event.accept()


    def checkWindowLocation(self, position, size, padding=[5, 25]):
        '''
        '''

        #  create a QRect that represents the app window
        appRect = QRect(position, size)

        #  check for the shift key which we use to force a move to the primary screen
        resetPosition = QGuiApplication.queryKeyboardModifiers() == Qt.KeyboardModifier.ShiftModifier
        if resetPosition:
            position = QPoint(padding[0], padding[0])

        #  get a reference to the primary system screen - If the app is off the screen, we
        #  will restore it to the primary screen
        primaryScreen = QGuiApplication.primaryScreen()

        #  assume the new and old positions are the same
        newPosition = position
        newSize = size

        #  Get the desktop geometry. We'll use availableVirtualGeometry to get the full
        #  desktop rect but note that if the monitors are different resolutions or have
        #  different scaling, some parts of this rect can still be offscreen.
        screenGeometry = primaryScreen.availableVirtualGeometry()

        #  if the app is partially or totally off screen or we're force resetting
        if resetPosition or not screenGeometry.contains(appRect):

            #  check if the upper left corner of the window is off the left side of the screen
            if position.x() < screenGeometry.x():
                newPosition.setX(screenGeometry.x() + padding[0])
            #  check if the upper right is off the right side of the screen
            if position.x() + size.width() >= screenGeometry.width():
                p = screenGeometry.width() - size.width() - padding[0]
                if p < padding[0]:
                    p = padding[0]
                newPosition.setX(p)
            #  check if the top of the window is off the top/bottom of the screen
            if position.y() < screenGeometry.y():
                newPosition.setY(screenGeometry.y() + padding[0])
            if position.y() + size.height() >= screenGeometry.height():
                p = screenGeometry.height() - size.height() - padding[1]
                if p < padding[0]:
                    p = padding[0]
                newPosition.setY(p)

            #  now make sure the lower right (resize handle) is on the screen
            if (newPosition.x() + newSize.width()) > screenGeometry.width():
                newSize.setWidth(screenGeometry.width() - newPosition.x() - padding[0])
            if (newPosition.y() + newSize.height()) > screenGeometry.height():
                newSize.setHeight(screenGeometry.height() - newPosition.y() - padding[1])

        return [newPosition, newSize]


if __name__ == "__main__":

    import sys

    app = QApplication(sys.argv)
    form = Ichthysetupdlg()
    form.show()
    app.exec()
