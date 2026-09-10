from ui import ui_EditDevicesDlg
from .baseEditDlg import BaseEditDlg

class editDevicesDlg(BaseEditDlg, ui_EditDevicesDlg.Ui_EditDevicesDlg):

    def __init__(self, db, parent=None):
        super().__init__(db, parent)
        self.setupUi(self)

        # Wire the buttons
        self.setup_base()

        # Populate dropdowns
        self.deviceInterfaces = []

        sql = f"SELECT device_interface from {self.schema}.device_interfaces"
        query = self.db.dbQuery(sql)
        for interfaces, in query:
            self.deviceInterfaces.append(interfaces)
        self.deviceInterfaceCB.addItems(self.deviceInterfaces)

    def setUp(self, device):
        if device:
            self.idLabel.setText(device[0])
            self.deviceNameLabel.setText(device[1])
            self.modelLabel.setText(device[2])
            self.serialNumLabel.setText(device[3])
            self.description.setText(device[4])
            self.isActive.setChecked(device[5] == 'Yes')
            self.deviceInterfaceCB.setCurrentIndex(self.deviceInterfaces.index(device[6]))
        else:
            # Get new ID logic
            sql = f'SELECT MAX(device_id) from {self.schema}.devices'
            query = self.db.dbQuery(sql)
            max_id = query.first()[0]
            # Handle case where table is empty
            newId = (int(max_id) + 1) if max_id is not None else 1

            self.idLabel.setText(str(newId))
            self.deviceNameLabel.setText('')
            self.modelLabel.setText('')
            self.serialNumLabel.setText('')
            self.description.setText('')
            self.isActive.setChecked(False)
            self.deviceInterfaceCB.setCurrentIndex(-1)
        

    def validate_fields(self):
        return self.validate_required_fields([
            ("deviceName", self.deviceNameLabel.text()),
            ("deviceInterface", self.deviceInterfaceCB.currentText())
        ])

    def getData(self):
        # This method can be used if you want to gather all data at once before saving
        print('stub')

    # Based on selected default config, initalize values in device configuration
    def initConfig(self):
        defaultConfig = self.defaultConfigCB.currentText()
        if defaultConfig == 'Barcode Scanner':
            config = {
                'BaudRate': 9600,
                'ParseExpression': '(\s+[0-9]+.[0-9]+)',
                'ParseIndex': 0,
                'ParseType': None,
                'SerialPort': 'COM6',
                'SoundFile': 'Ding'
            }
            self.initDeviceConfigTemplate(config)
        elif defaultConfig == 'Small Scale':
            config = {
                'BaudRate': 4800,
                'ParseExpression': '([0-9]+.[0-9]+)(?=.kg)',
                'ParseIndex': 0,
                'ParseType': 'regex',
                'SerialPort': 'COM4',
                'SoundFile': 'smallScaleSound'
            }
            self.initDeviceConfigTemplate(config)
        elif defaultConfig == 'Large Scale':
            config = {
                'BaudRate': 4800,
                'ParseExpression': '([0-9]+.[0-9]+)(?=.g)',
                'ParseIndex': 0,
                'ParseType': 'regex',
                'SerialPort': 'COM5',
                'SoundFile': 'largeScaleSound'
            }
            self.initDeviceConfigTemplate(config)
        elif defaultConfig == 'Barcode Scanner':
            config = {
                'BaudRate': 9600,
                'ParseExpression': '',
                'ParseIndex': 0,
                'ParseType': None,
                'SerialPort': 'COM13',
                'SoundFile': 'Blaster'
            }
            self.initDeviceConfigTemplate(config)
        elif defaultConfig == 'Label Printer':
            config = {
                'NetworkdAddress': '192.168.0.125',
                'NetworkPort': 9100,
            }
            self.initDeviceConfigTemplate(config)

    def perform_save(self):
        sql = (f"INSERT INTO {self.schema}.devices (device_id, device_name, model, "
               "serial_number, description, active, device_interface) "
               f"VALUES ({self.idLabel.text()},'{self.deviceNameLabel.text()}', " 
               f"'{self.modelLabel.text()}', '{self.serialNumLabel.text()}', "
               f"'{self.description.toPlainText()}' , {1 if self.isActive.isChecked() else 0}, "
               f"'{self.deviceInterfaceCB.currentText()}')")
        self.db.dbExec(sql)
        self.initConfig()
    
    def update(self):
        sql = (f"UPDATE {self.schema}.devices SET device_name='{self.deviceNameLabel.text()}', "
                f"model='{self.modelLabel.text()}', serial_number='{self.serialNumLabel.text()}', "
                f"description='{self.description.toPlainText()}', active={1 if self.isActive.isChecked() else 0}, "
                f"device_interface='{self.deviceInterfaceCB.currentText()}' WHERE device_id={self.idLabel.text()}")
        self.db.dbExec(sql)
        self.initConfig()
    
    def initDeviceConfigTemplate(self, config):
        for key, val in config.items():
            sql = (f"INSERT INTO {self.schema}.device_configuration (device_id, device_parameter, parameter_value) "
                f"VALUES ({self.idLabel.text()}, '{key}', '{val}') "
                f"ON CONFLICT (device_id, device_parameter) "
                f"DO UPDATE SET parameter_value=EXCLUDED.parameter_value")
            self.db.dbExec(sql)