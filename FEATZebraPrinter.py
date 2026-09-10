"""
FEAT specific instructions for printing labels

created by: Alicia Billings; alicia.billings@noaa.gov
date: April 2019
notes:
"""

from simple_zpl2 import Code128_Barcode, ZPLDocument, NetworkPrinter
import io
from PIL import Image
from datetime import datetime as dt
import socket


class PrintLabel:
    def __init__(self, ship, survey, ip='192.168.0.124', port=9100):
        self.ship = ship
        self.survey = survey
        self.ip = ip
        self.port = int(port)

    def printer_status(self):
        """
        tests that the printer can be connected to
        :return: boolean True for yes, False for no
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((self.ip, self.port))
            s.close()
            return True
        except Exception as e:
            print(e)
            return False

    def print_label(self, project, species_name, species_code, event, code, spec_num=None, length=None,
                    weight=None, center=None):
        """
        takes the passed information and sends to the printer
        :param project: name of the project
        :param species_name: name of the species
        :param species_code: code of the species
        :param event: event number
        :param code: barcode zpl
        :param spec_num: specimen number
        :param length: length of the specimen
        :param weight: weight of the specimen
        :param center: org name
        :return: none
        """
        # get current date
        cur_date = dt.now().date().strftime("%m/%d/%Y")

        # set up barcode
        bc = Code128_Barcode(code, 'N', 100, 'Y')

        z_doc = ZPLDocument()
        # TOP LINE; IWCPS Sample Haul: # SN: #
        z_doc.add_zpl_raw("^XA")
        z_doc.add_zpl_raw("^FO15,55")
        if center:
            z_doc.add_zpl_raw("^A0N,110,40^FDIWCPS " + center + " Sample\tHaul: " + str(event))
        else:
            z_doc.add_zpl_raw("^A0N,110,40^FDIWCPS Sample\tHaul: " + str(event))
        if spec_num:
            z_doc.add_zpl_raw("\t\tSN: " + str(spec_num) + "^FS")
        else:
            z_doc.add_zpl_raw("^FS")

        # SECOND LINE; project and species
        z_doc.add_zpl_raw("^FO15,170")
        z_doc.add_zpl_raw("^A0N,60,35^FDProject: " + str(project) + "\tSP: " + species_code + " - "
                          + species_name + "^FS")

        # THIRD LINE
        if length:
            z_doc.add_zpl_raw("^FO15,250")
            z_doc.add_zpl_raw("^A0N,40,30^FDLength: " + str(length))
            if weight:
                z_doc.add_zpl_raw("\tWeight: " + str(weight) + "^FS")
            else:
                z_doc.add_zpl_raw("^FS")

        # BARCODE
        z_doc.add_zpl_raw("^FO55,325")
        z_doc.add_zpl_raw("^A0N,60,50^BY3^BCN,100,Y,N,N")
        z_doc.add_zpl_raw("^FD" + str(code) + "^FS")

        # FINAL LINE
        z_doc.add_zpl_raw("^FO15,500")
        z_doc.add_zpl_raw(
            "^A0N,50,35^FDSurvey: " + self.survey + "\t\tShip: " + self.ship + "\t\tDate: " + str(cur_date) + "^FS")
        z_doc.add_zpl_raw("^XZ")

        # print it out to the screen as an image for now
        """
        png = z_doc.render_png(label_width=5, label_height=3)
        fake_file = io.BytesIO(png)
        img = Image.open(fake_file)
        img.show()
        """
        # print to network printer
        printer = NetworkPrinter(self.ip, self.port)
        try:
            printer.print_zpl(z_doc)
        except (TimeoutError, PermissionError):
            print('cannot connect to printer')
        #"""