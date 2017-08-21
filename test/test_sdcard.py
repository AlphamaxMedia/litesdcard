#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time

from litex.soc.tools.remote import RemoteClient

litesdcard_path = "../../"
sys.path.append(litesdcard_path) # XXX

from litesdcard.phy.sdphy import *
from litesdcard.software.libsdcard import *


SD_OK = 0
SD_CRCERROR = 1
SD_TIMEOUT = 2
SD_WRITEERROR = 3

SD_SWITCH_CHECK = 0
SD_SWITCH_SWITCH = 1

SD_SPEED_SDR12 = 0
SD_SPEED_SDR25 = 1
SD_SPEED_SDR50 = 2
SD_SPEED_SDR104 = 3
SD_SPEED_DDR50 = 4

SD_GROUP_ACCESSMODE = 0
SD_GROUP_COMMANDSYSTEM = 1
SD_GROUP_DRIVERSTRENGTH = 2
SD_GROUP_POWERLIMIT = 3


def wait_cmd_done(wb):
    while True:
        cmdevt = wb.regs.sdctrl_cmdevt.read()
        if cmdevt & 0x1:
            print('cmdevt: {:08x}{}{}'.format(
                cmdevt,
                ' (CRC Error)' if cmdevt & 0x8 else '',
                ' (Timeout)' if cmdevt & 0x4 else '',
            ))
            if cmdevt & 0x4:
                return SD_TIMEOUT
            elif cmdevt & 0x8:
                return SD_CRCERROR
            return SD_OK

def wait_data_done(wb):
    while True:
        dataevt = wb.regs.sdctrl_dataevt.read()
        if dataevt & 0x1:
            print('dataevt: {:08x}{}{}{}'.format(
                dataevt,
                ' (CRC Error)' if dataevt & 0x8 else '',
                ' (Timeout)' if dataevt & 0x4 else '',
                ' (Write Error)' if dataevt & 0x2 else '',
            ))
            if dataevt & 0x4:
                return SD_TIMEOUT
            elif dataevt & 0x2:
                return SD_WRITEERROR
            elif dataevt & 0x8:
                return SD_CRCERROR
            return SD_OK

def response(wb, length, nocrccheck=False):
    status = wait_cmd_done(wb)
    response = wb.read(wb.regs.sdctrl_response.addr, 4)
    if length == SDCARD_CTRL_RESPONSE_SHORT:
        s = "{:08x}".format(response[3])
        ba = bytearray(response[3].to_bytes(4, 'little'))
    elif length == SDCARD_CTRL_RESPONSE_LONG:
        ba = bytearray()
        s = "{:08x} {:08x} {:08x} {:08x}".format(*response)
        for r in reversed(response):
            ba += bytearray(r.to_bytes(4, 'little'))
    print(s)
    return ba, status

def cmd0(wb):
    print("0: MMC_CMD_GO_IDLE_STATE")
    wb.regs.sdctrl_argument.write(0x00000000)
    wb.regs.sdctrl_command.write((0 << 8) | SDCARD_CTRL_RESPONSE_NONE)

def cmd2(wb):
    print("2: MMC_CMD_ALL_SEND_CID")
    wb.regs.sdctrl_argument.write(0x00000000)
    wb.regs.sdctrl_command.write((2 << 8) | SDCARD_CTRL_RESPONSE_LONG)
    return response(wb, SDCARD_CTRL_RESPONSE_LONG)

def cmd3(wb):
    print("3: MMC_CMD_SET_RELATIVE_CSR")
    wb.regs.sdctrl_argument.write(0x00000000)
    wb.regs.sdctrl_command.write((3 << 8) | SDCARD_CTRL_RESPONSE_SHORT)
    return response(wb, SDCARD_CTRL_RESPONSE_SHORT)

def cmd6(wb, mode, group, value, destaddr):
    print("6: SD_CMD_SWITCH_FUNC")
    arg = (mode << 31) | 0xffffff
    arg &= ~(0xf << (group * 4))
    arg |= value << (group * 4)
    wb.regs.sdctrl_argument.write(arg)
    wb.regs.sdctrl_blocksize.write(64-1)
    wb.regs.sdctrl_blockcount.write(0)
    wb.regs.ramwraddr_address.write(destaddr//4)
    wb.regs.sdctrl_command.write((6 << 8) | SDCARD_CTRL_RESPONSE_SHORT | (SDCARD_CTRL_DATA_TRANSFER_READ << 5))
    r = response(wb, SDCARD_CTRL_RESPONSE_SHORT)
    wait_data_done(wb)
    return r

def cmd7(wb, rca):
    print("7: MMC_CMD_SELECT_CARD")
    wb.regs.sdctrl_argument.write(rca << 16)
    wb.regs.sdctrl_command.write((7 << 8) | SDCARD_CTRL_RESPONSE_SHORT)
    return response(wb, SDCARD_CTRL_RESPONSE_SHORT)

def cmd8(wb):
    print("8: MMC_CMD_SEND_EXT_CSD")
    wb.regs.sdctrl_argument.write(0x000001aa)
    wb.regs.sdctrl_command.write((8 << 8) | SDCARD_CTRL_RESPONSE_SHORT)
    return response(wb, SDCARD_CTRL_RESPONSE_SHORT)

def cmd9(wb, rca):
    print("9: MMC_CMD_SEND_CSD")
    wb.regs.sdctrl_argument.write(rca << 16)
    wb.regs.sdctrl_command.write((9 << 8) | SDCARD_CTRL_RESPONSE_LONG)
    return response(wb, SDCARD_CTRL_RESPONSE_LONG)

def cmd11(wb):
    print("11: MMC_CMD_VOLTAGE_SWITCH")
    wb.regs.sdctrl_argument.write(0x00000000)
    wb.regs.sdctrl_command.write((11 << 8) | SDCARD_CTRL_RESPONSE_SHORT)
    return response(wb, SDCARD_CTRL_RESPONSE_SHORT)

def cmd12(wb):
    print("12: MMC_CMD_STOP_TRANSMISSION")
    wb.regs.sdctrl_argument.write(0x00000000)
    wb.regs.sdctrl_command.write((12 << 8) | SDCARD_CTRL_RESPONSE_SHORT)
    return response(wb, SDCARD_CTRL_RESPONSE_SHORT)

def cmd13(wb, rca):
    print("13: MMC_CMD_SEND_STATUS")
    wb.regs.sdctrl_argument.write(rca << 16)
    wb.regs.sdctrl_command.write((13 << 8) | SDCARD_CTRL_RESPONSE_SHORT)
    return response(wb, SDCARD_CTRL_RESPONSE_SHORT)

def cmd16(wb, blocklen):
    print("16: MMC_CMD_SET_BLOCKLEN")
    wb.regs.sdctrl_argument.write(blocklen)
    wb.regs.sdctrl_command.write((16 << 8) | SDCARD_CTRL_RESPONSE_SHORT)
    return response(wb, SDCARD_CTRL_RESPONSE_SHORT)

def cmd17(wb, blkaddr, destaddr):
    print("17: MMC_CMD_READ_SINGLE_BLOCK")
    wb.regs.sdctrl_argument.write(blkaddr)
    wb.regs.sdctrl_blocksize.write(512-1)
    wb.regs.sdctrl_blockcount.write(0)
    wb.regs.ramwraddr_address.write(destaddr//4)
    wb.regs.sdctrl_command.write((17 << 8) | SDCARD_CTRL_RESPONSE_SHORT | (SDCARD_CTRL_DATA_TRANSFER_READ << 5))
    r = response(wb, SDCARD_CTRL_RESPONSE_SHORT)
    wait_data_done(wb)
    return r

def cmd18(wb, blkaddr, blkcnt, destaddr):
    print("18: MMC_CMD_READ_MULTIPLE_BLOCK")
    wb.regs.sdctrl_argument.write(blkaddr)
    wb.regs.sdctrl_blocksize.write(512-1)
    wb.regs.sdctrl_blockcount.write(blkcnt-1)
    wb.regs.ramwraddr_address.write(destaddr//4)
    wb.regs.sdctrl_command.write((18 << 8) | SDCARD_CTRL_RESPONSE_SHORT | (SDCARD_CTRL_DATA_TRANSFER_READ << 5))
    r = response(wb, SDCARD_CTRL_RESPONSE_SHORT)
    wait_data_done(wb)
    return r

def cmd23(wb, blkcnt):
    print("23: MMC_CMD_SET_BLOCK_COUNT")
    wb.regs.sdctrl_argument.write(blkcnt) # 1 means 1 block
    wb.regs.sdctrl_command.write((23 << 8) | SDCARD_CTRL_RESPONSE_SHORT)
    return response(wb, SDCARD_CTRL_RESPONSE_SHORT)

def cmd24(wb):
    print("24: MMC_CMD_WRITE_SINGLE_BLOCK")
    wb.regs.sdctrl_argument.write(0x00000000)
    wb.regs.sdctrl_blocksize.write(512-1)
    wb.regs.sdctrl_blockcount.write(0)
    wb.regs.sdctrl_command.write((24 << 8) | SDCARD_CTRL_RESPONSE_SHORT | (SDCARD_CTRL_DATA_TRANSFER_WRITE << 5))
    return response(wb, SDCARD_CTRL_RESPONSE_SHORT)

def cmd25(wb, blkaddr, blkcnt):
    print("25: MMC_CMD_WRITE_MULTIPLE_BLOCK")
    wb.regs.sdctrl_argument.write(blkaddr)
    wb.regs.sdctrl_blocksize.write(512-1)
    wb.regs.sdctrl_blockcount.write(blkcnt-1)
    wb.regs.sdctrl_command.write((25 << 8) | SDCARD_CTRL_RESPONSE_SHORT | (SDCARD_CTRL_DATA_TRANSFER_WRITE << 5))
    return response(wb, SDCARD_CTRL_RESPONSE_SHORT)

def cmd55(wb, rca=0):
    print("55: MMC_CMD_APP_CMD")
    wb.regs.sdctrl_argument.write(rca << 16)
    wb.regs.sdctrl_command.write((55 << 8) | SDCARD_CTRL_RESPONSE_SHORT)
    return response(wb, SDCARD_CTRL_RESPONSE_SHORT)

def acmd6(wb):
    print("6: SD_CMD_APP_SET_BUS_WIDTH")
    wb.regs.sdctrl_argument.write(0x00000002)
    wb.regs.sdctrl_command.write((6 << 8) | SDCARD_CTRL_RESPONSE_SHORT)
    return response(wb, SDCARD_CTRL_RESPONSE_SHORT)

def acmd13(wb, destaddr):
    print("13: SD_CMD_APP_SEND_STATUS")
    wb.regs.sdctrl_argument.write(0x00000000)
    wb.regs.sdctrl_blocksize.write(64-1)
    wb.regs.sdctrl_blockcount.write(0)
    wb.regs.ramwraddr_address.write(destaddr//4)
    wb.regs.sdctrl_command.write((13 << 8) | SDCARD_CTRL_RESPONSE_SHORT | (SDCARD_CTRL_DATA_TRANSFER_READ << 5))
    r = response(wb, SDCARD_CTRL_RESPONSE_SHORT)
    wait_data_done(wb)
    return r

def acmd41(wb, hcs=False, s18r=False):
    print("41: SD_CMD_APP_SEND_OP_COND")
    arg = 0x10ff8000
    if hcs:
        arg |= 0x60000000
    if s18r:
        arg |= 0x01000000
    wb.regs.sdctrl_argument.write(arg)
    wb.regs.sdctrl_command.write((41 << 8) | SDCARD_CTRL_RESPONSE_SHORT)
    return response(wb, SDCARD_CTRL_RESPONSE_SHORT, nocrccheck=True)

def acmd51(wb, destaddr):
    print("51: SD_CMD_APP_SEND_SCR")
    wb.regs.sdctrl_argument.write(0x00000000)
    wb.regs.sdctrl_blocksize.write(8-1)
    wb.regs.sdctrl_blockcount.write(0)
    wb.regs.ramwraddr_address.write(destaddr//4)
    wb.regs.sdctrl_command.write((51 << 8) | SDCARD_CTRL_RESPONSE_SHORT | (SDCARD_CTRL_DATA_TRANSFER_READ << 5))
    r = response(wb, SDCARD_CTRL_RESPONSE_SHORT)
    wait_data_done(wb)
    return r

def acmd22(wb, destaddr):
    print("22: SD_CMD_APP_SEND_NUM_WR_BLOCKS")
    wb.regs.sdctrl_argument.write(0x00000000)
    wb.regs.sdctrl_blocksize.write(4-1)
    wb.regs.sdctrl_blockcount.write(0)
    wb.regs.ramwraddr_address.write(destaddr//4)
    wb.regs.sdctrl_command.write((22 << 8) | SDCARD_CTRL_RESPONSE_SHORT | (SDCARD_CTRL_DATA_TRANSFER_READ << 5))
    r = response(wb, SDCARD_CTRL_RESPONSE_SHORT)
    wait_data_done(wb)
    return r

def settimeout(wb, clkfreq, timeout):
    clktimeout = int(timeout * clkfreq)
    wb.regs.sdctrl_cmdtimeout.write(clktimeout)
    wb.regs.sdctrl_datatimeout.write(clktimeout)

def memset(wb, addr, value, length):
    for i in range(length//4):
        wb.write(addr + 4*i, value)

def wait_ramread_done(wb):
    while not wb.regs.ramreader_done.read():
        pass

def ramread(wb, srcaddr):
    wb.regs.ramreader_address.write(srcaddr//4)
    wb.regs.ramreader_length.write(512)
    print("ramread")
    wait_ramread_done(wb)
    print("done")

def dumpall(wb, addr, length):
    for i in range(length//4):
        print('{:08x}: {:08x}'.format(addr + 4*i, wb.read(addr + 4*i)))

def incremental(wb, addr):
    for i in range(512//4):
        k = (4*i) & 0xff
        dw = k | ((k+1)<<8) | ((k+2)<<16) | ((k+3)<<24)
        wb.write(addr + 4*i, dw & 0xffffffff)

def main(wb, sim=False):
    clkfreq = 50000000
    settimeout(wb, clkfreq, 0.1)

    # RESET CARD
    cmd0(wb)
    cmd8(wb)

    # WAIT FOR CARD READY
    s18r = False
    while True:
        cmd55(wb)
        r3,status = acmd41(wb, hcs=True, s18r=s18r)
        if r3[3] & 0x80:
            print('ready')
            if s18r and (r3[3] & 0x01):
                print('1.8V ok')
            else:
                s18r = False
                print('1.8V NOT ok')
            break

    # VOLTAGE SWITCH
    if s18r:
        cmd11(wb)

    # SEND IDENTIFICATION
    cmd2(wb)

    # SET RELATIVE CARD CSRESS
    r6,status = cmd3(wb)
    rca = decode_rca(r6)

    # SEND CSD
    cmd9(wb, rca)
    # SELECT CARD
    cmd7(wb, rca)

    # SET BUS WIDTH (WIDE)
    cmd55(wb, rca)
    acmd6(wb)

    # SEND SCR
    cmd55(wb, rca)
    acmd51(wb, wb.mems.sram.base) # SCR register (rouge): 02 35 80 03 00 00 00 00 (Phy Layer Version 3.0)
    dumpall(wb, wb.mems.sram.base, 8)
    scr = decode_scr(wb, wb.mems.sram.base)
    if not scr.cmd_support_sbc:
        print("Need CMD23 support")
        return

    # SEND STATUS
    # cmd55(wb, rca)
    # acmd13(wb, wb.mems.sram.base)
    # dumpall(wb, wb.mems.sram.base, 64)

    # SWITCH SPEED
    cmd6(wb, SD_SWITCH_CHECK, SD_GROUP_ACCESSMODE, SD_SPEED_SDR25, wb.mems.sram.base)
    dumpall(wb, wb.mems.sram.base, 64) # 00 c8 80 01 80 01 80 01 80 01 c0 01 80 03 00 00 01 00 00 00 00 00 00 00 ...
    # cmd6(wb, SD_SWITCH_SWITCH, SD_GROUP_ACCESSMODE, SD_SPEED_SDR25, wb.mems.sram.base)
    # dumpall(wb, wb.mems.sram.base, 64)

    # SET BLOCKLEN
    cmd16(wb, 512)

    # # READ ONE BLOCK
    # memset(wb, wb.mems.sram.base, 0, 1024)
    # cmd17(wb, 0, wb.mems.sram.base)
    # dumpall(wb, wb.mems.sram.base, 512)

    # READ MULTIPLE BLOCKS
    memset(wb, wb.mems.sram.base, 0, 1024)
    cmd23(wb, 2) # If supported in SCR
    cmd18(wb, 0, 2, wb.mems.sram.base)
    cmd13(wb, rca)
    # dumpall(wb, wb.mems.sram.base, 1024)

    # WRITE MULTIPLE BLOCKS
    # incremental(wb, wb.mems.sram.base)
    # writemem(wb)
    memset(wb, wb.mems.sram.base, 0x0f0f0f0f, 1024)
    blkcnt = 16
    while True:
        r,status = cmd23(wb, blkcnt) # If supported in SCR
        if not status:
            break
    cmd25(wb, 0, blkcnt)
    for i in range(blkcnt):
        ramread(wb, wb.mems.sram.base)
    if not wait_data_done(wb) == SD_OK:
        cmd12(wb)
    cmd13(wb, rca)
    cmd55(wb, rca)
    acmd22(wb, wb.mems.sram.base)
    dumpall(wb, wb.mems.sram.base, 4)

    # READ MULTIPLE BLOCKS
    memset(wb, wb.mems.sram.base, 0, 1024)
    cmd23(wb, 2) # If supported in SCR
    cmd18(wb, 0, 2, wb.mems.sram.base)
    cmd13(wb, rca)
    dumpall(wb, wb.mems.sram.base, 1024)

if __name__ == '__main__':
    wb = RemoteClient(port=1234, debug=False)
    wb.open()
    main(wb, sim=False)
    wb.close()