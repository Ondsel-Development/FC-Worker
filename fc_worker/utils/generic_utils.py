import logging
from enum import Enum

import FreeCAD


logger = logging.getLogger(__name__)


EXCLUDE_PROPERTIES = ("CustomPropertyGroups", "ExpressionEngine", "Label", "Label2", "Proxy", "Visibility")


class PropertyType(Enum):
    STRING = "string"
    NUMBER = "number"
    SELECT = "select"
    BOOL = "bool"
    FLOAT = "float"
    LENGTH = "length"
    PERCENT = "percent"
    ANGLE = "angle"


PROPERTY_TYPE_MAPPING = {
    "App::PropertyString": PropertyType.STRING.value,
    "App::PropertyEnumeration": PropertyType.SELECT.value,
    "App::PropertyAngle": PropertyType.ANGLE.value,
    "App::PropertyBool": PropertyType.BOOL.value,
    "App::PropertyDistance": PropertyType.NUMBER.value,
    "App::PropertyFloat": PropertyType.FLOAT.value,
    "App::PropertyInteger": PropertyType.NUMBER.value,
    "App::PropertyLength": PropertyType.LENGTH.value,
    "App::PropertyPercent": PropertyType.PERCENT.value,
}


def get_property_data(obj, exclude_prps=EXCLUDE_PROPERTIES):
    data = dict()
    for prp in obj.PropertiesList:
        if prp in exclude_prps:
            continue
        prp_id = obj.getTypeIdOfProperty(prp)
        if prp_id not in PROPERTY_TYPE_MAPPING:
            logger.warning(f"{prp_id} not implemented yet.")
            continue
        value = obj.getPropertyByName(prp)
        unit = ""
        if isinstance(value, FreeCAD.Units.Quantity):
            _, unit = str(value).split(" ")
            value = value.Value

        if PROPERTY_TYPE_MAPPING[prp_id] == PropertyType.SELECT.value:
            data[prp] = {
                "type": PROPERTY_TYPE_MAPPING[prp_id],
                "value": value,
                "unit": unit,
                "items": obj.getEnumerationsOfProperty(prp)
            }
        else:
            data[prp] = {
                "type": PROPERTY_TYPE_MAPPING[prp_id],
                "value": value,
                "unit": unit,
            }
    return data


def get_property_bag_obj(doc: FreeCAD.ActiveDocument):
    property_bag = "PropertyBag"
    for obj in doc.Objects:
        if hasattr(obj, "Proxy") and obj.Proxy:
            if obj.Proxy.__class__.__name__ == property_bag:
                return obj
    return None


def get_shape_objs(doc: FreeCAD.ActiveDocument) -> list:
    """Return all objects which create shape in the document."""

    def _get_shape(obj) -> list:
        objs = []
        if (
            hasattr(obj, "Shape")
            and not obj.Shape.isNull()
            and not obj.isDerivedFrom("App::LinkGroup")
        ):
            objs.append(obj)
        elif obj.OutList:
            for child_obj in obj.OutList:
                objs += _get_shape(child_obj)
        return objs

    shape_objs = []
    for root_obj in doc.RootObjects:
        shape_objs += _get_shape(root_obj)
    return shape_objs
