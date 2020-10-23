# Brunoise

<a href="url"><img 
src="https://github.com/portugueslab/Brunoise/blob/master/brunoise/icons/GUI.png" 
align="left" 
height="190" 
width="270"></a>

Brunoise is a software for control of Two-Photon Laser Scanning Microscopy.
It is developed by members of the [PortuguesLab](http://www.portugueslab.com/)
 at the Technical University of Munich and Max Planck Institute of Neurobiology. 
 
Like [Sashimi](https://github.com/portugueslab/sashimi), the software is built for a particular microscope configuration, but the modular architecture allows for easy replacement of
hardware by other vendors. Moreover, the software can easily interact with others through the library [PyZMQ](https://pyzmq.readthedocs.io/en/latest/index.html) which allows to do imaging
experiments paired with a stimulation protocol.
 
# Installation

Clone this repository and navigate to the main folder `../brunoise`
    
The software uses the package `pyvisa` so oyu first need to install it:

    pip install pyvisa

# User Interface


Form the GUI the user can specify different acquisition settings and interact with external hardware such as shutters, motorized stage and laser. 
    
# Software architecture


Everything that handles the microscope hardware comes together in the ExperimentState.
Things that user set are called Settings (handled via lightparam for automated GUI creation), and the hardware-related things that are computed from
the user settings are called Parameters (e.g. `ScanningParameters`).
GUI code should only access the hardware through the `ExperimentState`
