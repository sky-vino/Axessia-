# android_accessibility_parser.py

import xml.etree.ElementTree as ET


class AccessibilityParseError(Exception):
    pass


def parse_accessibility_xml(xml_data: str) -> list:
    """
    Parses uiautomator accessibility XML into raw node dicts.
    """
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        raise AccessibilityParseError(f"Invalid accessibility XML: {e}")

    nodes = []

    for elem in root.iter("node"):
        node = {
            "class": elem.attrib.get("class", ""),
            "text": elem.attrib.get("text", ""),
            "content_desc": elem.attrib.get("content-desc", ""),
            "clickable": elem.attrib.get("clickable") == "true",
            "focusable": elem.attrib.get("focusable") == "true",
            "enabled": elem.attrib.get("enabled") == "true",
            "visible": elem.attrib.get("visible-to-user") == "true",
            "bounds": elem.attrib.get("bounds", ""),
            "resource_id": elem.attrib.get("resource-id", "")
        }
        nodes.append(node)

    return nodes
