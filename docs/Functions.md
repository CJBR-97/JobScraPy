---
title: Core Functions
layout: default
filename: Functions.md
excerpt: Documentation on the core functions of this project.
nav_order: 1
nav_exclude: false
search_exclude: false
---

### Core Functions

The core functions and their options will be detailed here as they are updated and examples are constructed.

## parse_extras
<dl>
<dt>def parse_extras(text, pattern, filter = False)</dt>
<dd> 
Capture or remove extra material from job description.
</dd>
</dl>

  **Parameters:**
  *  text (str) -- Input text data to parse through.
  *  pattern (str) -- Raw string regex expression to use on the text.
  *  filter (bool) -- Switches from returning all instances of pattern matches in the string to filtering pattern out of input string.  Default False.

  **Returns:**
  *  matches (str) -- The processed input text.

  **Example:**
  ```python
  # This will clean up 'blah' from a list of text strings called desc_txt
  parsedtxt = [parse_extras(text, r'(blah\s?)+', filter = True) for text in desc_txt if text != None]  
  ```

## desc_parser
<dl>
<dt>def desc_parser(filter_func, desc_txt, pattern)</dt>
<dd> 
Parse through a list of descriptive strings using a filter function and regex pattern.
</dd>
</dl>

  **Parameters:**
  *  filter_func (func) -- Any function that takes a string and regex pattern as an argument and returns a new string.
  *  desc_txt (list of str) -- A list containing string elements.
  *  pattern (str) -- Raw string regex expression to use with a filter function.

  **Returns:**
  *  reqs (list of str) -- A list of unique, sorted elements processed through the filter function.
