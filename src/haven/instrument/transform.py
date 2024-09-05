"""
Ophyd support for the EPICS transform record


Public Structures

.. autosummary::

    ~UserTransformN
    ~UserTransformsDevice
    ~TransformRecord
"""

import asyncio
from enum import Enum

# from ophyd import Device
from ophyd_async.core import (
    ConfigSignal,
    Device,
    DeviceVector,
    HintedSignal,
    StandardReadable,
)
from ophyd_async.epics.signal import epics_signal_r, epics_signal_rw, epics_signal_x

CHANNEL_LETTERS_LIST = "A B C D E F G H I J K L M N O P".split()


class StrEnum(str, Enum):
    pass


class CalcOption(StrEnum):
    CONDITIONAL = "Conditional"
    ALWAYS = "Always"


class ScanInterval(StrEnum):
    PASSIVE = "Passive"
    EVENT = "Event"
    IO_INTR = "I/O Intr"
    SCAN_10 = "10 second"
    SCAN_5 = "5 second"
    SCAN_2 = "2 second"
    SCAN_1 = "1 second"
    SCAN_0_5 = ".5 second"
    SCAN_0_2 = ".2 second"
    SCAN_0_1 = ".1 second"


class AlarmStatus(StrEnum):
    NO_ALARM = "NO_ALARM"
    READ = "READ"
    WRITE = "WRITE"
    HIHI = "HIHI"
    HIGH = "HIGH"
    LOLO = "LOLO"
    LOW = "LOW"
    STATE = "STATE"
    COS = "COS"
    COMM = "COMM"
    TIMEOUT = "TIMEOUT"
    HWLIMIT = "HWLIMIT"
    CALC = "CALC"
    SCAN = "SCAN"
    LINK = "LINK"
    SOFT = "SOFT"
    # BAD_SUB = "BAD_SUB"
    # UDF = "UDF"
    # DISABLE = "DISABLE"
    # SIMM = "SIMM"
    # READ_ACCESS = "READ_ACCESS"
    # WRITE_ACCESS = "WRITE_ACCESS"


class AlarmSeverity(StrEnum):
    NO_ALARM = "NO_ALARM"
    MINOR = "MINOR"
    MAJOR = "MAJOR"
    INVALID = "INVALID"


class InvalidLinkAction(StrEnum):
    IGNORE_ERROR = "Ignore error"
    DO_NOTHING = "Do Nothing"


class PVValidity(StrEnum):
    EXT_PV_NC = "Ext PV NC"
    EXT_PV_OK = "Ext PV OK"
    LOCAL_PV = "Local PV"
    CONSTANT = "Constant"


class EpicsRecordDeviceCommonAll(StandardReadable):
    """
    Many of the fields common to all EPICS records.

    Some fields are not included because they are not interesting to
    an EPICS client or are already provided in other support.
    """

    # Config signals
    def __init__(self, prefix, name=""):
        with self.add_children_as_readables(ConfigSignal):
            self.description = epics_signal_rw(str, f"{prefix}.DESC")
            self.scanning_rate = epics_signal_rw(ScanInterval, f"{prefix}.SCAN")
        # Other signals, not included in read
        self.disable_value = epics_signal_rw(int, f"{prefix}.DISV")
        self.scan_disable_input_link_value = epics_signal_rw(int, f"{prefix}.DISA")
        self.scan_disable_value_input_link = epics_signal_rw(str, f"{prefix}.SDIS")
        self.forward_link = epics_signal_rw(str, f"{prefix}.FLNK")
        self.device_type = epics_signal_r(StrEnum, f"{prefix}.DTYP")
        self.alarm_status = epics_signal_r(AlarmStatus, f"{prefix}.STAT")
        self.alarm_severity = epics_signal_r(AlarmSeverity, f"{prefix}.SEVR")
        self.new_alarm_status = epics_signal_r(AlarmStatus, f"{prefix}.NSTA")
        self.new_alarm_severity = epics_signal_r(AlarmSeverity, f"{prefix}.NSEV")
        self.disable_alarm_severity = epics_signal_rw(AlarmSeverity, f"{prefix}.DISS")
        self.processing_active = epics_signal_r(int, f"{prefix}.PACT")
        self.process_record = epics_signal_x(f"{prefix}.PROC")
        self.trace_processing = epics_signal_rw(int, f"{prefix}.TPRO")

        super().__init__(name=name)


class EpicsSynAppsRecordEnableMixin(Device):
    """Supports ``{PV}Enable`` feature from user databases."""

    def __init__(self, prefix, name=""):
        with self.add_children_as_readables(ConfigSignal):
            enable = epics_signal_rw(int, "Enable")
        super().__init__(name=name)

    async def reset(self):
        """set all fields to default values"""
        await asyncio.gather(
            self.enable.set(self.enable.enum_strs[1]), super().reset()  # Enable
        )


#############################
# End common synApps support
#############################


class TransformRecordChannel(StandardReadable):
    """
    channel of a synApps transform record: A-P

    .. index:: Ophyd Device; synApps transformRecordChannel

    .. autosummary::

        ~reset
    """

    def __init__(self, prefix, letter, name=""):
        self._ch_letter = letter
        with self.add_children_as_readables():
            self.current_value = epics_signal_rw(float, f"{prefix}.{letter}")
        with self.add_children_as_readables(ConfigSignal):
            self.input_pv = epics_signal_rw(str, f"{prefix}.INP{letter}")
            self.comment = epics_signal_rw(str, f"{prefix}.CMT{letter}")
            self.expression = epics_signal_rw(
                str,
                f"{prefix}.CLC{letter}",
            )
        self.output_pv = epics_signal_rw(str, f"{prefix}.OUT{letter}")
        self.last_value = epics_signal_r(float, f"{prefix}.L{letter}")
        self.input_pv_valid = epics_signal_r(PVValidity, f"{prefix}.I{letter}V")
        self.expression_invalid = epics_signal_r(int, f"{prefix}.C{letter}V")
        self.output_pv_valid = epics_signal_r(
            PVValidity,
            f"{prefix}.O{letter}V",
        )

        super().__init__(name=name)

    async def reset(self):
        """set all fields to default values"""
        await asyncio.gather(
            self.comment.set(self._ch_letter.lower()),
            self.input_pv.set(""),
            self.expression.set(""),
            self.current_value.set(0),
            self.output_pv.set(""),
        )


class TransformRecord(EpicsRecordDeviceCommonAll):
    """
    EPICS transform record support in ophyd

    .. index:: Ophyd Device; synApps TransformRecord

    .. autosummary::

        ~reset

    :see: https://htmlpreview.github.io/?https://raw.githubusercontent.com/epics-modules/calc/R3-6-1/documentation/TransformRecord.html#Fields
    """

    def __init__(self, prefix, name=""):
        with self.add_children_as_readables(ConfigSignal):
            self.units = epics_signal_rw(
                str,
                f"{prefix}.EGU",
            )
            self.precision = epics_signal_rw(int, f"{prefix}.PREC")
            self.version = epics_signal_r(
                float,
                f"{prefix}.VERS",
            )

            self.calc_option = epics_signal_rw(
                CalcOption,
                f"{prefix}.COPT",
            )
            self.invalid_link_action = epics_signal_r(
                InvalidLinkAction,
                f"{prefix}.IVLA",
            )
            self.input_bitmap = epics_signal_r(
                int, f"{prefix}.MAP", name="input_bitmap"
            )
        with self.add_children_as_readables():
            self.sensors = DeviceVector(
                {
                    char: TransformRecordChannel(prefix=prefix, letter=char)
                    for char in CHANNEL_LETTERS_LIST
                }
            )

        super().__init__(prefix=prefix, name=name)
        # Remove dtype, it's broken for some reason
        del self.device_type

    async def reset(self):
        """set all fields to default values"""
        channels = self.channels.values()
        await asyncio.gather(
            self.scanning_rate.set(ScanInterval.PASSIVE),
            self.description.set(self.name),
            self.units.set(""),
            self.calc_option.set(0),
            self.precision.set(3),
            self.forward_link.set(""),
            *[ch.reset() for ch in channels],
        )
        # Restore the hinted channels
        self.add_readables(channels, HintedSignal)


class UserTransformN(EpicsSynAppsRecordEnableMixin, TransformRecord):
    """Single instance of the userTranN database."""


class UserTransformsDevice(Device):
    """
    EPICS synApps XXX IOC setup of userTransforms: ``$(P):userTran$(N)``

    .. index:: Ophyd Device; synApps UserTransformsDevice
    """

    def __init__(self, prefix, name=""):
        # Config attrs
        with self.add_children_as_readables(ConfigSignal):
            self.enable = epics_signal_rw(int, f"{prefix}userTranEnable", name="enable")
        # Read attrs
        with self.add_children_as_readables():
            self.transform1 = UserTransformN("userTran1")
            self.transform1 = UserTransformN("userTran2")
            self.transform1 = UserTransformN("userTran3")
            self.transform1 = UserTransformN("userTran4")
            self.transform1 = UserTransformN("userTran5")
            self.transform1 = UserTransformN("userTran6")
            self.transform1 = UserTransformN("userTran7")
            self.transform1 = UserTransformN("userTran8")
            self.transform1 = UserTransformN("userTran9")
            self.transform1 = UserTransformN("userTran10")

    async def reset(self):  # lgtm [py/similar-function]
        """set all fields to default values"""
        await asyncio.gather(
            self.transform1.reset(),
            self.transform2.reset(),
            self.transform3.reset(),
            self.transform4.reset(),
            self.transform5.reset(),
            self.transform6.reset(),
            self.transform7.reset(),
            self.transform8.reset(),
            self.transform9.reset(),
            self.transform10.reset(),
        )
        self.add_readables(
            [
                self.transform1,
                self.transform2,
                self.transform3,
                self.transform4,
                self.transform5,
                self.transform6,
                self.transform7,
                self.transform8,
                self.transform9,
                self.transform10,
            ]
        )


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: (c) 2024, UChicago Argonne, LLC
#
# Distributed under the terms of the Argonne National Laboratory Open Source License.
#
# The full license is in the file LICENSE.txt, distributed with this software.
# -----------------------------------------------------------------------------