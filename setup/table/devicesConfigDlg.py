from ui import ui_DevicesConfigDlg
import setup.editDlgs.editDeviceConfigDlg as editDevicesConfig
from PyQt6.QtWidgets import QTableWidgetItem
# Import the base class created above
from .baseTableDlg import BaseTableDlg 

class devicesDlg(BaseTableDlg, ui_DevicesConfigDlg.Ui_DevicesConfigDlg):

    def __init__(self, db, parent=None):
        # Initialize Base Logic
        super().__init__(db, parent)
        # Initialize UI (from the generated file)
        self.setupUi(self)
        self.deviceId = 0

        # Create the specific child dialog
        self.dialog = editDevicesConfig.editDeviceConfig(self.db, parent=self)
        self.dialog.changed.connect(self.populate_table)

        # WIRE IT UP: Pass the specific table and dialog to the Base
        self.setup_base(self.deviceConfigTable, self.dialog)

    # --- Implement the Hooks ---
    def setDeviceId(self, id):
        self.deviceId = id
        self.dialog.setDeviceId(self.deviceId)

    def get_select_sql(self):
        return (f"SELECT device_id, device_parameter, parameter_value FROM "
               f"{self.schema}.device_configuration where device_id={self.deviceId} "
               f"ORDER BY device_id")

    def fill_row(self, row_idx, row_data):
        # Unpack the data returned by the query
        id, param, value = row_data
        
        self.table.setItem(row_idx, 0, QTableWidgetItem(str(id)))
        self.table.setItem(row_idx, 1, QTableWidgetItem(param))
        self.table.setItem(row_idx, 2, QTableWidgetItem(value))

    def get_data_for_edit(self, row_idx):
        # Workstation dialog only sends the ID (col 0) to the edit window
        return [
            self.table.item(row_idx, 0).text(),
            self.table.item(row_idx, 1).text(),
            self.table.item(row_idx, 2).text()
        ]