#!/usr/bin/env python3
"""Create empty JUnit XML for when no tests are collected."""
import xml.etree.ElementTree as ET

root = ET.Element('testsuites')
root.set('name', 'pytest tests')
suite = ET.SubElement(root, 'testsuite')
suite.set('name', 'pytest')
suite.set('errors', '0')
suite.set('failures', '0')
suite.set('skipped', '0')
suite.set('tests', '0')
suite.set('time', '0.0')
suite.set('timestamp', '')
suite.set('hostname', '')
tree = ET.ElementTree(root)
tree.write('api-contract-test-results.xml', encoding='utf-8', xml_declaration=True)