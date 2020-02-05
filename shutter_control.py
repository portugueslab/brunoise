import nidaqmx
from nidaqmx.constants import LineGrouping


with nidaqmx.Task() as shutter_task:

    #create a channel - units: Volts
    shutter_task.do_channels.add_do_chan("Dev1/port0/line1", line_grouping=LineGrouping.CHAN_PER_LINE)
    #define the task
    shutter_task.write(5, auto_start=True)
    #start the task
    shutter_task.start()
    shutter_task.wait_until_done()
