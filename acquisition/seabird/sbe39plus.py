"""
sbe39plus is a class that provides an interface for interacting with the Sea-Bird SBE 39plus
bathythermograph using its native XML command interface.
"""

import datetime
import struct
import re
from PyQt6.QtCore import *
from acquisition.SensorMonitor import SensorMonitor


class sbe39plus(QObject):
    """A class for downloading data from and setting parameters on the Sea Bird SBE 39plus
    bathythermograph operating in native mode.
    """

    # Define the sbe39plus class's signals
    SBETimeout = pyqtSignal(str)
    SBEData = pyqtSignal(str, str)
    SBEConnected = pyqtSignal(str)
    SBEDownloadData = pyqtSignal(str, list)
    SBEProgress = pyqtSignal(str, float)
    SBEAbort = pyqtSignal(str)
    SBEStatus = pyqtSignal(str, dict)
    SBECalibration = pyqtSignal(str, dict)
    SBEDownloadComplete = pyqtSignal(str, int, int)

    def __init__(self, serialPort, deviceName='SBE39Plus', baud=9600, serialMonitor=None, parent=None):
        QObject.__init__(self, parent)

        # Internal state variables
        self.deviceName = deviceName
        self.rxBuffer = []
        self.txBuffer = []
        self.status = {}
        self.calibration = {}
        self.connected = False
        self.lowBattery = False
        self.sbeIsAsleep = False
        self.binaryUploadEnable = False
        self.isAborting = False
        self.justStarted = False
        self.nTotalRecords = 0
        self.CTS = True
        self.nRecDL = 0
        self.maxConAttempts = 200
        self.extraSleepy = 0
        self.lastCommand = ''

        # Use provided SerialMonitor or instantiate a new one
        if serialMonitor is None:
            self.serMonitor = SensorMonitor.SensorMonitor()
        else:
            self.serMonitor = serialMonitor

        self.serMonitor.SensorDataReceived.connect(self.rxData)

        # Register device with SensorMonitor using default prompt
        self.serMonitor.addDevice(deviceName, serialPort, baud, 'None', '', 0,
                                  cmdPrompt='S>', pollRate=1000)

        # Transmit timer
        self.txTimer = QTimer(self)
        self.txTimer.setSingleShot(False)
        self.txTimer.setInterval(100)
        self.txTimer.timeout.connect(self.pollTxBuffer)

        # Response timeout timer
        self.rxTimeoutTimer = QTimer(self)
        self.rxTimeoutTimer.setSingleShot(True)
        self.rxTimeoutTimer.setInterval(3000)
        self.rxTimeoutTimer.timeout.connect(self.rxTimeout)


    def setConnectionParams(self, serialPort, baud):
        """setConnectionParams updates the serial parameters when disconnected."""
        if not self.connected:
            self.serMonitor.removeDevice(self.deviceName)
            self.serMonitor.addDevice(self.deviceName, serialPort, baud, 'None', '', 0,
                                      cmdPrompt='S>', pollRate=1000)


    def connect(self):
        """Connects to the serial port and wakes up the SBE 39plus."""
        if not self.connected:
            try:
                self.serMonitor.startMonitoring(devices=[self.deviceName])
                self.connected = True
                self.isConnecting = True
                self.sbeIsAsleep = True
                self.attempts = 0

                # Queue initial wake command
                self.txCommand([''])
                self.txTimer.start()
            except Exception as e:
                raise e


    def getStatus(self):
        """Requests status using native SBE 39plus 'GetSD' command."""
        if self.connected:
            self.txCommand(['GetSD'])


    def setTxRealTime(self, state):
        """Enables or disables real-time output using native OutputRealTime= command."""
        if self.connected:
            state_str = 'Y' if state else 'N'
            # Send OutputRealTime=Y
            self.txCommand([f'OutputRealTime={state_str}'])


    def setSamplingInterval(self, num):
        """Sets the sampling interval in seconds using SampleInterval= command."""
        if self.connected:
            num = int(num)
            num = max(0, min(num, 32767))
            self.txCommand([f'SampleInterval={num}'])


    def setBaud(self, baud):
        """Sets serial baud rate on the device."""
        if self.connected:
            validRates = [1200, 2400, 4800, 9600, 19200, 38400]
            if baud in validRates:
                self.txCommand([f'BAUD={baud}'])
            else:
                raise SBEError(f'Invalid baud rate: {baud}.')


    def setSampleNumber(self, num):
        """Resets the internal sample storage index."""
        if self.connected:
            self.stop()
            num_str = str(int(num))
            self.txCommand([f'SAMPLENUM={num_str}'])
            self.lastCommand = f'SAMPLENUM={num_str}'


    def sleep(self):
        """Puts device into low-power sleep mode."""
        if self.connected:
            self.txCommand(['QS'])


    def getCalParms(self):
        """Requests calibration coefficients using native GetCC command."""
        if self.connected:
            self.txCommand(['GetCC'])


    def disconnect(self):
        """Closes serial connection and resets state."""
        if self.connected:
            self.serMonitor.stopMonitoring(devices=[self.deviceName])
            self.txTimer.stop()
            self.rxTimeoutTimer.stop()

            self.connected = False
            self.calibration = {}
            self.status = {}
            self.rxBuffer = []
            self.txBuffer = []


    def stop(self):
        """Stops active logging session."""
        if self.connected:
            self.txCommand(['STOP'])


    def startNow(self):
        """Starts logging immediately."""
        if self.connected:
            self.txCommand(['STARTNOW'])


    def startLater(self):
        """Starts logging at configured start date/time."""
        if self.connected:
            self.txCommand(['STARTLATER'])


    def setStartDateTime(self, time=None, delay=None, localTime=False):
        """Sets delayed start date/time in native YYYYMMDDHHMMSS format."""
        if self.connected:
            if time is None:
                if localTime:
                    time = datetime.datetime.now()
                else:
                    time = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            if delay:
                time = time + datetime.timedelta(minutes=delay)

            self.txCommand(self.formatTime(time, start=True))


    def download(self, start=1, stop=None, mode='ASCII'):
        """Downloads samples using native GetSamples:start,stop command."""
        if self.connected:
            if stop:
                stop = int(stop)
            else:
                stop = int(self.status.get('sample number', 0))
                if stop > 5:
                    stop = stop - 4

            self.dlProgress = 0
            self.nRecDL = 0
            self.nTotalRecords = max((stop - int(start)) + 1, 1)

            start_str = str(int(start))
            stop_str = str(int(stop))

            self.txCommand([f'GetSamples:{start_str},{stop_str}'])


    def abort(self):
        """Sends control+C interrupt signal."""
        self.isAborting = True
        self.serMonitor.txData(self.deviceName, '\x03\r')


    def setRTC(self, time=None, localTime=False):
        """Sets internal real-time clock."""
        if self.connected:
            self.stop()
            if time is None:
                if localTime:
                    time = datetime.datetime.now()
                else:
                    time = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

            self.txCommand(self.formatTime(time))


    def txCommand(self, cmdList):
        """Enqueues command list to transmit buffer."""
        for cmd in cmdList:
            self.txBuffer.append(cmd + '\r')


    def pollTxBuffer(self):
        """Processes transmit queue and wake-up attempts."""
        if self.connected and len(self.txBuffer) > 0:
            if self.sbeIsAsleep:
                if self.attempts < self.maxConAttempts:
                    # Send GetSD to wake SBE 39plus cleanly
                    self.serMonitor.txData(self.deviceName, 'GetSD\r')
                    self.attempts += 1
                else:
                    self.disconnect()
                    self.SBETimeout.emit(self.deviceName)
            else:
                if self.CTS:
                    cmd = self.txBuffer.pop(0)
                    self.serMonitor.txData(self.deviceName, cmd)
                    self.lastCommand = cmd

                    if cmd == 'QS':
                        self.sbeIsAsleep = True
                        self.extraSleepy = 0
                        self.attempts = 0

                    self.CTS = False
                    self.rxTimeoutTimer.start()

    def rxData(self, name, val, err):
        """Processes incoming data buffer from SensorMonitor."""
        if ('stop' in self.lastCommand.lower()) and ('inactive command' in val.lower()):
            return

        if (val == 'S>') and self.justStarted:
            self.justStarted = False
            val = ''

        # Wake up check accepting S> or SBE 39plus XML tags
        if self.sbeIsAsleep and (
                val == 'S>' or '<ExecCommand' in val or '<Executed' in val or val.strip() == '<Executed/>'):
            self.sbeIsAsleep = False
            self.extraSleepy = 0
            if self.isConnecting:
                self.SBEConnected.emit(self.deviceName)
                self.isConnecting = False

        # --- REAL-TIME DATA PACKET PARSING ---
        # SBE 39plus streams <DataPacket> or CSV formatted lines every 3 seconds
        if '<datapacket>' in val.lower() or '<sample>' in val.lower():
            # Extract values inside XML tags like <T1>12.3456</T1> or <P1>10.123</P1>
            temp_match = re.search(r'<t1>\s*([\d\.-]+)\s*</t1>', val, re.IGNORECASE)
            press_match = re.search(r'<p1>\s*([\d\.-]+)\s*</p1>', val, re.IGNORECASE)
            time_match = re.search(r'<date>\s*([^<]+)\s*</date>.*<time>\s*([^<]+)\s*</time>', val,
                                   re.IGNORECASE | re.DOTALL)

            if temp_match:
                temp_str = temp_match.group(1)
                press_str = press_match.group(1) if press_match else "0.0"
                dt_str = f"{time_match.group(1)} {time_match.group(2)}" if time_match else ""

                formatted_rt = f"Real-Time Sample -> Temp: {temp_str} C, Press: {press_str} dbar {dt_str}"
                self.SBEData.emit(self.deviceName, formatted_rt)
            else:
                # Fallback: Strip XML tags and display clean line
                clean_text = re.sub(r'<[^>]+>', ' ', val).strip()
                if clean_text:
                    self.SBEData.emit(self.deviceName, clean_text)
            return

        # Emit raw string for non-datapacket lines (Status responses, commands, etc.)
        if val and not self.sbeIsAsleep:
            self.SBEData.emit(self.deviceName, val)

        if not self.CTS:
            self.rxTimeoutTimer.start()

        cmd = self.lastCommand.lower().strip()

        # Buffer response XML metadata
        if (cmd.startswith('getsd') or cmd.startswith('gethd') or cmd.startswith('getcc') or
                cmd.startswith('ds') or cmd.startswith('dc')):
            self.rxBuffer.append(val)

        # Parse sample download streams (GetSamples)
        elif cmd.startswith('getsamples') or cmd.startswith('dd'):
            if val != 'S>' and not val.startswith('</'):
                clean_val = re.sub(r'<[^>]+>', '', val).strip()
                if clean_val:
                    parts = [p.strip() for p in clean_val.split(',')]
                    if len(parts) >= 3:
                        try:
                            temp = float(parts[0])
                            if len(parts) == 4:
                                pressure = float(parts[1])
                                time_str = f"{parts[2]} {parts[3]}"
                            else:
                                pressure = 0.0
                                time_str = parts[1] if len(parts) == 2 else f"{parts[1]} {parts[2]}"

                            try:
                                time = datetime.datetime.strptime(time_str, '%d %b %Y %H:%M:%S')
                            except ValueError:
                                time = datetime.datetime.strptime(time_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')

                            self.nRecDL += 1.0
                            self.SBEDownloadData.emit(self.deviceName, [time, temp, pressure])

                            if self.nTotalRecords > 0:
                                dlProgress = (self.nRecDL / self.nTotalRecords) * 100.0
                                if dlProgress != self.dlProgress:
                                    self.dlProgress = dlProgress
                                    self.SBEProgress.emit(self.deviceName, self.dlProgress)

                        except Exception:
                            pass

        # Detect command execution completion
        if val == 'S>' or '</StatusData>' in val or '</CalibrationData>' in val or '</HardwareData>' in val or '<Executed/>' in val:
            if self.isAborting:
                self.isAborting = False
                self.SBEAbort.emit(self.deviceName)

            elif cmd.startswith('getsd') or cmd.startswith('gethd') or cmd.startswith('ds'):
                self.processStatus()
                self.SBEStatus.emit(self.deviceName, self.status)

            elif cmd.startswith('getcc') or cmd.startswith('dc'):
                self.processCalParms()
                self.SBECalibration.emit(self.deviceName, self.calibration)

            elif cmd.startswith('getsamples') or cmd.startswith('dd'):
                nDropped = max(0, int(self.nTotalRecords - self.nRecDL))
                self.rxTimeoutTimer.stop()
                self.SBEDownloadComplete.emit(self.deviceName, int(self.nRecDL), int(nDropped))

            self.lastCommand = ''
            self.CTS = True
            self.rxTimeoutTimer.stop()

        elif ('startnow' in val.lower()) or ('start now' in val.lower()):
            self.sbeIsAsleep = True
            self.extraSleepy = 0
            self.attempts = 0
            self.CTS = True
            self.rxTimeoutTimer.stop()
            self.justStarted = True

        elif '<!--Repeat command' in val:
            self.serMonitor.txData(self.deviceName, self.lastCommand + '\r')

        elif 'timeout' in val.lower():
            self.sbeIsAsleep = True
            self.attempts = 0


    def processCalParms(self):
        """Parses calibration values from GetCC XML or text response."""
        self.calibration = {}
        full_text = "\n".join(self.rxBuffer)

        if '<CalibrationData' in full_text:
            matches = re.findall(r'<([A-Za-z0-9_]+)>\s*([^<]+)\s*</\1>', full_text)
            for key, val in matches:
                try:
                    self.calibration[key] = float(val)
                except ValueError:
                    self.calibration[key] = val
            self.rxBuffer = []
            return

        for line in self.rxBuffer:
            if '=' in line:
                parts = line.split('=')
                key = parts[0].strip()
                val_str = parts[1].strip()
                try:
                    self.calibration[key] = float(val_str)
                except ValueError:
                    self.calibration[key] = val_str

        self.rxBuffer = []

    import re

    def processStatus(self):
        """processStatus extracts the status information from DS, GetSD, or GetHD."""
        self.status = {}
        full_text = "\n".join(self.rxBuffer)

        # --- 1. XML Parsing (Native SBE 39plus) ---
        if '<StatusData' in full_text or '<HardwareData' in full_text or '<SerialNumber>' in full_text:
            # Match <SerialNumber>12345</SerialNumber> OR SerialNumber="12345"
            sn_match = re.search(r'<SerialNumber>\s*([0-9A-Za-z]+)\s*</SerialNumber>', full_text, re.IGNORECASE) or \
                       re.search(r'SerialNumber=[\'"]([0-9A-Za-z]+)[\'"]', full_text, re.IGNORECASE)

            if sn_match:
                self.status['serial number'] = sn_match.group(1).strip()

            # Extract sample count / sample number
            sample_match = re.search(r'<(?:Samples|SampleNumber)>\s*(\d+)\s*</', full_text, re.IGNORECASE)
            if sample_match:
                self.status['sample number'] = sample_match.group(1).strip()

            self.rxBuffer = []
            return

        # --- 2. Robust Text Parsing (Legacy SBE 39) ---
        for line in self.rxBuffer:
            line_lower = line.lower()

            # Handles: "SERIAL NO. 1234", "SERIAL NO 1234", "sn: 1234", "sn=1234"
            if 'serial' in line_lower or 'sn' in line_lower:
                sn_match = re.search(r'(?:serial\s*no\.?|sn[:=]?)\s*([0-9]+)', line, re.IGNORECASE)
                if sn_match:
                    self.status['serial number'] = sn_match.group(1).strip()

            elif 'samplenumber' in line_lower or 'sample number' in line_lower:
                if '=' in line:
                    self.status['sample number'] = line.split('=')[1].split(',')[0].strip()

        self.rxBuffer = []


    def rxTimeout(self):
        """Handles connection response timeout."""
        self.disconnect()
        self.SBETimeout.emit(self.deviceName)


    def __del__(self):
        if self.connected:
            self.serMonitor.stopMonitoring(devices=[self.deviceName])

    def formatTime(self, time, start=False):
        """Formats datetime to native SBE 39plus format (mmddyyyyhhmmss).
        Example output: DateTime=09052026160856
        """
        # Format: MMDDYYYYHHMMSS (2-digit month, 2-digit day, 4-digit year, 24h time)
        time_str = time.strftime("%m%d%Y%H%M%S")

        if start:
            return [f'StartDateTime={time_str}']
        return [f'DateTime={time_str}']


class SBEError(Exception):
    def __init__(self, msg, parent=None):
        self.errText = msg
        self.parent = parent

    def __str__(self):
        return repr(self.errText)