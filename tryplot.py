import matplotlib.pyplot as plt
from pandas import *
import numpy as np
import sys
from matplotlib.gridspec import GridSpec
from itertools import groupby

def on_press(event):
    global force_seat, angle_seat, coord_disp, stroke_num, line_disp, avg_boat_power
    global list_chunked
    change = False
    if event.key == 'right' or 'left':
        change = True
        if event.key == 'right':
            stroke_num +=1 
        if event.key == 'left':
            if stroke_num > 0:
                stroke_num -=1
            else:
                stroke_num = 0

    #periodic
    if change :
        print(stroke_time[stroke_num-1])
        realdata = list_chunked[stroke_num-1]
        for seat in range(8):
            angle_seat[seat] = np.asarray(realdata[seat])
            print(len(angle_seat[seat]))
            force_seat[seat] = np.asarray(realdata[8 + seat])
            print(len(force_seat[seat]))
            swivel_power[seat] = np.asarray(aperiodic['SwivelPower.' + str(seat)])
            ax[seat].clear()
            ax[seat].plot(angle_seat[seat], force_seat[seat])
            ax[i].set_xlim(-55,45)
            ax[i].set_ylim(-20,120)
            plt.setp(ax[seat].get_yticklabels(), visible=False)
            plt.setp(ax[seat].get_xticklabels(), visible=False)
        plt.setp(ax[0].get_yticklabels(), visible=True)
        plt.setp(ax[4].get_yticklabels(), visible=True)
        

        # aperiodic
        for curdex in range(2):
            line_disp[curdex].remove()
            line_disp[curdex] = ax[8+curdex].axvline(x = stroke_num, color = 'b')
        txt = "({xco:.2f},  {yco:.2f})"
        for coordex in range(2):
            temp_coords = (stroke_num, avg_boat_power[stroke_num])
            coord_disp[coordex].remove()
            coord_disp[coordex] = ax[8 + coordex].text(int(temp_coords[0]), temp_coords[1], str(temp_coords))
            coord_disp[coordex].set_visible(True)
        change = False


    fig.canvas.draw_idle()







fig = plt.figure(constrained_layout=True)
gs = GridSpec(4, 4, figure=fig)

ax = [None]*10

ax[0] = fig.add_subplot(gs[0, 0])
ax[1] = fig.add_subplot(gs[0, 1])
ax[2] = fig.add_subplot(gs[0, 2])
ax[3] = fig.add_subplot(gs[0, 3])
ax[4] = fig.add_subplot(gs[1, 0])
ax[5] = fig.add_subplot(gs[1, 1])
ax[6] = fig.add_subplot(gs[1, 2])
ax[7] = fig.add_subplot(gs[1, 3])
ax[8] = fig.add_subplot(gs[2, :])
ax[9] = fig.add_subplot(gs[3, :])

 

fig.canvas.mpl_connect('key_press_event', on_press)
fig.tight_layout(pad = 1.0)
plt.rcParams['keymap.back'].remove('left')
plt.rcParams['keymap.forward'].remove('right')




# aperiodic

# datagrab
rows_to_skip = range(1,5)
aperiodic = read_csv("AllAperiodic.csv", skiprows = rows_to_skip)
aperiodic.rename(columns = {"SwivelPower": "SwivelPower.0"}, inplace = True)

# relevant graphing info
stroke_time = np.asarray(aperiodic['Time'])
avg_boat_power = np.asarray(aperiodic['Average Power'])
swivel_power = [None] * 8
x_aperiodic = list(range(1, len(avg_boat_power)+1))
stroke_num = 1
coord_disp = [None] * 2
line_disp = [None] * 2


# periodic
angle_seat = [None] * 8
force_seat = [None] * 8
angle_vel_seat = [None] * 8

# datagrab
rows_to_skip = range(1,158)
periodic = read_csv("AllPeriodic2.csv", skiprows = rows_to_skip)


# @ some pt modularize to DATA OF INTEREST


periodic.rename(columns = {"GateAngle": "GateAngle.0"}, inplace = True)
periodic.rename(columns = {"GateForceX": "GateForceX.0"}, inplace = True)
periodic.rename(columns = {"GateAngleVel": "GateAngleVel.0"}, inplace = True)
# print(periodic)


query = []
for i in range(8):
    query.append("GateAngle." + str(i))
    query.append("GateForceX." + str(i))
    query.append("GateAngleVel." + str(i))


periodic = periodic.loc[:, periodic.columns.isin(query)]


time_list = np.asarray(periodic)


list_chunked = [time_list[i:i + (stroke_time[stroke_num]-stroke_time[stroke_num-1])//20] for i in range(0, len(time_list), (stroke_time[stroke_num]-stroke_time[stroke_num-1])//20)]

# print(len(list_chunked[0]))

#print(list_chunked[0])
#print(list_chunked[0][0])

# list_chunked = [np.append(list_chunk[0], [list_chunk[0][0]]) for list_chunk in list_chunked]

# print(list_chunked[0])

# print(np.append(list_chunked[0], [list_chunked[0][0]], axis=0))

list_chunked = [chunk.T for chunk in list_chunked]
# print(list_chunked)


realdata = list_chunked[stroke_num-1]

# realdata = realdata.T

# print(realdata)



for i in range(8):
    # print("seat angle " + str(i))
    angle_seat[i] = np.asarray(realdata[i])
    # print(angle_seat[i])
    force_seat[i] = np.asarray(realdata[8 + i])
    swivel_power[i] = np.asarray(aperiodic['SwivelPower.' + str(i)])
    ax[i].clear()
    ax[i].plot(angle_seat[i], force_seat[i])
    ax[i].set_xlim(-55,45)
    ax[i].set_ylim(-20,120)
    plt.setp(ax[i].get_yticklabels(), visible=False)
    ax[i].set_title('Seat ' + str(i+1), x = .5, y = .85)
    ax[8].plot(x_aperiodic, swivel_power[i]) # , label='SwivelPower' + str(i+1))

plt.setp(ax[0].get_yticklabels(), visible=True)
plt.setp(ax[4].get_yticklabels(), visible=True)


# ax[8].legend()
ax[9].plot(x_aperiodic, avg_boat_power)

line_disp[0] = ax[8].axvline(x=stroke_num, color = 'b')
line_disp[1] = ax[9].axvline(x=stroke_num, color = 'b')
coord_disp[0] = ax[8].text(0, 20, 'Stroke #')
coord_disp[1] = ax[9].text(0, 20, 'Stroke #')
coord_disp[0].set_visible(False)
coord_disp[1].set_visible(False)



# Format plot
plt.subplots_adjust(bottom=0.30)


plt.show()