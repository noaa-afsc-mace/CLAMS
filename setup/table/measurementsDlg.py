from ui import ui_MeasurementsDlg
import setup.editDlgs.editMeasurementDlg as editMeasurementDlg
from PyQt6.QtWidgets import QTableWidgetItem
# Import the base class created above
from .baseTableDlg import BaseTableDlg 

class measurementsDlg(BaseTableDlg, ui_MeasurementsDlg.Ui_MeasurementsDlg):

    def __init__(self, db, parent=None):
        # Initialize Base Logic
        super().__init__(db, parent)
        # Initialize UI (from the generated file)
        self.setupUi(self)
        self.workstationId = 0

        # Create the specific child dialog
        self.dialog = editMeasurementDlg.editMeasurement(self.db, parent=self)
        self.dialog.changed.connect(self.populate_table)

        # WIRE IT UP: Pass the specific table and dialog to the Base
        self.setup_base(self.measurementTable, self.dialog)

    # --- Implement the Hooks ---
    def setCurrWorkstation(self, id):
        self.workstationId = id
        self.dialog.setCurrWorkstation(id)

    def get_select_sql(self):
        return (f"SELECT workstation_id, measurement_type, device_id, gui_module "
                f"FROM {self.schema}.measurement_setup "
                f"WHERE workstation_id={self.workstationId} ORDER BY gui_module")

    def fill_row(self, row_idx, row_data):
        # Unpack the data returned by the query
        w_id, measurement, deviceId, module = row_data
                
        self.table.setItem(row_idx, 0, QTableWidgetItem(str(w_id)))
        self.table.setItem(row_idx, 1, QTableWidgetItem(measurement))
        self.table.setItem(row_idx, 2, QTableWidgetItem(str(deviceId)))
        self.table.setItem(row_idx, 3, QTableWidgetItem(module))

    def get_data_for_edit(self, row_idx):
        # Workstation dialog only sends the ID (col 0) to the edit window
        return [
            self.table.item(row_idx, 0).text(),
            self.table.item(row_idx, 1).text(),
            self.table.item(row_idx, 2).text(),
            self.table.item(row_idx, 3).text(),
        ]