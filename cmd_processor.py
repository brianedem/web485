import re

# each subsystem will supply a possible class reference and a list of commands
# each item in the list is a tuple of three items:
# - re match pattern
# - a routine that performs the command
# - help text
# if the class reference is not None then the routine is assumed to be bound and
# will be passed the class reference

cmd_list = []
def reg_cmds(subsystem, commands):
    for cmd in commands:
        r, f, h = cmd
        cmd_list.append((subsystem, r, f, h))

def process(command):
    if command.startswith('help'):
        response = []
        response.append('help                           describe available commands')
        for c in cmd_list:
            if len(c) > 3:
                response.append(c[3])
            else:
                response.append(c[1])

        return '\n'.join(response)
 
    for c in cmd_list:
        s, r, f, h = c
        m = re.match(r, command)
        if m is None:
            continue
        if s is None:
            return f(*m.groups())
        else:
            return f(s, *m.groups())

    return 'unknown command'

