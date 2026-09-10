from ui import ui_EditWorkstationDlg
from .baseEditDlg import BaseEditDlg
from PyQt6.QtWidgets import QCheckBox

class editWorkstationDlg(BaseEditDlg, ui_EditWorkstationDlg.Ui_EditWorkstationDlg):

    def __init__(self, db, parent=None):
        super().__init__(db, parent)
        self.setupUi(self)

        # Wire the buttons
        self.setup_base()

        self.action_map = {
            'Trawl Event': self.trawlAction,
            'Enter Catch': self.catchAction,
            'Administration': self.adminAction,
            'Utilities': self.utilitiesAction
        }

    def setUp(self, workstation):
        maxCols = 2

        modules = ['Haul', 'Catch', 'Length', 'Specimen']
        if self.settings['OrganizationName'] == 'SWFSC':
            modules = ['Haul', 'Specimen', 'CatchSWFSC']
        
        self.module_map = self.populateCheckBoxes(self.modulesGrid, modules, maxCols)

        # If we have an ID (workstation list has data), it's an Edit
        if workstation and len(workstation) > 0:
            # (Keeping your original complex query logic)
            sql = ("SELECT w.workstation_id, w.hostname, w.status, w.description, w.active, "
                   "wc_main.parameter_value, wc_mod.parameter_value "
                   f"FROM {self.schema}.workstations w "
                   f"LEFT JOIN {self.schema}.workstation_configuration wc_main "
                    f"ON w.workstation_id=wc_main.workstation_id "
                   f"AND wc_main.parameter = 'MainActions' "
                   f"LEFT JOIN {self.schema}.workstation_configuration wc_mod "
                                                "ON w.workstation_id=wc_mod.workstation_id "
                   f"AND wc_mod.parameter = 'Modules' "
                   f"WHERE w.workstation_id = {workstation[0]}")
            
            query = self.db.dbQuery(sql)
            # Use tuple unpacking safely
            row = query.first()
            id_val, hostname, status, description, isActive, mainActions, modules = row

            self.idLabel.setText(str(id_val))
            self.hostnameLabel.setText(hostname)
            self.statusCB.setCurrentIndex(0 if status == 'closed' else 1)
            self.descriptionLabel.setText(description)
            self.isActive.setChecked(str(isActive) == '1')

            # Use Base Class helper methods
            if mainActions: self.sync_checkboxes(mainActions, self.action_map)
            if modules: self.sync_checkboxes(modules, self.module_map)

        else:
            # Get new ID logic
            sql = f'SELECT MAX(workstation_id) from {self.schema}.workstations'

            query = self.db.dbQuery(sql)
            max_id = query.first()[0]
            # Handle case where table is empty
            newId = (int(max_id) + 1) if max_id is not None else 1
            
            self.idLabel.setText(str(newId))
            self.hostnameLabel.setText('')
            self.statusCB.setCurrentIndex(0)
            self.descriptionLabel.setText('')
            self.isActive.setChecked(False)

            self.sync_checkboxes("", self.action_map)
            self.sync_checkboxes("", self.module_map)

    def validate_fields(self):
        return self.validate_required_fields([
            ("hostname", self.hostnameLabel.text()),
            ("description", self.descriptionLabel.text())
        ])

    def getData(self):
        # This method can be used if you want to gather all data at once before saving
        self.currHostname = self.hostnameLabel.text()
        self.currStatus = self.statusCB.currentText()
        self.currDescription = self.descriptionLabel.text()
        self.currIsActive = 1 if self.isActive.isChecked() else 0
        self.id = self.idLabel.text()

    def perform_save(self):
        # Use Base Class helper
        mainActionStr = self.create_csv_from_checkboxes(self.action_map)
        moduleStr = self.create_csv_from_checkboxes(self.module_map)

        # Insert Workstation
        prep = self.db.prepare(f"INSERT INTO {self.schema}.WORKSTATIONS "
            "(workstation_id, hostname, status, description, active) VALUES "
            "(:id, :hostname, :status, :description, :active)")
        
        data = {':id': self.id, ':hostname': self.currHostname, ':status': self.currStatus, 
                ':description': self.currDescription, ':active': self.currIsActive}
        self.db.dbExecPrepared(prep, data)

        # Insert Configs
        sql = (f"INSERT INTO {self.schema}.WORKSTATION_CONFIGURATION (workstation_id, parameter, parameter_value) "
                f"VALUES ({self.id}, 'MainActions', '{mainActionStr}'), "
                f"({self.id}, 'Modules', '{moduleStr}')")
        self.db.dbExec(sql)
    
    def update(self):
        # Use Base Class helper
        mainActionStr = self.create_csv_from_checkboxes(self.action_map)
        moduleStr = self.create_csv_from_checkboxes(self.module_map)

        # Update Workstation
        prep = self.db.prepare(f"UPDATE {self.schema}.WORKSTATIONS SET "
            "hostname=:hostname, status=:status, description=:description, active=:active "
            "WHERE workstation_id=:id")
        
        data = {':hostname': self.currHostname, ':status': self.currStatus, ':description': self.currDescription, 
                ':active': self.currIsActive, ':id': self.id}
        self.db.dbExecPrepared(prep, data)

        # Update Configs
        self.db.dbExec(f"UPDATE {self.schema}.WORKSTATION_CONFIGURATION SET "
                        f"parameter_value='{mainActionStr}' WHERE workstation_id={self.id} AND parameter='MainActions'")
        self.db.dbExec(f"UPDATE {self.schema}.WORKSTATION_CONFIGURATION SET "
                        f"parameter_value='{moduleStr}' WHERE workstation_id={self.id} AND parameter='Modules'")
      