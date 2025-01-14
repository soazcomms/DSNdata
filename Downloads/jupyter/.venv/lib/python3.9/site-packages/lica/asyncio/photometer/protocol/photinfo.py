# ----------------------------------------------------------------------
# Copyright (c) 2024 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

import re
import datetime
import asyncio

# -----------------
# Third Party imports
# -------------------

import aiohttp
from sqlalchemy import text

# --------------
# local imports
# -------------

from .. import Role, Sensor

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------


def formatted_mac(mac):
    ''''Corrects TESS-W MAC strings to be properly formatted'''
    return ':'.join(f"{int(x,16):02X}" for x in mac.split(':'))


class HTMLInfo:
    """
    Get the photometer by parsing the HTML photometer home page.
    Set the new ZP by using the same URL as the HTML form displayed for humans
    """
    CONFLICTIVE_FIRMWARE = ('Nov 25 2021 v 3.2',)

    GET_INFO = {
        # These apply to the /config page
        'model': re.compile(r"([-0-9A-Z]+)\s+Settings\."),
        'name': re.compile(r"(stars\d+)"),
        'mac': re.compile(r"MAC: ([0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2})"),
        'zp': re.compile(r"(ZP|CI|CI 1): (\d{1,2}\.\d{1,2})"),
        # 'zp'    : re.compile(r"Const\.: (\d{1,2}\.\d{1,2})"),
        'freq_offset': re.compile(r"Offset mHz: (\d{1,2}\.\d{1,2})"),
        # Non-greedy matching until <br>
        'firmware': re.compile(r"Compiled: (.+?)<br>"),
        'firmware_ext': re.compile(r"Firmware v: (\d+\.\d+)<br>"),
        # This applies to the /setconst?cons=nn.nn page
        'flash': re.compile(r"New Zero Point (\d{1,2}\.\d{1,2})"),
    }

    def __init__(self, parent, addr):
        self.parent = parent
        self.log = parent.log
        self.addr = addr
        self.log.info("Using %s Info", self.__class__.__name__)

    # ----------------------------
    # Photometer Control interface
    # ----------------------------

    async def get_info(self, timeout):
        '''
        Get photometer information. 
        '''
        # label = str(self.parent.role)
        result = {}
        result['tstamp'] = datetime.datetime.now(datetime.timezone.utc)
        url = self._make_state_url()
        self.log.info("Get info from %s", url)
        timeout = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                text = await response.text()
        matchobj = self.GET_INFO['name'].search(text)
        if not matchobj:
            self.log.error("name not found!. Check unit's name")
        result['name'] = matchobj.groups(1)[0]
        matchobj = self.GET_INFO['mac'].search(text)
        if not matchobj:
            self.log.error("MAC not found!")
        result['mac'] = formatted_mac(matchobj.groups(1)[0])
        matchobj = self.GET_INFO['zp'].search(text)
        if not matchobj:
            self.log.error("ZP not found!")
        # Beware the seq index, it is not 0 as usual. See the regexp!
        result['zp'] = float(matchobj.groups(1)[1])
        matchobj = self.GET_INFO['firmware'].search(text)
        if not matchobj:
            self.log.error("Firmware not found!")
        result['firmware'] = matchobj.groups(1)[0]
        matchobj = self.GET_INFO['firmware_ext'].search(text)
        if matchobj:
            result['firmware'] = result['firmware'] + ' v' + matchobj.groups(1)[0]
        if result['firmware'] in self.CONFLICTIVE_FIRMWARE:
            self.log.error("Conflictive firmware: %s", result['firmware'])        
        matchobj = self.GET_INFO['freq_offset'].search(text)
        if not matchobj:
            self.log.warn("Frequency offset not found, defaults to 0.0 mHz")
            result['freq_offset'] = 0.0
        else:
            result['freq_offset'] = float(matchobj.groups(1)[0])/1000.0
        matchobj = self.GET_INFO['model'].search(text)
        if not matchobj:
            self.log.warn("Model not found, defaults to TESS-W")
            result['model'] = "TESS-W"
        else:
            result['model'] = matchobj.groups(1)[0]
        # This must be agreed with Cristobal ...
        result['sensor'] = Sensor.TSL237.value
        self.log.warn("Sensor model is set to %s by default", result['sensor'])
        return result

    async def save_zero_point(self, zero_point, timeout=4):
        '''
        Writes Zero Point to the device. 
        '''
        label = str(self.parent.role)
        result = {}
        result['tstamp'] = datetime.datetime.now(datetime.timezone.utc)
        url = self._make_save_url()
        # params = [('cons', '{0:0.2f}'.format(zero_point))]
        # Paradoxically, the photometer uses an HTTP GET method to write a ZP ....
        timeout = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url,) as response:
                text = await response.text()
        matchobj = self.GET_INFO['flash'].search(text)
        if not matchobj:
            raise IOError("{:6s} ZP not written!".format(label))
        result['zp'] = float(matchobj.groups(1)[0])
        return result

    # --------------
    # Helper methods
    # --------------

    def _make_state_url(self):
        return f"http://{self.addr}/config"

    def _make_save_url(self):
        return f"http://{self.addr}/setconst"


class DBaseInfo:

    def __init__(self, parent, engine):
        self.parent = parent
        self.log = parent.log
        self.log.info("Using %s Info", self.__class__.__name__)
        self.engine = engine

    # ----------------------------
    # Photometer Control interface
    # ----------------------------

    async def save_zero_point(self, zero_point, timeout=4):
        '''
        Writes Zero Point to the device. 
        '''
        if self.parent.role is Role.TEST:
            raise NotImplementedError(
                "Can't save Zero Point on a database for the %s device", str(self.parent.role))
        section = 'ref-device' if self.parent.role is Role.REF else 'test-device'
        zero_point = str(zero_point)
        async with self.engine.begin() as conn:
            try:
                await conn.execute(text("UPDATE config_t SET value = :value WHERE section = :section AND property = :property"),
                                   {"section": section, "property": "zp",
                                       "value": zero_point}
                                   )
            except Exception:
                await conn.rollback()
            else:
                await conn.commit()

    async def get_info(self, timeout):
        '''
        Get photometer information. 
        '''
        section = 'ref-device' if self.parent.role is Role.REF else 'test-device'
        async with self.engine.begin() as conn:
            result = await conn.execute(text("SELECT property, value FROM config_t WHERE section = :section"),
                                        {"section": section}
                                        )
            result = {row[0]: row[1] for row in result}
        return result


# ===========================================================
# THIS CLASS MUST BE RE-WRITTEN AND DEBUGGED IT IS STILL TWISTED-BASED.
# DO NOT USET !!!!
# ===========================================================
class CLInfo:

    """
    Get the photometer by sending commands through a line oriented interface (i.e a serial port).
    Set the new ZP by sending commands through a line oriented interface (i.e a serial port)
    """

    SOLICITED_RESPONSES = [
        {
            'name': 'firmware',
            'pattern': r'^Compiled (.+)',
        },
        {
            'name': 'mac',
            'pattern': r'^MAC: ([0-9A-Za-z]{12})',
        },
        {
            'name': 'zp',
            'pattern': r'^Actual CI: (\d{1,2}.\d{1,2})',
        },
        {
            'name': 'written_zp',
            'pattern': r'^New CI: (\d{1,2}.\d{1,2})',
        },
    ]

    SOLICITED_PATTERNS = [re.compile(sr['pattern'])
                          for sr in SOLICITED_RESPONSES]

    def __init__(self, parent):
        self.parent = parent
        self.log = parent.log
        self.log.info("Using %s Info", self.__class__.__name__)

        self.read_deferred = None
        self.write_deferred = None

    # ---------------------
    # IPhotometerControl interface
    # ---------------------

    async def save_zero_point(self, zero_point, timeout=4):
        '''
        Writes Zero Point to the device. 
        Returns a Deferred
        '''
        line = 'CI{0:04d}'.format(int(round(zero_point*100, 2)))
        self.log.info("==> [{l:02d}] {line}", l=len(line), line=line)
        await asyncio.sleep(1)
        raise NotImplementedError("save_zero_point needs to be implemented")

        # We need to implement serial por writting in the transport object !!!!!
        self.parent.sendLine(line.encode('ascii'))
        self.write_deferred = defer.Deferred()
        self.write_deferred.addTimeout(timeout, reactor)
        self.write_response = {}
        return self.write_deferred

    async def get_info(self, timeout):
        '''
        Reads Info from the device.
        '''
        line = '?'
        label = str(self.parent.role)
        self.log.info("==> [{l:02d}] {line}",
                      label=label, l=len(line), line=line)
        await asyncio.sleep(1)
        raise NotImplementedError("save_zero_point needs to be implemented")

        self.parent.sendLine(line.encode('ascii'))
        self.read_deferred = defer.Deferred()
        self.read_deferred.addTimeout(timeout, reactor)
        self.cnt = 0
        self.read_response = {}
        return self.read_deferred

    def on_photometer_info_response(self, line, tstamp):
        '''
        Handle solicted responses from photometer.
        Returns True if handled, False otherwise
        '''
        sr, matchobj = self._match_solicited(line)
        if not sr:
            return False
        # This is hardwired until we can query this on the CLI
        self.read_response['freq_offset'] = 0
        if sr['name'] == 'name':
            self.read_response['tstamp'] = tstamp
            self.read_response['name'] = str(matchobj.group(1))
            self.cnt += 1
        elif sr['name'] == 'mac':
            self.read_response['tstamp'] = tstamp
            self.read_response['mac'] = formatted_mac(matchobj.group(1))
            self.cnt += 1
        elif sr['name'] == 'firmware':
            self.read_response['tstamp'] = tstamp
            self.read_response['firmware'] = str(matchobj.group(1))
            self.cnt += 1
        elif sr['name'] == 'zp':
            self.read_response['tstamp'] = tstamp
            self.read_response['zp'] = float(matchobj.group(1))
            self.cnt += 1
        elif sr['name'] == 'written_zp':
            self.write_response['tstamp'] = tstamp
            self.write_response['zp'] = float(matchobj.group(1))
        else:
            return False
        self._maybeTriggerCallbacks()
        return True

    # --------------
    # Helper methods
    # --------------

    def _maybeTriggerCallbacks(self):
        # trigger pending callbacks
        if self.read_deferred and self.cnt == 4:
            self.read_deferred.callback(self.read_response)
            self.read_deferred = None
            self.cnt = 0

        if self.write_deferred and 'zp' in self.write_response:
            self.write_deferred.callback(self.write_response)
            self.write_deferred = None

    def _match_solicited(self, line):
        '''Returns matched command descriptor or None'''
        for i, regexp in enumerate(self.SOLICITED_PATTERNS, 0):
            matchobj = regexp.search(line)
            if matchobj:
                self.log.debug(
                    "matched {pattern}", pattern=self.SOLICITED_RESPONSES[i]['name'])
                return self.SOLICITED_RESPONSES[i], matchobj
        return None, None
