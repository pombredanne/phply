#!/usr/bin/env python

# php2python.py - Converts PHP to Python using codegen.py
# Usage: php2python.py < input.php > output.py

import sys
sys.path.append('..')

from phply.phpparse import parser
from phply import pythonast

from ast import Module
from unparse import Unparser

input = sys.stdin
output = sys.stdout

body = [pythonast.from_phpast(ast) for ast in parser.parse(input.read())]
Unparser(body, output)
