import nidaqmx
from nidaqmx.constants import LineGrouping

with nidaqmx.Task() as shutter_task:
    # create a digital output channel
    shutter_task.do_channels.add_do_chan("Dev1/port0/line1",line_grouping=LineGrouping.CHAN_PER_LINE)
    # define the task\
    shutter_task.write(True, auto_start=True)
    shutter_task.write(False, auto_start=True)