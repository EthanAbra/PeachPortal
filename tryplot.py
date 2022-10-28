import matplotlib.pyplot as plt
from pandas import *
import numpy as np
import sys

def on_press(event):
    global force_seat, angle_seat, coord_disp, line_disp, line_pos


    if event.key == 'right' or 'left':
        if event.key == 'right':
            line_pos +=1 
        if event.key == 'left':
            if line_pos > 0:
                line_pos -=1
            else:
                line_pos = len(angle_seat) -1
    for curdex in range(8):
        coords = (curdex//4, curdex - ((curdex//4)*4))
        line_disp[curdex].remove()
        line_disp[curdex] = ax[coords].axvline(x = angle_seat[curdex][line_pos], color = 'b')

   

    txt = "({xco:.2f},  {yco:.2f})"

    for coordex in range(8):
        coords = (coordex//4, coordex - ((coordex//4)*4))
        temp_coords = (angle_seat[coordex][line_pos], force_seat[coordex][line_pos])
        coord_disp[coordex].remove()
        coord_disp[coordex] = ax[coords].text(temp_coords[0], temp_coords[1], txt.format(xco = temp_coords[0].item(), yco = temp_coords[1].item()))
        coord_disp[coordex].set_visible(True)


    fig.canvas.draw()

data = read_csv("analysedcsv.csv")
realdata = read_csv("tryonestroke.csv", index_col = 0)
realdata.rename(columns = {"GateAngle": "GateAngle.0"}, inplace = True)
realdata.rename(columns = {"GateForceX": "GateForceX.0"}, inplace = True)
realdata.rename(columns = {"GateAngleVel": "GateAngleVel.0"}, inplace = True)

fig, ax = plt.subplots(2, 4, sharex = True)


fig.canvas.mpl_connect('key_press_event', on_press)
fig.tight_layout(pad = 1.0)
plt.rcParams['keymap.back'].remove('left')
plt.rcParams['keymap.forward'].remove('right')


# parabola
xp = np.linspace(-90, 90, 360)
yp = (xp**2 + 2*xp + 2)/-90 +75

angle_seat = [None] * 8
force_seat = [None] * 8
coord_disp = [None] * 8
line_disp = [None] * 8
line_pos = 1


for i in range(8):
    angle_seat[i] = np.asarray(realdata['GateAngle.' + str(i)])
    force_seat[i] = np.asarray(realdata['GateForceX.' + str(i)])
    coords = (i//4, i - ((i//4)*4))
    ax[coords].clear()
    ax[coords].plot(angle_seat[i], force_seat[i])
    line_disp[i] = ax[coords].axvline(x=angle_seat[i][line_pos], color = 'b')
    ax[coords].set_ylabel('Gate Force')
    ax[coords].set_xlabel('Gate °')
    ax[coords].set_title('Seat ' + str(i+1), x = .5, y = .85)
    coord_disp[i] = ax[coords].text(0, 20, 'Force boi')
    coord_disp[i].set_visible(False)


# Format plot
plt.xticks(rotation=45, ha='right')
plt.subplots_adjust(bottom=0.30)


plt.show()