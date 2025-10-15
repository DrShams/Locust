from xml_template import XmlTemplate
import xml.etree.ElementTree as ET

# Загрузим файл как образец
tree = ET.parse("test.xml")
root = tree.getroot()

xml = XmlTemplate()

#Выведем все пути
xml.print_param_paths(root)

#Заменим параметры по определенным путям XML
values = {
    "Configuration/Database/Host": "localhost",
    "Configuration/Database/Port": "7644",
    "Configuration/Database/Username": "admin"
}

final_xml = xml.fill_xml_template_obj("test.xml", values)
root_filled = final_xml.getroot()

xml_str = ET.tostring(root_filled, encoding="unicode")
print(xml_str)