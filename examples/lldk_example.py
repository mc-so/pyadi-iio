import sys

import adi
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

# Optionally passs URI as command line argument,
# else use default ip:analog.local
vref = 4.096

my_uri = sys.argv[1] if len(sys.argv) >= 2 else "ip:analog.local"
print("uri: " + str(my_uri))

class ltc2387_x4(adi.ltc2387):
      _rx_channel_names = ["voltage0","voltage1","voltage2","voltage3"]
      _rx_data_type = np.int16

ltc2387_adc = ltc2387_x4(my_uri)
ltc2387_adc.rx_buffer_size = 4096
ltc2387_adc.sampling_frequency = 12000000

ad3552r_0 = adi.ad3552r(uri=my_uri, device_name="axi-ad3552r-0")
ad3552r_1 = adi.ad3552r(uri=my_uri, device_name="axi-ad3552r-1")

ad3552r_0.tx_enabled_channels = [1]
ad3552r_1.tx_enabled_channels = [1]
fs = int(ad3552r_0.sample_rate)
fc = 5000
N = int(fs / fc)
ts = 1 / float(fs)
t = np.arange(0, N * ts, ts)
samples = np.sin(2 * np.pi * t * fc)
samples *= (2 ** 15) - 1
samples += 2 ** 15
samples = np.int16(samples)
samples = np.bitwise_xor(32768,samples)
ad3552r_0.tx_cyclic_buffer = True
ad3552r_1.tx_cyclic_buffer = True
ad3552r_0.tx(samples)
ad3552r_1.tx(samples)


print("Sample Rate ltc : ", ltc2387_adc.sampling_frequency)
data = ltc2387_adc.rx()

x = np.arange(0, ltc2387_adc.rx_buffer_size)
out1 = np.array(data)
print(out1.shape)

voltage_0 = data[0] * 2.0 * vref / (2 ** 16)
voltage_1 = data[1] * 2.0 * vref / (2 ** 16)
voltage_2 = data[2] * 2.0 * vref / (2 ** 16)
voltage_3 = data[3] * 2.0 * vref / (2 ** 16)


plt.subplot(411)
plt.plot(x,voltage_0[0:ltc2387_adc.rx_buffer_size])
plt.subplot(412)
plt.plot(x,voltage_0[ltc2387_adc.rx_buffer_size:  2*ltc2387_adc.rx_buffer_size])
plt.subplot(413)
plt.plot(x,voltage_0[2*ltc2387_adc.rx_buffer_size:3*ltc2387_adc.rx_buffer_size])
plt.subplot(414)
plt.plot(x,voltage_0[3*ltc2387_adc.rx_buffer_size:4*ltc2387_adc.rx_buffer_size])
plt.show()