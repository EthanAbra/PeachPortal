import collections
from numpy import trapz
from numpy.polynomial import Polynomial
import numpy as np
from bokeh.layouts import layout, grid
from bokeh.plotting import show
from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.resources import INLINE
from bokeh.models import Span, Label, LabelSet, PolyAnnotation

def posMult(num):
    if num >= 0:
        return 1
    else:
        return -1

def double_dip_module(theta3, thetadot3):
    slopes = []
    for idx in range(index_min_angle + resampled_drive_angles//8,index_max_angle):
        slopes += [thetadot3[idx]-thetadot3[idx-1]]


    # print(slopes)
    count = 1
    signed_slopes = []  

    for i in range(1,len(slopes)):
        if (slopes[i] >= 0 and slopes[i-1]>=0) or (slopes[i] < 0 and slopes[i-1]<0):
            count+=1
        else:
            signed_slopes+=[posMult(slopes[i-1])*count]
            count = 1

    signed_slopes +=[posMult(slopes[-1]) * count]

    # print(signed_slopes)
        
    dbl_dip_xs = []
    dbl_dip_ys = []

    sidx = 0
    while sidx <= len(signed_slopes)-3:
        if signed_slopes[sidx] > 0 and signed_slopes[sidx+1] < 0 and signed_slopes[sidx+2] > 0:
            so_far = sum(map(abs, signed_slopes[:sidx+3]))-1
            so_far_high = abs(signed_slopes[sidx+2])+2
            print(so_far_high)
            dbl_dip_xs += [theta3[index_min_angle + so_far], theta3[index_min_angle + so_far + so_far_high]]
            dbl_dip_ys += [thetadot3[index_min_angle + so_far], thetadot3[index_min_angle + so_far + so_far_high]]
            sidx += 2
        else: sidx += 1


    coords = list(zip(dbl_dip_xs, dbl_dip_ys))
        
    return coords

def workModule():
    pct_50 = len(drive_time_old)//2
    first_half = trapz(drive_y_old[:pct_50], drive_time_old[:pct_50])/100
    second_half = trapz(drive_y_old[pct_50:], drive_time_old[pct_50:])/100
    return (first_half, second_half)
    

def helperMath(theta3, thetadot3, time_resamp):

    retDict = collections.defaultdict()
    global index_min_angle
    global index_max_force
    global index_max_angle
    global resampled_drive_angles
    global drive_y_old
    global drive_x_old
    global drive_time_old

    index_min_angle = min(range(len(theta3)), key=theta3.__getitem__)
    index_max_force = max(range(len(thetadot3)), key=thetadot3.__getitem__)

    index_max_angle = index_min_angle
    while thetadot3[index_max_angle] > 0:
        index_max_angle +=1

    resampled_drive_angles = index_max_angle-index_min_angle
    max_force_pct = (index_max_force-index_min_angle)/resampled_drive_angles
    drive_y_old = thetadot3[index_min_angle:index_max_angle]
    drive_x_old = theta3[index_min_angle:index_max_angle]
    drive_time_old = time_resamp[index_min_angle:index_max_angle]

    retDict['max_force_pct'] = max_force_pct
    retDict['double_dip_coords'] = double_dip_module(theta3, thetadot3)
    retDict['work_first_half'], retDict['work_second_half'] = workModule()
    return retDict


def ideal_stroke_module(theta3, thetadot3):
    stroke_dict = collections.defaultdict()
    min_angle = theta3[index_min_angle]
    max_angle = theta3[index_max_angle]
    total_angle = max_angle-min_angle

    # drive points
    points = np.array([(min_angle, thetadot3[index_min_angle]),
                    (min_angle + (total_angle)*.10, max(thetadot3)*.68),
                    (min_angle + (total_angle)*.37, max(thetadot3)),
                    (min_angle + (total_angle)*.70, max(thetadot3)*.70),
                    (min_angle + (total_angle)*.90, max(thetadot3)*.30),
                    (max_angle , 0)])
    # get x and y vectors
    x = points[:,0]
    y = points[:,1]

    # calculate polynomial

    drive_f = Polynomial.fit(x,y,6)

    # calculate new x's and y's
    drive_x_ideal = np.linspace(x[0], x[-1], resampled_drive_angles)
    stroke_dict['drivex'] = drive_x_ideal

    drive_y_ideal = drive_f(drive_x_ideal)
    stroke_dict['drivey'] = drive_y_ideal


    #recovery points
    points = np.array([(min_angle, thetadot3[index_min_angle]),
                    (min_angle + (total_angle)*.20, 0),
                    (min_angle + (total_angle)*.20, 0),
                    (min_angle + (total_angle)*.20, 0),
                    (min_angle + (total_angle)*.20, 0),
                    (max_angle, thetadot3[index_max_angle]),
                    (max_angle+2, 0)])
    # get x and y vectors
    x = points[:,0]
    y = points[:,1]

    # calculate polynomial

    f = Polynomial.fit(x,y,6)

    rec_x_ideal = np.linspace(x[0], x[-1], resampled_drive_angles)
    stroke_dict['recx'] = rec_x_ideal

    rec_y_ideal = f(rec_x_ideal)
    stroke_dict['recy'] = rec_y_ideal

    # slip points 

    points = np.array([(max_angle, 0),
                    (max_angle+.5, -7),
                    (max_angle+1, -12),
                    (max_angle+1.6, -5),
                    (max_angle+2, 0)])
    # get x and y vectors
    x = points[:,0]
    y = points[:,1]

    # calculate polynomial

    f = Polynomial.fit(x,y,4)

    b_slip_x_ideal = np.linspace(x[0], x[-1], resampled_drive_angles)
    b_slip_y_ideal = f(b_slip_x_ideal)

    stroke_dict['slipx'] = b_slip_x_ideal
    stroke_dict['slipy'] = b_slip_y_ideal


    stroke_dict['idealx'] = [drive_x_ideal, rec_x_ideal, b_slip_x_ideal]
    stroke_dict['idealy'] = [drive_y_ideal, rec_y_ideal, b_slip_y_ideal]
    stroke_dict['drive_f'] = drive_f

    return stroke_dict


def svd_module(elite, npts, chosen_seat=None, chosen_range = None):
    if chosen_range:
        start, end = chosen_range
        numstrokes = end-start +1
    else:
        numstrokes = elite.numstrokes
    if chosen_seat:
        numseats = 1
        cols = [chosen_seat+1, chosen_seat+9, chosen_seat+17]
        snapshots3 = np.zeros((len(cols)*npts, numstrokes))
        for s in range(numstrokes):
            dat = elite.resample_stroke(s, cols, npts)
            snapshots3[:,s] = dat.flatten()
    else:
        numseats = 8
        cols = np.array([1, 9, 17])
        snapshots3 = np.zeros((len(cols)*npts, numseats*numstrokes))
        for s in range(numstrokes):
            for seat in range(numseats):
                cols += seat
                ind = s*numseats + seat
                dat = elite.resample_stroke(s, cols, npts)
                snapshots3[:,ind] = dat.flatten()
                cols = np.array([1, 9, 17])
    mean3 = snapshots3.sum(1) / (numseats * numstrokes)
    # snapshots3 -= mean3[:,np.newaxis]
    u3, sig3, vt3 = None, None, None #np.linalg.svd(snapshots3, full_matrices=False)
    return {'mean': mean3, 'snapshots': snapshots3, "svd_vals": (u3, sig3, vt3)}



def plot_vector(vec, ax, label=None, label2 = None, color = "#084594", transparency = None, suppress_power = False, legend_title = ""):
    # split a vector into (theta, thetadot) and plot
    npts = len(vec) // 2
    t = np.linspace(0, 1, npts+1)[:-1]
    theta = vec[::3]
    thetadot = vec[1::3]
    thetaq = vec[2::3]
    
    
    if not suppress_power:
        if label:
            ax[0].line(x = theta, y = thetadot, legend_label = label, line_color = color, line_join = 'bevel', line_width = 2)
            ax[0].legend.background_fill_alpha = 0.2
            ax[0].legend.location = "center"
            ax[0].legend.label_text_font_size = '8pt'
            ax[0].legend.spacing = 2
            ax[0].legend.title = legend_title
            ax[0].xaxis.axis_label='Gate Angle °'
            ax[0].yaxis.axis_label='Gate Force (N)'
        else:
            ax[0].line(x = theta, y = thetadot, line_color = color, line_join = 'bevel', line_width = 2)
            ax[0].xaxis.axis_label='Gate Angle °'
            ax[0].yaxis.axis_label='Gate Force (N)'


    if label2:
        ax[1].line(x = theta, y = thetaq, legend_label = label2, line_color = color, line_join = 'bevel', line_width = 2)
        ax[1].legend.background_fill_alpha = 0.2
        ax[1].legend.location = "center"
        ax[1].legend.label_text_font_size = '8pt'
        ax[1].legend.spacing = 2
        ax[1].legend.title = legend_title

    else:
        ax[1].line(x = theta, y = thetaq, line_color = color, line_join = 'bevel', line_width = 2)


    ax[1].xaxis.axis_label='Gate Angle °'
    ax[1].yaxis.axis_label='Gate Angle Veclocity'




def plot_single(vec, ax, label=None, color = "#084594"):
    # split a vector into (theta, thetadot) and plot
    npts = len(vec) // 2
    t = np.linspace(0, 1, npts+1)[:-1]
    theta = vec[::3]
    thetadot = vec[1::3]
    thetaq = vec[2::3]

    mathDict = helperMath(theta, thetadot, t)

    ideal_stroke = ideal_stroke_module(theta, thetadot)

    ax[1].multi_line(xs = ideal_stroke['idealx'], ys = ideal_stroke['idealy'], line_join = 'bevel', line_width = 2, legend_label="Ideal Stroke")

    # w = np.zeros(N)

    idx_min_angle = min(range(len(theta)), key=theta.__getitem__)
    idx_max_angle = idx_min_angle
    while thetadot[idx_max_angle] > 0:
        idx_max_angle +=1
    

    lowz = []
    lowzw = []
    lowxz = []

    patches = []

    larger = ideal_stroke['drive_f'](theta[idx_min_angle]) > thetadot[idx_min_angle]

    for i in range(idx_min_angle, idx_max_angle):
        if larger and ideal_stroke['drive_f'](theta[i]) > thetadot[i]:
            lowz.append(ideal_stroke['drive_f'](theta[i]))
            lowzw.append(thetadot[i])
            lowxz.append(theta[i])
        elif not larger and ideal_stroke['drive_f'](theta[i]) <= thetadot[i]:
            lowzw.append(ideal_stroke['drive_f'](theta[i]))
            lowz.append(thetadot[i])
            lowxz.append(theta[i])
        else:
            larger = not larger
            lowz.extend(reversed(lowzw))
            lowxz.extend(reversed(lowxz))
            patches += [(lowxz, lowz, larger)]
            if not larger:
                lowzw = [ideal_stroke['drive_f'](theta[i])]
                lowz = [thetadot[i]]
                lowxz = [theta[i]]
            else:
                lowz = [ideal_stroke['drive_f'](theta[i])]
                lowzw = [thetadot[i]]
                lowxz = [theta[i]]


    if len(lowz) >0:
        lowz.extend(reversed(lowzw))
        lowxz.extend(reversed(lowxz))
        patches += [(lowxz, lowz, not larger)]


    for patch in patches:
        if patch[2]:
            ax[1].patch(patch[0], patch[1], color='green', fill_alpha = .2, line_alpha = 0)
        else:
            ax[1].patch(patch[0], patch[1], color='red', fill_alpha = .2, line_alpha = 0)

    # ax[1].patch(highxz, highz, color='green', fill_alpha = .2)

    # ax[1].patch(ideal_stroke['idealx'][0], w, color='green')
    
    if label:
        ax[1].line(x = theta, y = thetadot, legend_label = label, line_color = color, line_join = 'bevel', line_width = 2)
        ax[1].legend.background_fill_alpha = 0.2
        ax[1].legend.location = "center"
        ax[1].legend.label_text_font_size = '8pt'
        ax[1].legend.spacing = 2
        ax[1].xaxis.axis_label='Gate Angle °'
        ax[1].yaxis.axis_label='Gate Force (N)'
    else:
        ax[1].line(x = theta, y = thetadot, line_color = color, line_join = 'bevel', line_width = 2)
        ax[1].xaxis.axis_label='Gate Angle °'
        ax[1].yaxis.axis_label='Gate Force (N)'

    return mathDict



def plot_degree_velocity(vec, ax, label=None, label2 = None, color = "#084594", transparency = None, suppress_power = False, legend_title = ""):
    # split a vector into (theta, thetadot) and plot
    npts = len(vec) // 3
    t = np.linspace(0, 1, npts+1)[:-1]
    theta = vec[::3]
    thetadot = vec[1::3]
    thetaq = vec[2::3]
    
    idx_min_angle = min(range(len(theta)), key=theta.__getitem__)
    idx_max_angle = idx_min_angle
    while thetadot[idx_max_angle] > 0:
        idx_max_angle +=1


    max_force = max(thetadot[idx_min_angle:idx_max_angle])


    start_70 = idx_min_angle+1
    slopes = []

    while thetadot[start_70] < max_force * .7:
        start_70+=1
        slopes += [thetadot[start_70]-thetadot[start_70-1]]

    count = 1
    signed_slopes = []  

    for i in range(1,(idx_max_angle-idx_min_angle)//8 + 1):
        if (slopes[i] >= 0 and slopes[i-1]>=0) or (slopes[i] < 0 and slopes[i-1]<0):
            count+=1
        else:
            signed_slopes+=[posMult(slopes[i-1])*count]
            count = 1

    signed_slopes +=[posMult(slopes[-1]) * count]

    print(signed_slopes)

    dbl_dip_xs = []
    dbl_dip_ys = []

    sidx = 0
    while sidx <= len(signed_slopes)-1:
        if signed_slopes[sidx] < -1:
            so_far = sum(map(abs, signed_slopes[:sidx]))
            so_far_high = abs(signed_slopes[sidx])*2
            dbl_dip_xs += [t[idx_min_angle + so_far], t[idx_min_angle + so_far + so_far_high]]
            dbl_dip_ys += [thetadot[idx_min_angle + so_far], thetadot[idx_min_angle + so_far + so_far_high]]
            break
        else: sidx += 1

    coordinates = []
    annot = None

    if dbl_dip_xs:
        coordinates = list(zip(dbl_dip_xs, dbl_dip_ys))

        print(coordinates)

        plotxs=[coordinates[0][0], coordinates[0][0], coordinates[1][0], coordinates[1][0]]
        plotys=[coordinates[0][1]-5, coordinates[0][1]+2, coordinates[1][1]+2, coordinates[1][1]-5]
        annot = PolyAnnotation(
            fill_color="red",
            fill_alpha=0.3,
            xs=plotxs,
            ys = plotys)
        lab = Label(
            x=coordinates[0][0]-npts/2000,
            y=(coordinates[0][1] + coordinates[1][1] + 1)/2,
            angle = (plotys[2]-plotys[1])/(plotxs[2]-plotxs[1]), 
            x_units='data', y_units = 'data', 
            text='Sloppy\nBladework')



    end_70 = idx_max_angle

    while thetadot[end_70] < max_force * .7:
        end_70-=1

    span_start_70 = Span(location=t[start_70],
                    dimension='height', line_color='blue',
                    line_dash='dashed', line_width=3)

    span_label = Label(
        x=t[start_70]-npts/2000,
        y=min(thetadot),
        x_units='data', y_units = 'data', 
        text='70%\nPeak\nForce')

    ax[0].add_layout(span_label)


    span_end_70 = Span(location=t[end_70],
                    dimension='height', line_color='blue',
                    line_dash='dashed', line_width=3)

    span_label = Label(
        x=t[end_70]-npts/2000,
        y=min(thetadot),
        x_units='data', y_units = 'data', 
        text='70%\nPeak\nForce')

    ax[0].add_layout(span_label)

    ax[0].line(x = [t[start_70],t[end_70]], y = [thetadot[start_70], thetadot[end_70]], line_color = "red", line_dash = "dashed", line_width = 3)

    span_label = Label(
        x=t[start_70 + (end_70-start_70)//2]-npts/2000,
        y=thetadot[end_70],
        x_units='data', y_units = 'data', 
        text='Time\n@70%')

    ax[0].add_layout(span_label)


    drive_start = Span(location=t[idx_min_angle],
                        dimension='height', line_color='green',
                        line_dash='dashed', line_width=3)

    span_label = Label(
        x=t[idx_min_angle]-npts/2000,
        y=min(thetadot),
        x_units='data', y_units = 'data', 
        text='Catch')

    ax[0].add_layout(span_label)

    drive_end = Span(location=t[idx_max_angle],
                    dimension='height', line_color='green',
                    line_dash='dashed', line_width=3)

    span_label = Label(
        x=t[idx_max_angle]-npts/2000,
        y=min(thetadot),
        x_units='data', y_units = 'data', 
        text='Finish')

    ax[0].add_layout(span_label)
    ax[0].add_layout(drive_start)
    ax[0].add_layout(drive_end)
    ax[0].add_layout(span_start_70)
    ax[0].add_layout(span_end_70)




    if label:
        ax[0].line(x = t, y = thetadot, legend_label = label, line_color = color, line_join = 'bevel', line_width = 2)
        ax[0].legend.background_fill_alpha = 0.2
        ax[0].legend.location = "top_left"
        ax[0].legend.label_text_font_size = '8pt'
        ax[0].legend.spacing = 2
        ax[0].legend.title = legend_title
        ax[0].xaxis.axis_label='Time (normalized)'
        ax[0].yaxis.axis_label='Gate Force (N)'
    else:
        ax[0].line(x = t, y = thetadot, line_color = color, line_join = 'bevel', line_width = 2)
        ax[0].xaxis.axis_label='Time (normalized)'
        ax[0].yaxis.axis_label='Gate Force (N)'

    if annot:
        ax[0].add_layout(annot)
        ax[0].add_layout(lab)

    if label2:
        ax[1].line(x = t, y = theta, legend_label = label2, line_color = color, line_join = 'bevel', line_width = 2)
        ax[1].legend.background_fill_alpha = 0.2
        ax[1].legend.location = "top_left"
        ax[1].legend.label_text_font_size = '8pt'
        ax[1].legend.spacing = 2
        ax[1].legend.title = legend_title

    else:
        ax[1].line(x = t, y = theta, line_color = color, line_join = 'bevel', line_width = 2)

    span_label = Label(
        x=t[idx_min_angle]-npts/2000,
        y=min(theta),
        x_units='data', y_units = 'data', 
        text='Catch')

    ax[1].add_layout(span_label)

    span_label = Label(
        x=t[idx_max_angle]-npts/2000,
        y=min(theta),
        x_units='data', y_units = 'data', 
        text='Finish')

    ax[1].add_layout(span_label)

    ax[1].add_layout(drive_start)
    ax[1].add_layout(drive_end)

    ax[1].xaxis.axis_label='Time(Normalized)'
    ax[1].yaxis.axis_label='Gate Angle'

