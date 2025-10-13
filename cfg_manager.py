import mconfigparser as configparser
import logging
import os
import cmd_processor

log = logging.getLogger(__name__)

class config_manager():
    def __init__(self, config_file):
        cmd_processor.reg_cmds(self, self.cmd_list)
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.validate = []
        try:
            self.config.read(config_file)
        except OSError:
            log.warning(f'Config file {config_file} could not be found')
        except ValueError:
            log.warning(f'Config file {config_file} format error')

    def _set(self, *args):
        if len(args) == 2:      # section was not specified
            section = configparser.UNNAMED_SECTION
        elif len(args) == 3:    # section was specified
            section = args[0]
        else:
            return "incorrect number of parameters"
        option, value = args[-2:] # last two arguments
        if self.config.has_section(section):
            self.config.set(section, option, value)
        else:
            return f'Unknown section {section}'
        return "OK"

    def show(self):
        return self.config.dump2()

    def save(self):
        temp_file = 'config_tmp.ini'
        try:
            with open(temp_file, 'w') as cfd:
                self.config.write(cfd)
        except:
            return "save failed - unable to create temporary file"
        try:
            os.rename(temp_file, self.config_file)
        except:
            return f"save failed - unable to replace {self.config_file} with temporary file"
        return "OK"

    def _delete(self, *args):
        if len(args) == 1:      # section not specified
            section = 'UNNAMED_SECTION'
        elif len(args) == 2:
            section = args[0]
        else:
            return "incorrect number of parameters"
        option = args[-1]
        if self.config.has_section(section):
            self.config.remove_option(section, option)
        else:
            return f'Unknown section {section}'
        return 'OK'

    def _section(self, *args):
        if len(args) != 2:
            return 'incorrect number of parameters'
        action = args[0]
        section = args[1]
        if action=='add':
            if self.config.has_section(section):
                return f'Section {section} already exists'
            else:
                self.config.add_section(section)
        else:   # action=='remove'
            if self.config.has_section(section):
                self.config.remove_section(section)
            else:
                return f'Section {section} does not exist'
        return 'OK'

    cmd_list = (
        (r'config show', show,
            'config show                    show the current configuration'),
        (r'config save', save,
            'config save                    save the current configuration to disk'),
        (r'config del (\w+) (\w+)',_delete,
            'config del <section> <option>  delete the specified option from the configuration'),
        (r'config del (\w+)',_delete,
            'config del <option>            delete the specified option from the configuration'),
        (r'config set (\w+) (\w+) (\w+)',_set,
            'config set <section> <element> <value>       set the option to the value'),
        (r'config set (\w+) (\w+)',_set,
            'config set <element> <value>   set the option to the value'),
        (r'config section (add|remove) (\w+)', _section,
            'config section add|remove <section>       create named section'),
        )

