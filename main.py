import machine
import logging
import cfg_manager
import mod485
import cmd_processor
import select
import sys
import lan
import line_edit
import time
import socket
import json

# Using power_monitor as a reference but some items from mailbox

    # rough sense of time for uptime reporting
pollTimeoutMs = 100     # 100ms polling

# set up the LED and define routine to toggle
led = machine.Pin('LED', machine.Pin.OUT)
def toggleLED() :
    led.value(not led.value())

# set up logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()

# TODO need to create a memory handler and add to logger

# configuration management from Mailbox project
cfg_mgr = cfg_manager.config_manager('main.ini')
config = cfg_mgr.config

# access via config[SECTION][OPTION]

    # set up access to the water meter
water_meter = mod485.mod485(mod485.MODBUS_RTU)

def water_meter_read():

    result = {}
    response = water_meter.read_registers(1,1,2)
    if response is None:
        return None
    value = water_meter.toREAL4(response)
    result['flow'] = value

    response = water_meter.read_registers(1,9,4)
    if response is None:
        return None
    if response:
        value = water_meter.toLONG(response[:2]) + water_meter.toREAL4(response[2:])
    else:
        value = None
    result['accumulated'] = value

    return result

# TODO ble for configuration?

# the command processor is a hybrid of the old power_monitor processor
# and the newer scheme used in the Mailbox.
def reboot_command(*args):
    machine.reset()
    return ''

cmd_list = (
    ('reboot', reboot_command, f'reboot                         reboot the system'),
)
cmd_processor.reg_cmds(None, cmd_list)

# web server
html_head = """<!DOCTYPE html>
<html>
    <head> <title>{0}</title> </head>
    <body> <h1>{0} Power Monitor</h1>
        <pre style="font-size:3vw;">
"""
html_tail = """
        </pre>
    </body>
</html>
"""
errorMessages = {
    400:'Bad Request',
    404:'Not Found',
    405:'Method Not Allowed'
    }

def respondError(cl, code, explain=None):
    try :
        cl.send(f'HTTP/1.0 {code} {errorMessages[code]}\r\nContent-type: text/html\r\n\r\n')
        if explain :
            cl.send(f'<!DOCTYPE html><html><head><title>{errorMessages[code]}</title></head>'+
                    f'<body><center><h1>{explain}</h1></center></body></html>\r\n')
    except ConnectionResetError:
        log.error(f'ConnectionResetError while generating error response')

    return

def processWebRequest(cl, request):
    log.debug(request)
    response = ''
    try :
        header, body = request.split(b'\r\n\r\n', 1)
    except ValueError :
        respondError(cl,400, 'Unable to detect blank line separating header from body')
        return
    headerLines = header.splitlines()
    firstHeaderLine = headerLines[0].split()
    if len(firstHeaderLine) != 3 :
        respondError(cl,400, 'Missing request parameter')
        return
    (method, target, version) = firstHeaderLine
    if method != b'GET' :
        respondError(cl,405, 'Only GET method supported')		# Method not supported
        return
    if target == b'/' or target == b'/index.html' :
        html_body = ''

        values = water_meter_read()
        if values :
            html_body += f'flow = {values['flow']} gpm\n'
            html_body += f'accumulated = {values['accumulated']/100} ccf\n'
        else:
            html_body += 'Water meter is not responding'

        response = 'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'
        response += html_head.format(wifi.hostname) + html_body + html_tail
        
    elif target == b'/data.json' :
        response = 'HTTP/1.0 200 OK\r\nContent-type: application/json\r\n\r\n'
        v = water_meter_read()
        if v is None:
            v = {}

        if wifi.hostname :
            v['hostname'] = wifi.hostname
        response += json.dumps(v)

    else :
        request = request.decode()
        log.error(f'{request} {firstHeaderLine}')
        respondError(cl,404, 'File not found')
        return
    try :
        cl.send(response)
    except ConnectionResetError:
        log.error(f'ConnectionResetError while responding to request')

    # set up polling for USB console
poller = select.poll()
poller.register(sys.stdin, select.POLLIN)

    # initialize the wifi interface
wifi = lan.lan()
if wifi.wlan.isconnected():
    wifi.wifi_disconnect()
    time.sleep(1)

server = None
request_count = 0
server_state = 'idle'

    # this loop operates on a 100ms tick managed by the poller timeout
try:
    while True:
            # set up the server socket when the network comes up
        if server is None :
            if wifi.wlan.isconnected() :
                ip_address = wifi.wlan.ifconfig()[0]
                address = (ip_address, 80)
                server = socket.socket()
                server.bind(address)
                server.listen(5)
                server.setblocking(False)
                poller.register(server, select.POLLIN)
                log.info(f'Server is listening on {ip_address}:80')
                led.on()
            else :
                if any(config.options('WIFI')):
                    wifi.wifi_connect(config.get('hostname'), config.options('WIFI'))
                toggleLED()

            # check and service console and/or web server
        events = poller.poll(pollTimeoutMs)   # timeout generates empty list
        for fd, flag in events:
            if fd == sys.stdin :
                value = sys.stdin.read(1)
                command = line_edit.process_key(value)
                if command :
                    response = cmd_processor.process(command)
                    print(response)

            elif fd == server :
                server_state = 'busy'
                request_count += 1
                try :
                    cl, addr = server.accept()
                except OSError as e:
                    if e.errno != errno.ETIMEDOUT:
                        log.error(f'Connection accept() error: {e}')
                    continue

                server_state = addr
                log.debug(f'client connected from {addr}')
                cl.settimeout(5)    # LG WebTV opens connection without sending request
                try :
                    request = cl.recv(1024)
                except OSError as e:
                    log.error(f'Connection timeout - closing; {e}')
                else :
                    processWebRequest(cl, request)
                finally :
                    cl.close()
                server_state = 'idle'
            else :
                log.error(f'unknown fd {fd}')
except Exception as e:
    e_text = str(e)
    log.error(f'Fatal exceptioni in main loop - {e_text}')

# TODO web server providing viewable pages with history?
# TODO Telnet
