from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtSql
from ui.xga import ui_DeviceSetupDlg
import keypad
import serial
import listseldialog

class DeviceSetupDlg(QDialog, ui_DeviceSetupDlg.Ui_deviceSetupDlg):

    def __init__(self, parent=None):
        super(DeviceSetupDlg, self).__init__(parent)
        self.setupUi(self)
        self.workStation=parent.workStation
        self.settings=parent.settings
        self.spBoxes=[]
        self.brBoxes=[]
        self.sfBoxes=[]
        self.ptBoxes=[]
        self.dnLabels=[]
        self.piLineEdits=[]
        self.peLineEdits=[]

        for i in range(7):

            exec('self.spBoxes.append(self.sp_'+str(i+1)+')')
            exec('self.connect(self.sp_'+str(i+1)+',SIGNAL("activated(int)"), self.checkPortAvailability)')
            exec('self.brBoxes.append(self.br_'+str(i+1)+')')
            exec('self.sfBoxes.append(self.sf_'+str(i+1)+')')
            exec('self.ptBoxes.append(self.pt_'+str(i+1)+')')
            exec('self.dnLabels.append(self.dn_'+str(i+1)+')')
            exec('self.piLineEdits.append(self.pi_'+str(i+1)+')')
            exec('self.peLineEdits.append(self.pe_'+str(i+1)+')')

                                                                                                

        #  set up signals
        self.connect(self.addBtn, SIGNAL("clicked()"), self.addDevice)
        self.connect(self.removeBtn, SIGNAL("clicked()"), self.removeDevice)
        self.connect(self.doneBtn, SIGNAL("clicked()"), self.doneClicked)
        
        
        # populate work station box
        query = QtSql.QSqlQuery("SELECT hostname FROM " + self.schema + ".workstation WHERE workstation_id="+self.workStation)
        self.ws.setText(self.workStation)
        query.first()
        self.hn.setText(query.value(0).toString())
        
        # get valid serial ports
        #self.validPorts=serial.tools.list_ports.comports()
        self.populateBoxes()
        self.getDevices()
        
        
    def populateBoxes(self):
        validPorts=QStringList()
        for i in range(10):#port in self.validPorts:
            validPorts<<str(i)
        validBauds=QStringList()
        validBauds<<'1200'<<'4800'<<'9600'<<'19200'<<'57600'
        validParseTypes=QStringList()
        validParseTypes<<'None'<<'regex'
        soundsDir=QDir(self.settings[QString('SoundsDir')] )
        soundFiles=soundsDir.entryList()
        validSFs=QStringList()
        for file in soundFiles:
            if file.endsWith('.wav'):
                file.remove('.wav')
                validSFs<<file
        

        for i in range(7):
            self.spBoxes[i].clear()
            self.spBoxes[i].addItems(validPorts)
            self.brBoxes[i].clear()
            self.brBoxes[i].addItems(validBauds)
            self.sfBoxes[i].clear()
            self.sfBoxes[i].addItems(validSFs)
            self.ptBoxes[i].clear()
            self.ptBoxes[i].addItems(validParseTypes)
            self.piLineEdits[i].setText('')
            self.peLineEdits[i].setText('')
            
            self.spBoxes[i].hide()
            self.brBoxes[i].hide()
            self.sfBoxes[i].hide()
            self.ptBoxes[i].hide()
            self.dnLabels[i].hide()
            self.piLineEdits[i].hide()
            self.piLineEdits[i].setEnabled(False)
            self.peLineEdits[i].hide()
            self.peLineEdits[i].setEnabled(False)

    def getDevices(self):

        # get devices
        query = QtSql.QSqlQuery("  SELECT DEVICE.DEVICE_ID, DEVICE.DEVICE_NAME FROM " + self.schema + ".DEVICE, MEASUREMENT_SETUP  "+ 
            "WHERE MEASUREMENT_SETUP.DEVICE_ID = DEVICE.DEVICE_ID  and "+ 
            " MEASUREMENT_SETUP.WORKSTATION_ID = "+self.workStation+"  AND MEASUREMENT_SETUP.DEVICE_INTERFACE='Serial'"+
            "GROUP BY DEVICE.DEVICE_ID, DEVICE.DEVICE_NAME")
         # top level
        self.devices=[]
        i=0
        while query.next():
            self.devices.append(query.value(0).toString())
            self.spBoxes[i].show()
            self.brBoxes[i].show()
            self.sfBoxes[i].show()
            self.ptBoxes[i].show()
            self.dnLabels[i].show()
            self.piLineEdits[i].show()
            self.peLineEdits[i].show()
            self.dnLabels[i].setText(query.value(1).toString())
            parsetype='None'
            query1=QtSql.QSqlQuery("SELECT device_parameter, parameter_value FROM " + self.schema + ".device_configuration WHERE device_id= "+query.value(0).toString())
            while query1.next():
                
                if query1.value(0).toString()=='SerialPort':
                    ind=self.spBoxes[i].findText(query1.value(1).toString(), Qt.MatchExactly)
                    self.spBoxes[i].setCurrentIndex(ind)
                elif query1.value(0).toString()=='BaudRate':
                    ind=self.brBoxes[i].findText(query1.value(1).toString(), Qt.MatchExactly)
                    self.brBoxes[i].setCurrentIndex(ind)
                elif query1.value(0).toString()=='SoundFile':
                    ind=self.sfBoxes[i].findText(query1.value(1).toString(), Qt.MatchExactly)
                    self.sfBoxes[i].setCurrentIndex(ind)
                elif query1.value(0).toString()=='ParseType':
                    ind=self.ptBoxes[i].findText(query1.value(1).toString(), Qt.MatchExactly)
                    self.ptBoxes[i].setCurrentIndex(ind)
                    parsetype=query1.value(1).toString()
                    
                elif query1.value(0).toString()=='ParseIndex':
                    self.piLineEdits[i].setEnabled(True)
                    self.piLineEdits[i].setText(query1.value(1).toString())
                elif query1.value(0).toString()=='ParseExpression':
                    self.peLineEdits[i].setEnabled(True)
                    self.peLineEdits[i].setText(query1.value(1).toString())
            if not parsetype=='None':
                self.piLineEdits[i].setEnabled(True)
                self.peLineEdits[i].setEnabled(True)
            i+=1
            
    def checkPortAvailability(self):
        ports=QStringList()
        for i in range (7):
            if not self.spBoxes[i].isHidden() and not self.spBoxes[i]==self.sender():
                ports<<self.spBoxes[i].currentText()
        if self.sender().currentText() in ports:
            QMessageBox.critical(self, "ERROR", "<font size = 12> This port is already taken, please choose another port.")

    def addDevice(self):
        """
          add a device to workstation
        """

        
        availableDevices=[]
        availableDeviceIds=[]
        query = QtSql.QSqlQuery("  SELECT DEVICE.DEVICE_ID, DEVICE.DEVICE_NAME FROM " + self.schema + ".DEVICE, MEASUREMENT_SETUP  "+ 
            "WHERE MEASUREMENT_SETUP.DEVICE_ID = DEVICE.DEVICE_ID  and "+ 
            "  MEASUREMENT_SETUP.DEVICE_INTERFACE='Serial'"+
            "GROUP BY DEVICE.DEVICE_ID, DEVICE.DEVICE_NAME")
        while query.next(): 
            availableDevices.append(query.value(1).toString())
            availableDeviceIds.append(query.value(0).toString())
#        availableDevices.append('New Device')
#        availableDeviceIds.append('99')
        self.listDialog = listseldialog.ListSelDialog(availableDevices, self)
        self.listDialog.label.setText('Select a device')
        if not self.listDialog.exec_():
            return
#        if self.listDialog.itemList.currentItem().text()=='New Device':
#            
#            keyDialog = keypad.KeyPad('',  self)
#            keypad.infoLabel.setText('Type in New Device Name ...')
#            if not keyDialog.exec_():
#                return
#            newDevice=keyDialog.dispEdit.toPlainText()
            
            
        ind=availableDevices.index(self.listDialog.itemList.currentItem().text())
        
        
        availableMeasurements=[]
        query = QtSql.QSqlQuery("  SELECT measurement_types.measurement_type FROM " + self.schema + ".measurement_types  "+ 
            "WHERE measurement_types.description = 'Serial' ORDER BY measurement_types.measurement_type")
        while query.next(): 
            availableMeasurements.append(query.value(0).toString())
        self.listDialog = listseldialog.ListSelDialog(availableMeasurements, self)
        self.listDialog.label.setText('What will this device measure?')
        if not self.listDialog.exec_():
            return
        query = QtSql.QSqlQuery("INSERT INTO " + self.schema + ".measurement_setup (workstation_id,  measurement_type,  device_id,  device_interface, gui_module) VALUES("+
                                            self.workStation+", '"+self.listDialog.itemList.currentItem().text()+"', "+availableDeviceIds[ind]+", 'Serial','Specimen')")
        
        self.populateBoxes()
        self.getDevices()
        
    def removeDevice(self):
        """
          remove device from workstation
        """
        currentDevices=[]
        currentDeviceIds=[]
        query = QtSql.QSqlQuery("  SELECT DEVICE.DEVICE_ID, DEVICE.DEVICE_NAME FROM " + self.schema + ".DEVICE, " + self.schema + ".MEASUREMENT_SETUP  "+ 
            "WHERE MEASUREMENT_SETUP.DEVICE_ID = DEVICE.DEVICE_ID  and MEASUREMENT_SETUP.WORKSTATION_ID = "+self.workStation+" AND "+ 
            "  MEASUREMENT_SETUP.DEVICE_INTERFACE='Serial'"+
            "GROUP BY DEVICE.DEVICE_ID, DEVICE.DEVICE_NAME")
        while query.next(): 
            currentDevices.append(query.value(1).toString())
            currentDeviceIds.append(query.value(0).toString())
        self.listDialog = listseldialog.ListSelDialog(currentDevices, self)
        self.listDialog.label.setText('Select a device to remove')
        if not self.listDialog.exec_():
            return
        ind=currentDevices.index(self.listDialog.itemList.currentItem().text())
        reply = QMessageBox.question(self, 'WARNING!',"Are you sure you want to remove the "+currentDevices[ind]+" device?"+
            "Do you want to continue?", QMessageBox.Yes, QMessageBox.No)
        if reply==QMessageBox.No:
            return
        
        query = QtSql.QSqlQuery("DELETE FROM " + self.schema + ".measurement_setup WHERE measurement_setup.workstation_id="+self.workStation+" AND measurement_setup.device_id = "+currentDeviceIds[ind])
        self.populateBoxes()
        self.getDevices()
    
    def writeData(self):
            for i in range(7):
                if not self.spBoxes[i].isHidden():
                    query = QtSql.QSqlQuery("UPDATE " + self.schema + ".device_configuration SET parameter_value='"+self.spBoxes[i].currentText()+
                    "' WHERE device_parameter = 'SerialPort' AND device_id="+self.devices[i]+")")
                    query = QtSql.QSqlQuery("UPDATE " + self.schema + ".device_configuration SET parameter_value='"+self.brBoxes[i].currentText()+
                    "' WHERE device_parameter = 'BaudRate' AND device_id="+self.devices[i]+")")
                    query = QtSql.QSqlQuery("UPDATE " + self.schema + ".device_configuration SET parameter_value='"+self.sfBoxes[i].currentText()+
                    "' WHERE device_parameter = 'SoundFile' AND device_id="+self.devices[i]+")")
                    query = QtSql.QSqlQuery("UPDATE " + self.schema + ".device_configuration SET parameter_value='"+self.ptBoxes[i].currentText()+
                    "' WHERE device_parameter = 'ParseType' AND device_id="+self.devices[i]+")")
                    if not self.piLineEdits[i].isEnabled():
                        query = QtSql.QSqlQuery("UPDATE " + self.schema + ".device_configuration SET parameter_value='"+self.piLineEdits[i].currentText()+
                        "' WHERE device_parameter = 'ParseIndex' AND device_id="+self.devices[i]+")")
                    if not self.peLineEdits[i].isEnabled():
                        query = QtSql.QSqlQuery("UPDATE " + self.schema + ".device_configuration SET parameter_value='"+self.peLineEdits[i].currentText()+
                        "' WHERE device_parameter = 'ParseExpression' AND device_id="+self.devices[i]+")")
                        
    
                    






                elif query1.value(0).toString()=='BaudRate':
                    ind=self.brBoxes[i].findText(query1.value(1).toString(), Qt.MatchExactly)
                    self.brBoxes[i].setCurrentIndex(ind)
                elif query1.value(0).toString()=='ParseType':
                    ind=self.ptBoxes[i].findText(query1.value(1).toString(), Qt.MatchExactly)
                    self.ptBoxes[i].setCurrentIndex(ind)
                elif query1.value(0).toString()=='ParseIndex':
                    self.piLineEdits[i].setText(query1.value(1).toString())
                elif query1.value(0).toString()=='ParseExpression':
                    self.peLineEdits[i].setText(query1.value(1).toString())

    def doneClicked(self):
        
        self.close()


    def closeEvent(self, event=None):
#        self.writeData()
        event.accept()


