# 2-photon reconstruction project
"Infrared new deal"

## Instrumentation control

For the following it needs to be figured out how it communicates with the computer
and which Python API should be used

- [X] Stage control
Serial port: figure out the port and the communication commands, use PySerial

- [X] Shutter control
Diego

- [X] Laser power control
Diego

- [ ] Photon-counted data
It is done in software. To be investigated


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

- [ ] Figure out where the image reconstruction offset of -400 at 500000Hz output rate (probably different at other rates) comes from and calculate it automatically,
or fix the timing so it is not needed. 

- [ ]  Information streaming
(Luigi or Vilim)
Hardware control needs to run in a separate process from the GUI,
yet has to be controllable through it and stream information back
(queues, ArrayQueues)
Separate process for the hardware control
and communication (parameter and array queues)

- [ ] Data saving
HDF file(s): directly split datasets

- [ ] Automatic drift correction
    Before the beginning of the experiment, capture one plane above and one below. Check online if the current image is 
    better correlated with either rather than the current plane, if so, move the stage until it is. (having one above and one below helps determine the direction)

- [ ] Physical units
    This already exists, but is not done systematically, and the nonlinearity of the galvo voltage is not taken into account
    Calibrate the physical units so at different zoom levels the size of pixels is known
    Can be done with anything flourescent and just moving it with the objective motor and checking with the caliper. 
    Physical units can then be displayed on the screen and used in the GUI for: zooming, drawing a scale bar, having a small measuring tool

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

- [ ] Diagnostics of scan patterns
Each scan pattern causes image deformations depending on other paramteres. 
Version (a) Provide a diagnostic view of the
 galvo position (also fix the physical cabling so it is not precarious) so that optimal parameters can be adjusted from the impulse response.
Veriosn (b) Use the step response function (linearity can be probably assumed) to automatically calculate the optimal parameters for the scanning pattern. 

## Further tasks
- red PMT
- ablations
