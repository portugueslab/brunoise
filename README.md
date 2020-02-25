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

- [x] Calculation of parameters
basic algebra and looking up NI documentation
(area, frequency, resolution, aspect ratio)
on paper and python functions
e.g. given the zoom and the target aspect ratio, calculate the scanning pattern
     * [x] Calculate single plane duration
     * [x] See how the parameters have to be adjusted (scanning stopped) to get an _exact_ plane duration
     * [ ] Decide on parameters for user to input for scanning (sample rate output is not intuitive) and calculate the rest from those (e.g. resolution, aspect ratio, frame rate)
     * [ ] Investigate what parameters are possible in the NI system for input and output rates
     * [ ] Look at galvo responses to see how far the speed can be pushed before they fly out or burn

- [X] Image reconstruction and acquisition
readout from the PMT in a different frequency
figuring out how the binning happens and photon counted or not
managing the memory of the data

- [X] Parameters and state machine for scanning
(preview, experiment running, shutter on or off)

- [X] Figure out where the image reconstruction offset of -400 at 500000Hz output rate (probably different at other rates) comes from and calculate it automatically,

- [ ] fix things so that the mystery offset is not needed. 

- [X]  Information streaming
(Luigi or Vilim)
Hardware control needs to run in a separate process from the GUI,
yet has to be controllable through it and stream information back
(queues, ArrayQueues)
Separate process for the hardware control
and communication (parameter and array queues)

- [ ] Figure out input voltage scaling from the ADC (is it 12-bit?) and optimal saving format

- [X] Data saving
HDF file(s): directly split datasets

- [ ] Automatic drift correction
    Before the beginning of the experiment, capture one plane above and one below. Check online if the current image is 
    better correlated with either rather than the current plane, if so, move the stage until it is. (having one above and one below helps determine the direction)

- [ ] Physical units
    This already exists, but is not done systematically, and the nonlinearity of the galvo voltage is not taken into account
    Calibrate the physical units so at different zoom levels the size of pixels is known
    Can be done with anything flourescent and just moving it with the objective motor and checking with the caliper. 
    Physical units can then be displayed on the screen and used in the GUI for: zooming, drawing a scale bar, having a small measuring tool

- [ ] Add the Pockel cell and write the extra binary patter from the parts of the scanning pattern not relevant 
to the image

## GUI

- [X] Image display
    * [X] just display
    * [ ] ROI for live signal view (Hagar)
    * [ ] using the Napari library for image viewing (history of acquired images in a rolling buffer, two-channel view when red channel is implemented, gamma etc adjustments)
    * [ ] Temporal averaging

- [X] Stage control
    * [X] like labview (labels for current position and spin boxes to change)
    * [X] nice sliders with markers for current position

- [x] Experiment control
    * [x] input duration from Stytra, start button and z shift
    * [x] get all data from Stytra and just z shift

- [ ] Scanning parameter gui
    * [X] all manual parameters like in labview
    * [X] intuitive parameters (vilim)
    * [ ] zoom in and out of the image like google maps

- [X] ZMQ synchronisation for Stytra (consult with Luigi, Ema)
bits about networking and zeromq, look at lightsheet software (Ema)

- [ ] Diagnostics of scan patterns: each scan pattern causes image deformations depending on other paramteres. 
    * [ ] Provide a diagnostic view of the galvo position (also fix the physical cabling so it is not precarious) so that optimal parameters can be adjusted from the impulse response.
    * [ ] Use the step response function (linearity can be probably assumed) to automatically calculate the optimal parameters for the scanning pattern. 

## Further tasks
- [ ] red PMT
- [ ] ablations
- [ ] interlacing scanning pattern
- [ ] spiral scanning pattern
- [ ] resilient mode: if something goes wrong with scanning, restart stytra for this plane

# Notes on the program architecture
Everything that handles the microscope hardware comes together in the ExperimentState.
Things that user set are called Settings (handled via lightparam for automated GUI creation), and the hardware-related things that are computed from
the user settings are called Parameters (e.g. `ScanningParameters`).

GUI code should only access the hardware through the `ExperimentState`
