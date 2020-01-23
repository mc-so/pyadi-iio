import pytest
import sys

import random

import iio

import numpy as np
import pytest
import adi
import test.iio_scanner as iio_scanner
import test.rf.spec as spec
import sys
import time

dev_checked = False
found_dev = False
URI = "ip:analog"


class BaseTestHelpers:
    devicename = "pluto"
    skipped_tests = []
    classname = "adi.ad9361"

    def check_skip(self):
        # Check if calling function is in skip list
        calling_func = sys._getframe(1).f_code.co_name
        if (calling_func in self.skipped_tests) or (not self.check_dev()):
            # pytest.xfail()
            pytest.skip("Skipping")

    def check_dev(self):
        # Must use globals since each test is a separate class instance
        global dev_checked
        global found_dev
        if not dev_checked:
            found_dev, board = iio_scanner.find_device(self.devicename)
            if found_dev:
                global URI
                URI = board.uri
            dev_checked = True
        return found_dev

    def dev_interface(self, val, attr, tol):
        global URI
        sdr = eval(self.classname + "(uri='" + URI + "')")
        # Check hardware
        setattr(sdr, attr, val)
        rval = float(getattr(sdr, attr))
        del sdr
        if not isinstance(val, str):
            if abs(val - rval) > tol:
                print("Failed to set: " + attr)
                print("Set: " + str(val))
                print("Got: " + str(rval))
            return abs(val - rval)
        else:
            return val == str(rval)


class BoardInterface(BaseTestHelpers):
    def __init__(self, classname, devicename):
        self.classname = classname
        self.devicename = devicename
        self.check_skip()


def attribute_single_value(classname, devicename, attr, start, stop, step, tol):
    bi = BoardInterface(classname, devicename)
    # Pick random number in operational range
    numints = int((stop - start) / step)
    ind = random.randint(0, numints + 1)
    val = start + step * ind
    # Check hardware
    assert bi.dev_interface(val, attr, tol) <= tol


def attribute_single_value_str(classname, devicename, attr, val, tol):
    bi = BoardInterface(classname, devicename)
    # Check hardware
    assert bi.dev_interface(str(val), attr, tol) <= tol


def attribute_single_value_pow2(classname, devicename, attr, max_pow, tol):
    bi = BoardInterface(classname, devicename)
    # Pick random number in operational range
    nums = []
    for k in range(0, max_pow):
        nums.append(2 ** k)
    ind = random.randint(0, len(nums) - 1)
    val = nums[ind]
    # Check hardware
    assert bi.dev_interface(val, attr, tol) <= tol


def dma_rx(classname, devicename, channel):
    bi = BoardInterface(classname, devicename)
    global URI
    sdr = eval(bi.classname + "(uri='" + URI + "')")
    if sdr._num_rx_channels > 2:
        if not isinstance(channel, list):
            sdr.rx_enabled_channels = [channel]
        else:
            sdr.rx_enabled_channels = channel

    try:
        for _ in range(10):
            data = sdr.rx()
            if isinstance(data, list):
                for chan in data:
                    assert np.sum(np.abs(chan)) > 0
            else:
                assert np.sum(np.abs(data)) > 0
    except Exception as e:
        del sdr
        raise Exception(e)

    del sdr


def dma_loopback(classname, devicename, channel):
    bi = BoardInterface(classname, devicename)
    global URI
    sdr = eval(bi.classname + "(uri='" + URI + "')")
    sdr.loopback = 1
    sdr.tx_cyclic_buffer = True
    if sdr._num_tx_channels > 2:
        sdr.tx_enabled_channels = [channel]
    if sdr._num_rx_channels > 2:
        sdr.rx_enabled_channels = [channel]

    # Create a ramp signal with different values for I and Q
    start = 0
    tx_data = np.array(range(start, 2 ** 11), dtype=np.int16)
    tx_data = tx_data << 4
    tx_data = tx_data + 1j * (tx_data * -1 - 1)
    sdr.rx_buffer_size = len(tx_data) * 2
    try:
        sdr.tx(tx_data)
        # Flush buffers
        for _ in range(100):
            data = sdr.rx()
        # Turn off loopback (for other tests)
        sdr.loopback = 0
    except Exception as e:
        del sdr
        raise Exception(e)
    del sdr
    # Check data
    offset = 0
    for i in range(len(data)):
        if np.real(data[i]) == start:
            for d in range(len(tx_data)):
                # print(str(data[i+offset])+" "+str(d+start))
                assert np.real(data[i + offset]) == (d + start)
                assert np.imag(data[i + offset]) == ((d + start) * -1 - 1)
                offset = offset + 1
            break


def freq_est(y, fs):
    N = len(y)
    T = 1.0 / fs
    yf = np.fft.fft(y)
    yf = np.fft.fftshift(yf)
    xf = np.linspace(-1.0 / (2.0 * T), 1.0 / (2.0 * T), N)
    # if self.do_plots:
    #     import matplotlib.pyplot as plt
    #
    #     fig, ax = plt.subplots()
    #     ax.plot(xf, 2.0 / N * np.abs(yf))
    #     plt.show()
    indx = np.argmax(np.abs(yf))
    return xf[indx]


def iq_loopback(classname, devicename, channel, param_set):
    bi = BoardInterface(classname, devicename)
    # See if we can tone using DMAs
    global URI
    sdr = eval(bi.classname + "(uri='" + URI + "')")
    # Set custom device parameters
    for p in param_set.keys():
        setattr(sdr, p, param_set[p])
    # Set common buffer settings
    sdr.tx_cyclic_buffer = True
    sdr.rx_buffer_size = 2 ** 15
    if sdr._num_tx_channels > 2:
        sdr.tx_enabled_channels = [channel]
    if sdr._num_rx_channels > 2:
        sdr.rx_enabled_channels = [channel]
    # Create a sinewave waveform
    if hasattr(sdr, "sample_rate"):
        RXFS = int(sdr.sample_rate)
    else:
        RXFS = int(sdr.rx_sample_rate)
    fc = RXFS * 0.1
    N = 2 ** 14
    ts = 1 / float(RXFS)
    t = np.arange(0, N * ts, ts)
    i = np.cos(2 * np.pi * t * fc) * 2 ** 15 * 0.5
    q = np.sin(2 * np.pi * t * fc) * 2 ** 15 * 0.5
    iq = i + 1j * q
    # Pass through SDR
    try:
        sdr.tx(iq)
        for _ in range(30):  # Wait for IQ correction to stabilize
            data = sdr.rx()
    except Exception as e:
        del sdr
        raise Exception(e)
    del sdr
    tone_freq = freq_est(data, RXFS)

    # if self.do_plots:
    #     import matplotlib.pyplot as plt
    #
    #     reals = np.real(data)
    #     plt.plot(reals)
    #     imags = np.imag(data)
    #     plt.plot(imags)
    #     plt.xlabel("Samples")
    #     plt.ylabel("Amplitude [dbFS]")
    #     plt.show()

    diff = np.abs(tone_freq - fc)
    assert (fc * 0.01) > diff
    # self.assertGreater(fc * 0.01, diff, "Frequency offset")


def t_sfdr(classname, devicename, channel, param_set, sfdr_min):
    bi = BoardInterface(classname, devicename)
    # See if we can tone using DMAs
    global URI
    sdr = eval(bi.classname + "(uri='" + URI + "')")
    # Set custom device parameters
    for p in param_set.keys():
        setattr(sdr, p, param_set[p])
    time.sleep(5)  # Wait for QEC to kick in
    # Set common buffer settings
    sdr.tx_cyclic_buffer = True
    sdr.rx_buffer_size = 2 ** 14
    if sdr._num_tx_channels > 2:
        sdr.tx_enabled_channels = [channel]
    if sdr._num_rx_channels > 2:
        sdr.rx_enabled_channels = [channel]
    # Create a sinewave waveform
    if hasattr(sdr, "sample_rate"):
        RXFS = int(sdr.sample_rate)
    else:
        RXFS = int(sdr.rx_sample_rate)
    fc = RXFS * 0.1
    N = 2 ** 14
    ts = 1 / float(RXFS)
    t = np.arange(0, N * ts, ts)
    i = np.cos(2 * np.pi * t * fc) * 2 ** 15 * 0.9
    q = np.sin(2 * np.pi * t * fc) * 2 ** 15 * 0.9
    iq = i + 1j * q
    # Pass through SDR
    try:
        sdr.tx(iq)
        for _ in range(10):  # Wait for IQ correction to stabilize
            data = sdr.rx()
    except Exception as e:
        del sdr
        raise Exception(e)
    del sdr
    val = spec.sfdr(data, plot=False)
    assert val > sfdr_min


def gain_check(
    classname, devicename, channel, param_set, dds_scale, min_rssi, max_rssi
):
    bi = BoardInterface(classname, devicename)
    # See if we can tone using DMAs
    global URI
    sdr = eval(bi.classname + "(uri='" + URI + "')")
    # Set custom device parameters
    for p in param_set.keys():
        setattr(sdr, p, param_set[p])
    # Enable DDSs
    if hasattr(sdr, "sample_rate"):
        fs = int(sdr.sample_rate)
    else:
        fs = int(sdr.rx_sample_rate)
    sdr.dds_single_tone(np.floor(fs * 0.1), dds_scale, channel)
    time.sleep(3)

    # Check RSSI
    if channel==0:
        rssi = sdr._get_iio_attr("voltage0", "rssi", False, sdr._ctrl)
    if channel==1:
        rssi = sdr._get_iio_attr("voltage1", "rssi", False, sdr._ctrl)
    if channel==2:
        rssi = sdr._get_iio_attr("voltage0", "rssi", False, sdr._ctrl_b)
    if channel==3:
        rssi = sdr._get_iio_attr("voltage1", "rssi", False, sdr._ctrl_b)
    if channel==4:
        rssi = sdr._get_iio_attr("voltage0", "rssi", False, sdr._ctrl_c)
    if channel==5:
        rssi = sdr._get_iio_attr("voltage1", "rssi", False, sdr._ctrl_c)
    if channel==6:
        rssi = sdr._get_iio_attr("voltage0", "rssi", False, sdr._ctrl_d)
    if channel==7:
        rssi = sdr._get_iio_attr("voltage1", "rssi", False, sdr._ctrl_d)

    print(rssi)
    assert rssi >= min_rssi
    assert rssi <= max_rssi


#########################################
# Fixtures
@pytest.fixture()
def test_attribute_single_value():
    yield attribute_single_value


@pytest.fixture()
def test_attribute_single_value_str():
    yield attribute_single_value_str


@pytest.fixture()
def test_attribute_single_value_pow2():
    yield attribute_single_value_pow2


@pytest.fixture()
def test_dma_rx():
    yield dma_rx


@pytest.fixture()
def test_dma_loopback():
    yield dma_loopback


@pytest.fixture()
def test_sfdr():
    yield t_sfdr


@pytest.fixture()
def test_iq_loopback():
    yield iq_loopback


@pytest.fixture()
def test_gain_check():
    yield gain_check