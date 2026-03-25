from ui import ui_DevicesDlg
import setup.editDlgs.editDevicesDlg as editDevicesDlg
from PyQt6.QtWidgets import QTableWidgetItem
# Import the base class created above
from .baseTableDlg import BaseTableDlg 
import setup.table.devicesConfigDlg as devicesConfigDlg

class devicesDlg(BaseTableDlg, ui_DevicesDlg.Ui_DevicesDlg):

    def __init__(self, db, parent=None):
        # Initialize Base Logic
        super().__init__(db, parent)
        # Initialize UI (from the generated file)
        self.setupUi(self)
        self.workstationId = 0

        # Create the specific child dialog
        self.dialog = editDevicesDlg.editDevicesDlg(self.db, parent=self)
        self.dialog.changed.connect(self.populate_table)

        # create device config dialog
        self.devicesConfigDlg = devicesConfigDlg.devicesDlg(self.db, parent=self)

        # WIRE IT UP: Pass the specific table and dialog to the Base
        self.setup_base(self.devicesTable, self.dialog)
        self.deviceConfigBtn.clicked.connect(self.openDeviceConfig)

        # Hookup duplicate button
        self.duplicateBtn.clicked.connect(self.duplicate)

    # --- Implement the Hooks ---
    def setCurrWorkstation(self, id):
        self.workstationId = id
        self.dialog.setCurrWorkstation(id)

    def get_select_sql(self):
        return (f"SELECT device_id, device_name, model, serial_number, description, active, device_interface FROM " 
            f"{self.schema}.devices ORDER BY device_id")

    def fill_row(self, row_idx, row_data):
        # Unpack the data returned by the query
        id, name, model, serialNum, description, active, interface = row_data
        
        self.table.setItem(row_idx, 0, QTableWidgetItem(str(id)))
        self.table.setItem(row_idx, 1, QTableWidgetItem(name))
        self.table.setItem(row_idx, 2, QTableWidgetItem(model))
        self.table.setItem(row_idx, 3, QTableWidgetItem(serialNum))
        self.table.setItem(row_idx, 4, QTableWidgetItem(description))
        self.table.setItem(row_idx, 5, QTableWidgetItem('Yes' if str(active) == '1' else 'No'))
        self.table.setItem(row_idx, 6, QTableWidgetItem(interface))

    def get_data_for_edit(self, row_idx):
        # Workstation dialog only sends the ID (col 0) to the edit window
        return [
            self.table.item(row_idx, 0).text(),
            self.table.item(row_idx, 1).text(),
            self.table.item(row_idx, 2).text(),
            self.table.item(row_idx, 3).text(),
            self.table.item(row_idx, 4).text(),
            self.table.item(row_idx, 5).text(),
            self.table.item(row_idx, 6).text()
        ]

    def on_selection_change(self, has_selection):
        # This automatically runs when selection changes in the Base class
        device_id = self.table.item(self.currentRow, 0).text()
        self.devicesConfigDlg.setDeviceId(device_id)
        self.deviceConfigBtn.setEnabled(has_selection)
        self.duplicateBtn.setEnabled(has_selection)
    
    def openDeviceConfig(self):
        self.devicesConfigDlg.populate_table()
        self.devicesConfigDlg.exec()

    def duplicate(self):
        currDeviceId = self.table.item(self.currentRow, 0).text()

        try:
            self.db.startTransaction()

            # Get new ID logic
            sql = f'SELECT MAX(device_id) FROM {self.schema}.devices'
            query = self.db.dbQuery(sql)
            max_id = query.first()[0]
            # Handle case where table is empty
            newId = (int(max_id) + 1) if max_id is not None else 1

            # Query devices table and duplicate
            sql = (f"SELECT device_name, model, serial_number, description, active, device_interface "
                f"FROM {self.schema}.devices WHERE device_id={currDeviceId}")
            query = self.db.dbQuery(sql)
            device_name, model, serial_number, description, active, device_interface = query.first()

            prep = self.db.prepare(f"INSERT INTO {self.schema}.devices "
                "(device_id, device_name, model, serial_number, description, active, device_interface) VALUES "
                "(:id, :device_name, :model, :serial_number, :description, :active, :device_interface)")
            
            data = {':id': newId, ':device_name': device_name + '_copy', ':model': model, 
                    ':serial_number': serial_number, ':description': description, 
                    ':active': active, ':device_interface': device_interface}
            self.db.dbExecPrepared(prep, data)

            # Query device_configuration table and duplicate all entries
            sql = (f"SELECT device_parameter, parameter_value "
                f"FROM {self.schema}.device_configuration WHERE device_id={currDeviceId}")
            query = self.db.dbQuery(sql)

            for device_parameter, parameter_value in query:
                prep = self.db.prepare(f"INSERT INTO {self.schema}.device_configuration "
                                    f"(device_id, device_parameter, parameter_value) "
                                    f"VALUES (:id, :device_parameter, :parameter_value)")
                data = {':id': newId, ':device_parameter': device_parameter, ':parameter_value': parameter_value}
                self.db.dbExecPrepared(prep, data)
            
            self.db.commit()
            self.populate_table()
        except Exception:
            self.db.rollback()
            raise