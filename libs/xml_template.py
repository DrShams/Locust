import xml.etree.ElementTree as ET

class XmlTemplate(object):
    def __init__(self):
        pass

    def print_param_paths(self, element, path=""):
        """
        :param element: текущий элемент (xml.etree.ElementTree.Element)
        :param path: строка — путь до родителя текущего элемента
        :return: ничего (печатает строки на stdout)
        """
        if path:
            current_path = f"{path}/{element.tag}"
        else:
            current_path = element.tag

        #Если элемент содержит внутри себя текст и это не пустая строка
        if element.text and element.text.strip():
            print(f"{current_path} = {element.text.strip()}")

        #Проитись по каждому элементу рекурсивно
        for child in element:
            self.print_param_paths(child, current_path)

    def set_param_value(self, element, values, current_path=""):
        """
        получает XML-элемент (element),
        словарь с путями и новыми значениями (values),
        и (внутренне) текущий путь current_path;
        рекурсивно проходит по всем тегам в дереве и заменяет текст внутри нужных элементов.
        """
        # Собрать текущий путь
        if current_path:
            full_path = f"{current_path}/{element.tag}"
        else:
            full_path = element.tag

        # Если текущий путь внутри словаря, заменить значение
        # Здесь мы изменяем текст внутри существующего объекта Element, который уже принадлежит дереву tree
        if full_path in values:
            element.text = str(values[full_path])

        # Рекурсивно пройтись по элементам
        for child in element:
            self.set_param_value(child, values, full_path)


    def fill_xml_template_obj(self, xml_file, values):
        """
        Загрузить XML шаблон, заполнить параметрами и вернуть значение как tree
        """
        tree = ET.parse(xml_file)#это контейнер для всего дерева
        root = tree.getroot()

        # Провести замену для перечня значений
        self.set_param_value(root, values)

        # Записать в мутируемый объект
        return tree