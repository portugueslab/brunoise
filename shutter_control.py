import nidaqmx

with nidaqmx.Task() as shutter_task:

    #create a channel - units: Volts
    shutter_task.ao_channels.add_ao_voltage_chan("Dev1/port0/line2", min_val=-5, max_val=5)
    #define the task
    shutter_task.write(5, auto_start=True)
    #start the task
    shutter_task.start()