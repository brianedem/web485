# web485
This application provides web access gateway to devices on an serial bus

Written in microPython, this project provides access to a Modbus ASCII peripheral on an RS485 bus using HTTP messages. The target hardware used to develop the application was a Raspberry Pi Pico with a using a MAX4857 based RS485 converter 

Registers are read using a URI of the form `http://<network_addr>/read_registers/<dev_addr>/<reg_addr>[?count=<number>]`, where the parameter in [] is optional

The request is converted into a Modbus PDU of the form `<dev_addr> 03 <reg_addr> <count>`. <dev_addr> is an 8-bit device address on the Modbus, <reg_addr> the 16-bit address of the first register of the sequence to be read, and <count> the number of registers to read (also 16 bit). The 16-bit values are sent MSB first.

The PDU is sent onto the serial bus using the ASCII serial format, where each byte is converted to a 2-byte ASCII hex value, introduced with an ASCII ':' and concluded with an 8-bit LRC, a carrage return, and a line feed. The LRC is calculated by adding together the bytes in the PDU with end-around carry, and inverting the result before transmitting as a 2-byte ASCII hex value.
## Example
For example, to read the first four registers of bus device 1 connected to the 'flow' gateway device the command
>http://flow/read_registers/1/0?4

would be used.

This would generate the ASCII message on the bus of
>:010300000004F8<CR><LF>

The captured response, in the form of `:010308wwwwxxxxyyyyzzzzLR<CR><LF>, could be converted into the HTTP response of
>TBD
