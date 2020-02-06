# 2-photon reconstruction project
"Infrared new deal"

- [ ] Proper scanning pattern
(already almost complete)

- [ ] Calculation of parameters
basic algebra and looking up NI documentation
(area, frequency, resolution, aspect ratio)
on paper and python functions
e.g. given the zoom and the target aspect ratio, calculate the scanning pattern

- [ ] Image reconstruction and acquisition
readout from the PMT in a different frequency
figuring out how the binning happens and photon counted or not
managing the memory of the data

(for proper and improper scanning pattern)

For the following it needs to be figured out how it communicates with the computer
and which Python API should be used

- [ ] Stage control
Serial port: figure out the port and the communication commands, use PySerial

- [x] Shutter control
Diego

- [ ] Laser power control
Diego

- [ ] GUI
Needs: 
preview of the image & scanning pattern
settings for resolution and area
settings for frequency/plane duration
starting of experiment

- [ ] ZMQ synchronisation for Stytra (consult with Luigi, Ema)
bits about networking and zeromq, look at lightsheet software

- [ ]  Information streaming
(Luigi or Vilim)
Hardware control needs to run in a separate process from the GUI,
yet has to be controllable through it and stream information back
(queues, ArrayQueues)
Separate process for the hardware control
and communication (parameter and array queues)

- [ ] Data saving
HDF file(s): directly split datasets

## Further tasks
- red PMT
- ablations
