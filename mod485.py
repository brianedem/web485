from machine import UART
from machine import Pin
import struct

# Routines for reading TUF-2000B ultrasonic flow meter registers via modbus

# The unit ships with Modbus-ASCII as the default mode, but unit did not respond
# Example code in the manual did not appear to include the device address in the
# LRC calculation, but the unit did not respond with it included or not
# The unit did response to Modbus-RTU requests without any changes to the
# Communication Protocol (menu window 63 or M63), even though the instruction
# manual indicates that it needs to be changed to '1' for Modbus-RTU (unit
# was shipped with the value of '6')

# For values stored in multiple registers (ie 32-bit LONG) the unit stores
# the LSW word at the lower address, which is opposite from the Modbus standard
# of 'big-Endian'

# The unit does use the convention of documenting registers with a register
# address one greater than the register address used in the modbus request
# Theis library makes that adjustment

# modbus modes
MODBUS_RTU = 1
MODBUS_ASCII = 2

# supported modbus functions
READ_HOLDING_REGISTERS = 0x03
WRITE_SINGLE_REGISTER = 0x06

# UART used for the modbus interface
MODBUS_UART = 1

# CRC calculator for RTU messages
def crc16(data) :
    crc = 0xFFFF
    for d in data :
        crc ^= d
        for i in range(8) :
            if crc&0x0001 : crc ^= 0xA001<<1
            crc >>= 1
    return crc

class mod485:
    def __init__(self, type=MODBUS_RTU):
        self.uart = UART(MODBUS_UART, baudrate=9600, tx=Pin(4), rx=Pin(5), timeout=500, timeout_char=10)
        self.type = type

    def read_registers(self, dev_addr, start_addr, count) :
        pdu = struct.pack('>2B2H', dev_addr, READ_HOLDING_REGISTERS, start_addr-1, count)
        expected_response_pdu_len = 3 + count*2   # addr, op, len, values
        if self.type == MODBUS_ASCII:
            lrc = sum(pdu[1:])
#           lrc = sum(pdu)
            lrc = (lrc&0xFF) + (lrc>>8)
            lrc = (lrc&0xFF) + (lrc>>8)
            lrc ^= 0xFF
            request_ascii = f':{pdu.hex()}{lrc:02x}\r\n'
            print('ASCII request: ', request_ascii[:-2])
            self.uart.write(request_ascii)

            expect = 1 + (expected_response_pdu_len + 3)*2  # :, and pdu, fcs, CR, LF hex charactors
            response_ascii = self.uart.readline()
            if response_ascii is None:
                print('Timeout with no response')
                return None
            if len(response_ascii) < expect:
                print('Timeout = only {len(response_hex)} bytes received, expected {expect}')
                return None
            print('ASCII response: ', response_ascii[:-2])
            response = bytes.fromhex(response_ascii[1:-2])  # strip leading : and trailing \r\n
            print(response(' '))
            unpacked = struct.unpack(f'>3B{count}HB', response)
            r_addr, r_op, r_len = unpacked[:3]
            r_values = unpacked[3:-1]
            r_fcs = unpacked[-1:]

        else:
            request_rtu = pdu + struct.pack('H', crc16(pdu))
            print('RTU request: ', request_rtu.hex(' '))
            self.uart.write(request_rtu)

            expect = expected_response_pdu_len + 2*1            # pfu and fcs bytes
            response = self.uart.read(count*2 + 5)
            if response is None:
                print('Timeout with no response')
                return None
            if len(response) < expect:
                print('Timeout - only {len(response)} bytes received, expected {count*2+5}')
                print(' received {response.hex(" ")}')
                return None
            print('RTU response: ', response.hex())
            unpacked = struct.unpack(f'>3B{count+1}H', response)
            r_addr, r_op, r_len = unpacked[:3]
            r_values = unpacked[3:-1]
            r_fcs = unpacked[-1]

        return r_values

    def toLONG(self, words):
        print(f'toLONG processing {words}')
        return words[1]<<16 | words[0] if words else None # LSW first

    def toREAL4(self, words):
        print(f'toREAL4 processing {words}')
        if words:
            print('have words')
            rev_words = struct.pack('>2H', words[1], words[0])  # repack with words reversed
            return struct.unpack('>f', rev_words)[0]
        else:
            print('words is None')
            return None
