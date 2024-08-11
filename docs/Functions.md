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

<dl>
<dt>def **parse_extras**(text, pattern, filter = False)</dt>
<dd> 
Capture or remove extra material from job description.
  
  **Parameters:**
    *  text (string) -- Input text data to parse through.
    *  pattern (string) -- Raw string regex expression to use on the text.
    *  filter (bool) -- Switches from returning all instances of pattern matches in the string to filtering pattern out of input string.  Default False.

  **Example:**
  ```python
  # This will clean up 'blah' from a list of text strings called desc_txt
  parsedtxt = [parse_extras(text, r'(blah\s?)+', filter = True) for text in desc_txt if text != None]  
  ```

</dd>
</dl>
