from ui import ui_WorkstationDlg
import setup.editDlgs.editWorkstationDlg as editWorkstationDlg
from PyQt6.QtWidgets import QTableWidgetItem
# Import the base class created above
from .baseTableDlg import BaseTableDlg 
import setup.table.measurementsDlg as measurementsDlg

class workstationDlg(BaseTableDlg, ui_WorkstationDlg.Ui_WorkstationDlg):

    def __init__(self, db, parent=None):
        # Initialize Base Logic
        super().__init__(db, parent)
        # Initialize UI (from the generated file)
        self.setupUi(self)

        # Create the specific child dialog
        dialog = editWorkstationDlg.editWorkstationDlg(self.db, parent=self)
        dialog.changed.connect(self.populate_table)

        # create measurement dialog
        self.measurementDialog = measurementsDlg.measurementsDlg(self.db, parent=self)

        # WIRE IT UP: Pass the specific table and dialog to the Base
        self.setup_base(self.workstationTable, dialog)
        self.editMeasurements.clicked.connect(self.openMeasurements)

        # Hookup duplicate button
        self.duplicateBtn.clicked.connect(self.duplicate)

    def get_select_sql(self):
        return (f"SELECT workstation_id, hostname, description, active "
                f"FROM {self.schema}.workstations ORDER BY workstation_id")

    def fill_row(self, row_idx, row_data):
        # Unpack the data returned by the query
        w_id, hostname, description, active = row_data
        
        isActive = 'Yes' if str(active) == '1' else 'No'
        
        self.table.setItem(row_idx, 0, QTableWidgetItem(str(w_id)))
        self.table.setItem(row_idx, 1, QTableWidgetItem(hostname))
        self.table.setItem(row_idx, 2, QTableWidgetItem(description))
        self.table.setItem(row_idx, 3, QTableWidgetItem(isActive))

    def get_data_for_edit(self, row_idx):
        # Workstation dialog only sends the ID (col 0) to the edit window
        return [self.table.item(row_idx, 0).text()]

    def on_selection_change(self, has_selection):
        # This automatically runs when selection changes in the Base class
        workstationId = self.table.item(self.currentRow, 0).text()
        self.measurementDialog.setCurrWorkstation(workstationId)
        self.editMeasurements.setEnabled(has_selection)
        self.duplicateBtn.setEnabled(has_selection)
    
    def openMeasurements(self):
        self.measurementDialog.populate_table()
        self.measurementDialog.exec()
    
    def duplicate(self):
        currWorkstationId = self.table.item(self.currentRow, 0).text()
        # Get new ID logic
        sql = f'SELECT MAX(workstation_id) from {self.schema}.workstations'
        query = self.db.dbQuery(sql)
        max_id = query.first()[0]
        # Handle case where table is empty
        newId = (int(max_id) + 1) if max_id is not None else 1

        # Query workstations table and duplicate
        sql = (f"SELECT hostname, status, description, active "
               f"FROM {self.schema}.WORKSTATIONS WHERE workstation_id={currWorkstationId}")
        query = self.db.dbQuery(sql)
        hostname, status, description, active = query.first()

        prep = self.db.prepare(f"INSERT INTO {self.schema}.WORKSTATIONS "
            "(workstation_id, hostname, status, description, active) VALUES "
            "(:id, :hostname, :status, :description, :active)")
        
        data = {':id': newId, ':hostname': hostname, ':status': status, 
                ':description': description, ':active': active}
        self.db.dbExecPrepared(prep, data)

        # Query workstations config table and duplicate
        sql = (f"SELECT parameter, parameter_value "
               f"FROM {self.schema}.WORKSTATION_CONFIGURATION WHERE workstation_id={currWorkstationId}")
        query = self.db.dbQuery(sql)

        for parameter, parameter_value in query:
            sql = (f"INSERT INTO {self.schema}.WORKSTATION_CONFIGURATION (workstation_id, parameter, " 
                   f"parameter_value) "
                   f"VALUES ({newId}, '{parameter}', '{parameter_value}')")
            self.db.dbExec(sql)

        # Query measurements from measurement_setup table to duplicate
        sql = f"SELECT measurement_type, device_id, gui_module FROM {self.schema}.MEASUREMENT_SETUP WHERE workstation_id={currWorkstationId}"
        query = self.db.dbQuery(sql)

        # Duplicate measurements
        for measurement_type, device_id, gui_module in query:
            sql = (f"INSERT INTO {self.schema}.MEASUREMENT_SETUP (workstation_id, measurement_type, " 
                   f"device_id, gui_module) "
                   f"VALUES ({newId}, '{measurement_type}', {device_id}, '{gui_module}')")
            self.db.dbExec(sql)
        
        self.populate_table()

