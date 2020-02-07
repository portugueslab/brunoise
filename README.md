# 2-photon reconstruction project
"Infrared new deal"

## Instrumentation control

For the following it needs to be figured out how it communicates with the computer
and which Python API should be used

- [X] Stage control
Serial port: figure out the port and the communication commands, use PySerial

- [X] Shutter control
Diego

- [ ] Laser power control
Diego

- [ ] Photon-counted data
Ask Ruben / Ot


## Scanning

- [ ] Proper scanning pattern
(already almost complete)

- [ ] Calculation of parameters
basic algebra and looking up NI documentation
(area, frequency, resolution, aspect ratio)
on paper and python functions
e.g. given the zoom and the target aspect ratio, calculate the scanning pattern

- [X] Image reconstruction and acquisition
readout from the PMT in a different frequency
figuring out how the binning happens and photon counted or not
managing the memory of the data

(for proper and improper scanning pattern)

- [ ] Parameters and state machine for scanning
(preview, experiment running, shutter on or off)


- [ ]  Information streaming
(Luigi or Vilim)
Hardware control needs to run in a separate process from the GUI,
yet has to be controllable through it and stream information back
(queues, ArrayQueues)
Separate process for the hardware control
and communication (parameter and array queues)

- [ ] Data saving
HDF file(s): directly split datasets

## GUI

- [X] Image display
version a) just display
version b) ROI for live signal view

- [ ] Stage control
version a) like labview (labels for current position and spin boxes to change)
version b) nice sliders with markers for current position

- [ ] Experiment control
version a) input duration from Stytra, and z shift
version b) get all data from Stytra and just z shift
start button

- [ ] Scanning parameter gui
version a) all manual parameters like in labview
version b) intuitive parameters
version c) zoom in and out of the image like google maps

- [ ] ZMQ synchronisation for Stytra (consult with Luigi, Ema)
bits about networking and zeromq, look at lightsheet software


## Further tasks
- red PMT
- ablations
