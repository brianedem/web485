'''
This is a minimal implemention of the configparser library
for use in a MicroPython application.

The .ini file is organized into sections, each containing zero or more objects.
A new section is introduced with a line continaing the section name inclosed in
square brackets ([]).
An object consists of a line containing an object name, an '=', and a value.
The value is treated as a string and may be quoted or unquoted with double quotes (").
Comments , introduced with a '#' or ';', are allowed on otherwise empty lines, and may be indented

The .ini file is parsed into a dictonary indexed by section name. Each section entry contains
a dictonary indexed by object name and contains the object value.

Implementation Notes:

 Reading the .ini file
 When a .ini file is read an outline of the file contents is created. The outline preserves the
 order of the entries, comments, and any blank or ill-formed lines.
 If there are duplicate section declarations, they are counted in the section_count dictonary

 Writing the .ini file
 When a .ini file is displayed or written, the outline is used to generate the output.
 New sections will be located after all previously existing entries.
 New options will be added to the end of the section
 If duplicate sections were present in the original file, new options will be added to the last duplicate section
 A shadow values object is used to identify new sections and objects. As objects are output, they are removed
 from the shadow. At the end of last duplicate section any remaining objects of the section in the shadow values
 are new. At the end of processing the outline, any sections in the shadow values still containing object are
 new sections.

'''
# TODO - option names need to be forced to lower case

import logging
import platform
import re
import os

_SECTION = 0
_OPTION = 1
_COMMENT = 2
UNNAMED_SECTION = 'UNNAMED_SECTION'

log = logging.getLogger(__name__)

class NoSectionError(Exception):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details

class DuplicateSectionError(Exception):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details

class ConfigParser():
    def __init__ (self):
        self.values = {UNNAMED_SECTION: {}}
        self.modified = False
        self.validate = []
        self.outline = []               # template used when updating configuration file
        self.section_count = {UNNAMED_SECTION:1}    # tracks identical section headers

    def __getitem__(self, section):
        return(self.values[section])

    def __setitem__(self, section, value):
        self.values[section] = value

    def sections(self):
        return self.values.keys()

    def add_section(self, section):
        if type(section) is not str:
            raise TypeError("section must be str type");
        if self.has_section(section):
            raise DuplicateSectionError("Duplicate section error")
        self.values[section] = {}

    def has_section(self, section):
        return section in self.values

    def options(self, section):
        return self.values.get(section, {})

    def has_option(self, section, option):
        return option in self.values[section] if self.has_section(section) else False

    def read(self, config_file):
        self.config_file = config_file
        sp = re.compile(r'\s*\[(\w+)\]')
        op = re.compile(r'\s*([0-9a-zA-Z_.]+)\s*=\s*([^\s].*)')
        cp = re.compile(r'\s*[#;]')

        line_no = 0
        section = UNNAMED_SECTION
        self.values[section] = {}
        try:
            cf = open(config_file)
            for line in cf:
                line_no += 1

                if m := sp.match(line):     # section match
                    section = m.group(1)
                    if section in self.values:
                        self.section_count[section] += 1
                    else:
                        self.values[section] = {}
                        self.section_count[section] = 1
                    self.outline.append((_SECTION,section))
                    continue

                if m := op.match(line):     # unquoted option value assignment
                    option, value = m.groups()
                    self.values[section][option] = value.strip()
                    self.outline.append((_OPTION,option))
                    continue

                self.outline.append((_COMMENT,line.strip('\n')))
                if m := cp.match(line):     # comment
                    continue

                if line.strip():            # unmatched non-blank line
                    print(f'format error at line {line_no} - ignoring')
                    
        except OSError:
            log.warning(f'Config file {config_file} not found')

    def get(self, *args, fallback=None):
        if len(args) == 2:
            section = args[0]
        else:
            section = UNNAMED_SECTION
        option = args[-1]
        return self.values[section][option] if self.has_option(section, option) else fallback

    def getint(self, section, option, fallback=None):
        value = self.get(section, option)
        return fallback if value is None else int(value)

    def set(self, *args):
        if len(args) == 3:
            section = args[0]
        elif len(args) == 2:
            section = UNNAMED_SECTION
        else:
            raise TypeError(f'set() requires two or three positional arguments')
        option, value = args[-2:]
        if type(option) is not str:
            raise TypeError("option must be of str type")
        if type(value) is not str:
            raise TypeError("value must be of str type")
        if not self.has_section(section):
            raise NoSectionError("Section not present")
        self.values[section][option] = value
            
    def write(self, fd):
        fd.write(self.dump2())

    def remove_option(self, section, option):
        if not self.has_section(section):
            raise NoSectionError("Section not present")
        if self.has_option(section, option):
            del self.values[section][option]
            return True
        else:
            return False
            
    def remove_section(self, section):
        if self.has_section(section):
            del self.values[section]
            return True
        else:
            return False

    def dump(self):
        res = []
        for section in self.values:
            options = self.values[section]
            if section != UNNAMED_SECTION:
                res.append(f'[{section}]')
            else:
                res.append(f'#[{section}]')
            for option,value in options.items():
                res.append(f'{option} = {value}')
        return '\n'.join(res)

    def dump2(self):
        response = []

        # create a shadow copy of section_count as it will be modified
        shadow_section_count = self.section_count.copy()

        # create a shadow copy of the values structure containing section and option names
        # options will be deleted from the shadow copy when referenced by the outline
        # remaining option values were added and need to be output separately
        shadow_values = {}
        for section in self.values:
            shadow_values[section] = set(self.values[section])

        section = UNNAMED_SECTION   # first section is unnamed

        if self.outline:            # if there is an existing outline use it as a guide
            for type_,i in self.outline:
    #           print(type_, i)
                if type_ is _SECTION:
                    # check to see if the previous section has any more copies
                    if shadow_section_count[section] == 1:  # no
                        # any remaining options are new and need to be output
    #                   print(shadow_values[section])
                        for option in shadow_values[section]:
                            value = self.values[section][option]
                            response.append(f'{option} = {value}')
                            shadow_values[section].remove(option)
                        del shadow_values[section]
                    else:
                        shadow_section_count[section] -= 1

                    section = i
                    if section in self.values:
                        response.append(f'[{section}]')
                    else:
                        pass    # section was deleted
                elif type_ is _OPTION:
                    option = i
                    if section in self.values and option in self.values[section]:
                        value = self.values[section][option]
                        response.append(f'{option} = {value}')
                        shadow_values[section].remove(option)
                    else:
                        pass    # section or option was deleted
                else:
                    response.append(i)

        else:   # starting from scratch
            response.append(f'#[{UNNAMED_SECTION}]')    # add first line comment

        # see if the last section processed has any more options
        # this will also dump the UNNAMED section first if starting from scratch
        for option in shadow_values[section]:
            value = self.values[section][option]
            response.append(f'{option} = {value}')
            shadow_values[section].remove(option)
        del shadow_values[section]

        # any non-empty sections in shadow values are new and need to be output
        for section in shadow_values:
            if section is not UNNAMED_SECTION:
                response.append(f'[{section}]')
            for option in shadow_values[section]:
                value = self.values[section][option]
                response.append(f'{option} = {value}')

        return '\n'.join(response)
 
if __name__ == '__main__':
    c = ConfigParser()
    print(f'{c.dump()}')
    c.read('mailbox.ini')
    print(c.dump())

    print(f'{c["NTFY"]["Topic"]}')

    c['NEW'] = {}
    c['NEW']['x'] = '5'
    print(f'{c.dump()}')

    print(c.values.keys())
    print(f'{c.has_section('WIFI')=}')
    print(f'{c.has_section('foo')=}')
    print(f'{c.options('WIFI')=}')
    print(f'{c.options('foo')=}')
    print(f'{c.has_option('NTFY','Topic')=}')
    print(f'{c.has_option('foo','Topic')=}')
    print(f'{c.has_option('NTFY','foo')=}')
    print(f'{c.get('NTFY','Topic')=}')
    print(f'{c.get('foo','Topic')=}')
    print(f'{c.get('NTFY','foo')=}')
    print(f'{c.getint('NEW','x')=}')
    try:
        x = c.getint('NTFY','Topic')
        print("ValueError for getint('NTFY','Topic') not detected")
    except ValueError:
        pass
    c.set('NEW','y','5')
    try:
        c.set('NEW','z',7)
        print("ValueError for set('NEW','z',7) not detected")
    except TypeError:
        pass
