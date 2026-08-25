#!/usr/bin/env python3
"""Generate test summary from JUnit XML results."""
import sys
import xml.etree.ElementTree as ET

def summarize(xml_file, title):
    if not xml_file.exists():
        return
    tree = ET.parse(xml_file)
    root = tree.getroot()
    testsuite = root.find('testsuite')
    if testsuite is None:
        testsuite = root
    tests = int(testsuite.attrib.get('tests', 0))
    failures = int(testsuite.attrib.get('failures', 0))
    errors = int(testsuite.attrib.get('errors', 0))
    skipped = int(testsuite.attrib.get('skipped', 0))
    passed = tests - failures - errors - skipped
    duration = float(testsuite.attrib.get('time', 0))
    print(f'## {title}')
    print(f'| Metric | Count |')
    print(f'|--------|-------|')
    print(f'| Total | {tests} |')
    print(f'| Passed | {passed} |')
    print(f'| Failed | {failures + errors} |')
    print(f'| Skipped | {skipped} |')
    print(f'| Duration | {duration:.2f}s |')
    print(f'')
    if failures + errors > 0:
        for testcase in root.findall('.//testcase'):
            failure = testcase.find('failure')
            error = testcase.find('error')
            if failure is not None:
                print(f'::error file={testcase.attrib.get("classname", "")},line={testcase.attrib.get("line", 0)}::{testcase.attrib.get("name", "")} - {failure.text[:200] if failure.text else ""}')
            elif error is not None:
                print(f'::error file={testcase.attrib.get("classname", "")},line={testcase.attrib.get("line", 0)}::{testcase.attrib.get("name", "")} - {error.text[:200] if error.text else ""}')

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <xml_file> <title>")
        sys.exit(1)
    from pathlib import Path
    summarize(Path(sys.argv[1]), sys.argv[2])