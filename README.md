# Brunoise

[![DOI](https://zenodo.org/badge/238418598.svg)](https://zenodo.org/badge/latestdoi/238418598)
<a href="url"><img 
src="https://github.com/portugueslab/twop_python/blob/master/icons/GUI.PNG"
align="left" 
height="190" 
width="270"></a>

Brunoise is a software package for control of two-photon laser scanning microscopes.
It is developed by members of the [Portugues Lab](http://www.portugueslab.com/)
 at the Technical University of Munich and Max Planck Institute of Neurobiology. 
 
Like [Sashimi](https://github.com/portugueslab/sashimi), the software is built for a particular microscope configuration, but the modular architecture allows for easy replacement of
hardware by other vendors. Moreover, the software can easily interact with others through the library [PyZMQ](https://pyzmq.readthedocs.io/en/latest/index.html) which synchronizing imaging
experiments with behavioral recording and stimulation protocols.
 
# Installation

Clone this repository and navigate to the main folder `../brunoise`
    
The software uses the package `pyvisa` so oyu first need to install it:

    pip install pyvisa

# User Interface


From the GUI the user can specify different acquisition settings and interact with external hardware such as shutters, motorized stage and laser. 
    
# Software architecture


Everything that handles the microscope hardware comes together in the ExperimentState.
Things that user set are called Settings (handled via lightparam for automated GUI creation), and the hardware-related things that are computed from
the user settings are called Parameters (e.g. `ScanningParameters`).
GUI code should only access the hardware through the `ExperimentState`
