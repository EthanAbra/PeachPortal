import collections
from numpy import trapz
from numpy.polynomial import Polynomial
import numpy as np
from bokeh.models import Span, Label, LabelSet, PolyAnnotation
from bokeh.plotting import figure
from bokeh.palettes import Oranges9
from bokeh.models import Label, PolyAnnotation, Text, Range1d, ColumnDataSource
import warnings

def posMult(num):
    if num >= 0:
        return 1
    else:
        return -1

def double_dip_module(theta3, thetadot3):
    index_min_angle = min(range(len(theta3)), key=theta3.__getitem__)

    index_max_angle = index_min_angle
    while thetadot3[index_max_angle] > 0:
        index_max_angle +=1

    resampled_drive_angles = index_max_angle-index_min_angle
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
            # print(so_far_high)
            dbl_dip_xs += [theta3[index_min_angle + so_far], theta3[index_min_angle + so_far + so_far_high]]
            dbl_dip_ys += [thetadot3[index_min_angle + so_far], thetadot3[index_min_angle + so_far + so_far_high]]
            sidx += 2
        else: sidx += 1


    coords = list(zip(dbl_dip_xs, dbl_dip_ys))
        
    return coords

def workModule(theta3, thetadot3):

    time_resamp = np.linspace(0, 1, len(theta3)+1)[:-1]
    index_min_angle = min(range(len(theta3)), key=theta3.__getitem__)

    index_max_angle = index_min_angle
    while thetadot3[index_max_angle] > 0:
        index_max_angle +=1
    drive_y_old = thetadot3[index_min_angle:index_max_angle]

    drive_time_old = time_resamp[index_min_angle:index_max_angle]
    pct_50 = len(drive_time_old)//2
    
    first_half = trapz(drive_y_old[:pct_50], drive_time_old[:pct_50])/100
    second_half = trapz(drive_y_old[pct_50:], drive_time_old[pct_50:])/100
    return (first_half, second_half)
    

def helperMath(theta3, thetadot3):

    retDict = collections.defaultdict()

    index_min_angle = min(range(len(theta3)), key=theta3.__getitem__)

    index_max_angle = index_min_angle
    while thetadot3[index_max_angle] > 0:
        index_max_angle +=1


    retDict['work_first_half'], retDict['work_second_half'] = workModule(theta3, thetadot3)
    return retDict


def ideal_stroke_module(theta3, thetadot3):
    index_min_angle = min(range(len(theta3)), key=theta3.__getitem__)

    index_max_angle = index_min_angle
    while thetadot3[index_max_angle] > 0:
        index_max_angle +=1

    resampled_drive_angles = index_max_angle-index_min_angle
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
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
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

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

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

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        f = Polynomial.fit(x,y,4)

    b_slip_x_ideal = np.linspace(x[0], x[-1], resampled_drive_angles)
    b_slip_y_ideal = f(b_slip_x_ideal)

    stroke_dict['slipx'] = b_slip_x_ideal
    stroke_dict['slipy'] = b_slip_y_ideal


    stroke_dict['idealx'] = [drive_x_ideal, rec_x_ideal, b_slip_x_ideal]
    stroke_dict['idealy'] = [drive_y_ideal, rec_y_ideal, b_slip_y_ideal]
    stroke_dict['drive_f'] = drive_f

    return stroke_dict




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

    mathDict = helperMath(theta, thetadot)

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



def plot_degree_velocity(vec, ax, label=None, label2 = None, color = "#084594", legend_title = ""):
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

    # print(signed_slopes)

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
    sloppy_bladework = False
    if dbl_dip_xs:
        coordinates = list(zip(dbl_dip_xs, dbl_dip_ys))
        sloppy_bladework = True

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
        x_units='data', y_units = 'data', text_color = "blue",
        text='70%\nPeak\nForce')

    ax[0].add_layout(span_label)


    span_end_70 = Span(location=t[end_70],
                    dimension='height', line_color='blue',
                    line_dash='dashed', line_width=3)

    span_label = Label(
        x=t[end_70]-npts/2000,
        y=min(thetadot),
        x_units='data', y_units = 'data', text_color = "blue", 
        text='70%\nPeak\nForce')

    ax[0].add_layout(span_label)

    span_70_pct = Span(location=t[idx_min_angle + round((idx_max_angle-idx_min_angle)*.7)],
                    dimension='height', line_color='pink',
                    line_dash='dashed', line_width=3)

    ax[0].add_layout(span_70_pct)


    span_label = Label(
        x=t[idx_min_angle + round((idx_max_angle-idx_min_angle)*.7)]-npts/2000,
        y=max(thetadot)-10,
        x_units='data', y_units = 'data', text_color = "pink", 
        text='70%\nDrive\nLength')

    ax[0].add_layout(span_label)



    drive_start = Span(location=t[idx_min_angle],
                        dimension='height', line_color='green',
                        line_dash='dashed', line_width=3)

    span_label = Label(
        x=t[idx_min_angle]-npts/2000,
        y=min(thetadot),
        x_units='data', y_units = 'data', text_color = "green",
        text='Catch')

    ax[0].add_layout(span_label)

    drive_end = Span(location=t[idx_max_angle],
                    dimension='height', line_color='green',
                    line_dash='dashed', line_width=3)

    span_label = Label(
        x=t[idx_max_angle]-npts/2000,
        y=min(thetadot),
        x_units='data', y_units = 'data', text_color = "green",
        text='Finish')

    ax[0].add_layout(span_label)
    ax[0].add_layout(drive_start)
    ax[0].add_layout(drive_end)
    ax[0].add_layout(span_start_70)
    ax[0].add_layout(span_end_70)

    tail_off = True
    if t[idx_min_angle + round((idx_max_angle-idx_min_angle)*.7)] < t[start_70]:
        tail_off = False
    



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
        ax[2].line(x = t, y = theta, legend_label = label2, line_color = color, line_join = 'bevel', line_width = 2)
        ax[2].legend.background_fill_alpha = 0.2
        ax[2].legend.location = "top_left"
        ax[2].legend.label_text_font_size = '8pt'
        ax[2].legend.spacing = 2
        ax[2].legend.title = legend_title

    else:
        ax[2].line(x = t, y = theta, line_color = color, line_join = 'bevel', line_width = 2)

    span_label = Label(
        x=t[idx_min_angle]-npts/2000,
        y=min(theta),
        x_units='data', y_units = 'data', 
        text='Catch')

    ax[2].add_layout(span_label)

    span_label = Label(
        x=t[idx_max_angle]-npts/2000,
        y=min(theta),
        x_units='data', y_units = 'data', 
        text='Finish')

    ax[2].add_layout(span_label)

    ax[2].add_layout(drive_start)
    ax[2].add_layout(drive_end)

    ax[2].xaxis.axis_label='Time(Normalized)'
    ax[2].yaxis.axis_label='Gate Angle'

    return sloppy_bladework, tail_off



def plot_double_dip(bx, coordinates):
    polygons = []
    for coordIdx in range(0,len(coordinates), 2):
        plotxs=[coordinates[coordIdx][0], coordinates[coordIdx][0], coordinates[coordIdx+1][0], coordinates[coordIdx+1][0]]
        plotys=[coordinates[coordIdx][1]-5, coordinates[coordIdx][1]+2, coordinates[coordIdx+1][1]+2, coordinates[coordIdx+1][1]-5]
        polygons += [(
            PolyAnnotation(
            fill_color="red",
            fill_alpha=0.3,
            xs=plotxs,
            ys = plotys
        ), 
        Label(
            x=coordinates[coordIdx][0],
         y=(coordinates[coordIdx][1] + coordinates[coordIdx+1][1] + 1)/2,
         angle = (plotys[2]-plotys[1])/(plotxs[2]-plotxs[1]), 
         x_units='data', y_units = 'data', 
         text='Disconnect')
         )]

    for polygon, polylabel in polygons:
        bx[0].add_layout(polygon)
        bx[0].add_layout(polylabel)

def generate_figs(analysis = True):
    ax = [figure(background_fill_color="#fafafa"), figure(background_fill_color="#fafafa")]
    bx = [figure(background_fill_color="#fafafa"), figure(background_fill_color="#fafafa")]
    cx = [figure(background_fill_color="#fafafa"), figure(background_fill_color="#fafafa")]
    dx = None
    if analysis:
        dx = [figure(background_fill_color="#fafafa"), figure(background_fill_color="#ffffff", x_range = Range1d(0,100), y_range = Range1d(0,100), tools =[]), figure(background_fill_color="#fafafa")]
        dx[1].xaxis.major_tick_line_color = None  
        dx[1].xaxis.minor_tick_line_color = None  
        dx[1].yaxis.major_tick_line_color = None  
        dx[1].yaxis.minor_tick_line_color = None  
        dx[1].xaxis.major_label_text_font_size = '0pt'  
        dx[1].yaxis.major_label_text_font_size = '0pt'  
        dx[1].outline_line_width = 7
        dx[1].outline_line_alpha = 0.3
        dx[1].outline_line_color = "navy"
        dx[1].grid.visible = False
        dx[1].xaxis.visible = False 
        dx[1].yaxis.visible = False 

        title  = Label(x=39, y=90, text='Analysis', text_color = '#00008b', text_font_size = "32px")

        dx[1].add_layout(title)
    return ax,bx,cx,dx
    






def render_analysis(dx, analysis_pts):
    x = [5]*len(analysis_pts)

    y = list(np.linspace(5,85,len(analysis_pts)))[::-1]


    source = ColumnDataSource(dict(x=x, y=y, text = analysis_pts))    

    title  = Text(x='x', y='y', text='text', text_color = '#00008b', text_font_size = "20px")

    dx[1].add_glyph(source, title)
    

def gen_overall_plots(piece_num, athleteMap):
    ax = []
    for i in range(len(athleteMap[int(piece_num)])):
        ax.append(figure(background_fill_color="#fafafa"))

    ax.append(figure(background_fill_color="#fafafa", sizing_mode="stretch_width"))
    return ax

def tech_tree(early_build, max_force_pct, sloppy_bladework, tail_off, double_dips, sudden_accel, late_placement, work_first, work_second):
    analysis_pts = []
    
    if max_force_pct <= 33:
        analysis_pts.append("Max Force Percentage is too early.")
    elif max_force_pct > 40:
        analysis_pts.append("Max Force Percentage is too late")
        analysis_pts.append("Try springing off the footplate at the catch")
        early_build = False
    else:
        if work_first > work_second:
            analysis_pts.append("Max Force Percentage looks good!!.")
        else:
            analysis_pts.append("Try to anticipate the front end better.")
            analysis_pts.append("Roll off the stretchers")
            
            
    if early_build and double_dips and tail_off:
        analysis_pts.append("You are likely using too much body at the front end")
        analysis_pts.append("Try a quicker leg drive and push through the heels")
    elif early_build and tail_off:
        analysis_pts.append("Try to leverage your body better.")
        analysis_pts.append("Fully extend your hips late in the drive")
        analysis_pts.append("Gather more bend at the catch.")
        analysis_pts.append("Connect through the foot stretchers with your heels")
    elif early_build and not tail_off:
        analysis_pts.append("Nice work quickly acheiving and maintaining force!")

    late_prep = sudden_accel and late_placement

    if not early_build and late_prep:
        analysis_pts.append("You are likely lunging at the catch")
        analysis_pts.append("Try to prepare the body earlier.") 
        analysis_pts.append("Catch through your fingertips, not shoulders")
    if not early_build and not late_prep:
        analysis_pts.append("Get those legs down faster! ")
        analysis_pts.append("Try to focus on changing direction quicker.")

    if sloppy_bladework:
        analysis_pts.append("Your blade is entering before accelerating to stern")
        analysis_pts.append("Try not to \"pull\" the handle at the catch.")
        analysis_pts.append("Relax and elongate your upper body")
    return analysis_pts


def gen_athlete_dict(athleteMap):
    athDict = {}
    for pieceIdx in range(len(athleteMap)):
        for paidx, piece_athlete in enumerate(athleteMap[pieceIdx]):
            in_dict = athDict.get(piece_athlete,None)
            if in_dict is not None:
                pl = in_dict
                pl.append((pieceIdx, paidx))
                athDict[piece_athlete] = pl
            else:
                athDict[piece_athlete] = [(pieceIdx, paidx)]
    return athDict


def mean_and_ideal(seatMean, analysis, ax, bx, dx):
    mathDict = plot_single(seatMean, ax, color = "#FFA500", label= "Actual Stroke")
    
    plot_vector(seatMean, label= 'Overall Mean Stroke', label2 = 'Overall Mean Recovery', ax=bx)
    if not analysis:
        return
    sloppy_bladework, tail_off = plot_degree_velocity(seatMean, ax=dx, label= 'Overall Mean Stroke', label2 = 'Overall Mean Recovery')
    return mathDict,sloppy_bladework,tail_off


    
    

def splits(elite, seat_num, cx):
    split = elite.get_rating_chunks()
    for idx, one_split in enumerate(split):
        plot_splits(elite, seat_num, cx, idx, one_split)
        
def plot_individual(npts, piece_num, elite, colors, athleteMap, ax, stroke_nums, average_aper_data, peep):
    theta3 = []
    thetadot3 = []
    for s in range(1, elite.numstrokes):
        dat3 = elite.resample_stroke(s, [0, peep+1,peep+1+elite.numseats], npts)
        theta3 += [dat3[:,1]]
        thetadot3 += [dat3[:,2]]
        
    plot_superimposed(elite.numseats, average_aper_data, elite.numstrokes, peep, colors, ax, theta3, thetadot3, peep)        
    ax[-1].line(x = stroke_nums, y = elite.aper_data[:,1+peep][:-1], line_color = colors[peep], line_join = 'bevel', line_width = 2, legend_label=athleteMap[int(piece_num)][peep])
            
def recovery_and_mean(elite, seat_num, bx):
    boat_mean = mean_module(elite, 100)

    plot_vector(boat_mean, color = "#ba34eb", label = 'Boat Mean Stroke', suppress_power=True, label2='Boat Mean Recovery', ax = bx)

    if seat_num !=elite.numseats-1: # if not stroke seat
        stroke_mean = mean_module(elite, 100, 7)
        plot_vector(stroke_mean, color = "#30d93e", suppress_power=True, label2='Stroke Mean Recovery', ax = bx)
        

def resample_and_superimposed(elite, render, seat_num, npts, colors, ax, average_aper_data):
    theta3 = []
    thetadot3 = []
    time_resamp = []
    for s in range(1, elite.numstrokes):
        dat3 = elite.resample_stroke(s, [0, seat_num+1,seat_num+1+elite.numseats], npts)
        time_resamp += [dat3[:,0]]
        theta3 += [dat3[:,1]]
        thetadot3 += [dat3[:,2]]
    num_strokes = elite.numstrokes
    plot_superimposed(elite.numseats, average_aper_data, num_strokes, seat_num, colors, ax, theta3, thetadot3, render=render)
        
        
def athlete_span(athlete_list, colors):
    totalspan = ""
    for pieceIdx, piece in enumerate(athlete_list):
        spanner = '<span>Piece ' + str(pieceIdx+1) + ": </span>"
        for idx, athlet in enumerate(piece):
            spapender = ", </span>" if idx<len(athlete_list)-1 else "</span>"
            spanner += '<span style=color:' +  colors[idx] + '>Seat ' +str(idx+1) + \
                ": "+ athlet + spapender
        if pieceIdx > 0:
            totalspan += "<br>"
        totalspan += spanner
    return totalspan


        
def plot_boat_pwrinfo(elite, ax, stroke_nums, average_aper_data):
    boat_pow = elite.get_boat_power()
    
    ax[-1].line(x = stroke_nums, y = boat_pow, line_join = 'bevel', line_width = 2, legend_label = "Average Boat Power")

    label = Label(x=elite.numstrokes//2-10, y=np.max(boat_pow), x_units='data', y_units = 'data', 
        text='Average Boat:\nPower: %.2f N\nSlip: %.2f°\nWash: %.2f°\nMax Force: %.2f%%' %
        (np.mean(average_aper_data[1:1+elite.numseats]),np.mean(average_aper_data[1+2*elite.numseats:1+3*elite.numseats]), np.mean(average_aper_data[1+4*elite.numseats:1+5*elite.numseats]), np.mean(average_aper_data[1+15*elite.numseats:1+16*elite.numseats])),
            border_line_color='black', border_line_alpha=.5,
            background_fill_color='#fafafa', background_fill_alpha=0, text_color = '#0096FF')
            
    
    ax[-1].add_layout(label)
    ax[-1].legend.click_policy="hide"
    
    
def plot_splits(elite, seat_num, cx, idx, one_split):
    split_mean = mean_module(elite, 100, seat_num, (one_split[0], one_split[1]))
    plot_vector(split_mean, ax=cx, color=Oranges9[idx], legend_title = "Stroke over Time",
        label="Stroke %d-%d, avg s/m: %.1f, avg W: %.1fW" 
        %(one_split[0]+1, one_split[1]+1, 
        elite.get_average_aper_data(one_split)[1+16*elite.numseats], 
        elite.get_average_aper_data(one_split)[1+seat_num]), 
        label2 = "Stroke %d-%d, avg Max Force: %.2f%%" 
        %(one_split[0]+1, one_split[1]+1, 
        elite.get_average_aper_data(one_split)[1+15*elite.numseats+seat_num]))
    
    
    
def mean_module(elite, npts, chosen_seat=None, chosen_range = None):
    if chosen_range:
        start, end = chosen_range
        numstrokes = end-start +1
    else:
        numstrokes = elite.numstrokes
    if chosen_seat is not None:
        divisor = 1
        cols = [chosen_seat+1, chosen_seat+1+elite.numseats, chosen_seat+1+2*elite.numseats]
        snapshots = np.zeros((len(cols)*npts, numstrokes))
        for s in range(numstrokes):
            dat = elite.resample_stroke(s, cols, npts)
            snapshots[:,s] = dat.flatten()
    else:
        divisor = elite.numseats
        cols = np.array([1, 1+elite.numseats, 1+2*elite.numseats])
        snapshots = np.zeros((len(cols)*npts, elite.numseats*numstrokes))
        for s in range(numstrokes):
            for seat in range(elite.numseats):
                cols += seat
                ind = s*elite.numseats + seat
                dat = elite.resample_stroke(s, cols, npts)
                snapshots[:,ind] = dat.flatten()
                cols = np.array([1, 1+elite.numseats, 1+2*elite.numseats])
    return snapshots.sum(1) / (divisor * numstrokes)
    
    
def dips_and_late(numseats, seat_num, bx, average_aper_data, seatMean):
    theta = seatMean[::3]
    thetadot = seatMean[1::3]
    
    double_dips = double_dip_module(theta, thetadot)
    
    plot_double_dip(bx, double_dips)
    late_placement = False

    if seat_num < numseats-1:
        look_ahead_avg = np.mean(average_aper_data[1+5*numseats+seat_num+1:numseats*6+1])/200 # all seats ahead of seat_num catch time
        if look_ahead_avg-average_aper_data[1+5*numseats+seat_num] <= .01 or average_aper_data[1+5*numseats+7]- average_aper_data[1+5*numseats+seat_num] <= .01:
            late_placement = True
    return double_dips,late_placement    


def gen_indv_response(numseats, seat_num, meta, internal, piece_num, multi_piece, piece_loop, ad):
    response = ""
    if not internal:
        if multi_piece:
            response = '<div id = "piecelist" hx-swap-oob = "true"> <ul class="navbar-nav mr-auto">'
            for piece, num, s_num in piece_loop:
                response +=  '<li class="nav-item">'  
                response += '<button class="btn btn-outline-info'
                if num == piece_num:
                    response += ' active" role = "button" aria-pressed = "true'
                response +=  '" hx-post= "/workoutseat?w=' + str(meta['_id']) + '&s=' 
                response += str(s_num) + '&piece=' + str(num)
                if ad:
                    response+= '&ad=1'
                response += '" hx-target = "#raw">' + str(piece) + '</button>' 
                response += '</li>'
            response += '</ul> </div>'
        response += '<div id = "seatlist" hx-swap-oob = "true"> <ul class="navbar-nav mr-auto">'
        response +=  '<li class="nav-item">'  
        response += '<button class="btn btn-outline-primary'
        if multi_piece: 
            response +=  '" hx-post= "/workoutoverall?w=' + str(meta['_id']) + '&piece=' + str(piece_num) + '" hx-target = "#raw">' + "Overall View" + '</button>' 
        else:
            response +=  '" hx-post= "/workoutoverall?w=' + str(meta['_id']) + '" hx-target = "#raw">' + "Overall View" + '</button>' 
        response += '</li>'
        for num in range(numseats):
            response +=  '<li class="nav-item">'  
            response += '<button class="btn btn-outline-primary'
            if num == seat_num:
                response += ' active" role = "button" aria-pressed = "true'
            if not multi_piece:
                response +=  '" hx-post= "/workoutseat?w=' + str(meta['_id']) + '&s='+str(num)
                if ad:
                    response+= '&ad=1'
                response += '" hx-target = "#raw">' + "Seat " + str(num+1) + " Details" + '</button>'
            else:
                response +=  '" hx-post= "/workoutseat?w=' + str(meta['_id']) + '&s='+str(num) + '&piece=' + str(piece_num)
                if ad:
                    response+= '&ad=1'
                response += '" hx-target = "#raw">' + "Seat " + str(num+1) +  " Details" + '</button>' 
            response += '</li>'
        response += '</ul> </div>'
    return response

def gen_overall_response(numseats, internalId, piece_num, meta, multi_piece):
    response = ""
    if not internalId:
        if multi_piece:
            response = '<div id = "piecelist" hx-swap-oob = "true"> <ul class="navbar-nav mr-auto">'
            for num, piece in enumerate(meta['piece_list']):
                response +=  '<li class="nav-item">'  
                response += '<button class="btn btn-outline-info'
                if str(num) == piece_num:
                    response += ' active" role = "button" aria-pressed = "true'
                response +=  '" hx-post= "/workoutoverall?w=' + str(meta['_id']) + '&piece=' + str(num) + '" hx-target = "#raw">' + piece + '</button>' 
                response += '</li>'
            response += '</ul> </div>'

        
        response += '<div id = "seatlist" hx-swap-oob = "true"> <ul class="navbar-nav mr-auto"> <li class="nav-item"> <button class="btn btn-outline-primary active" role = "button" aria-pressed = "true'
        if multi_piece: 
            response +=  '" hx-post= "/workoutoverall?w=' + str(meta['_id']) + '&piece=' + piece_num + 'ad=1" hx-target = "#raw">' + "Overall View" + '</button>' 
        else:
            response +=  '" hx-post= "/workoutoverall?w=' + str(meta['_id']) + 'ad=1" hx-target = "#raw">' + "Overall View" + '</button>' 
        response += '</li>'
        for num in range(numseats):
            response +=  '<li class="nav-item">'  
            response += '<button class="btn btn-outline-primary"'
            if not multi_piece:
                response +=  ' hx-post= "/workoutseat?w=' + str(meta['_id']) + '&s='+str(num) + 'ad=1" hx-target = "#raw">' + "Seat " + str(num+1) + " Details" + '</button>'
            else:
                response +=  ' hx-post= "/workoutseat?w=' + str(meta['_id']) + '&s='+str(num) + '&piece=' + piece_num + '&ad=1" hx-target = "#raw">' + "Seat " + str(num+1) +  " Details" + '</button>' 
            response += '</li>'
        response += '</ul> </div>'
    return response

    
def plot_superimposed(numseats, average_aper_data, num_strokes, seat_num, colors, ax, theta3, thetadot3, peep = 0, render = None):
    ax[peep].multi_line(xs = theta3, ys = thetadot3, line_alpha = max(-0.001111*num_strokes + 0.2722, .02), color=colors[seat_num], legend_label = 'All Strokes Superimposed', line_join = 'bevel', line_width = 2)
    ax[peep].xaxis.axis_label='Gate Angle °'
    ax[peep].yaxis.axis_label='Gate Force (N)'
    if render is None:
        text='Average:\nPower: %.2f N\nSlip: %.2f°\nWash: %.2f°\nMax Force: %.2f%%' %(average_aper_data[1+seat_num],
                                                                                      average_aper_data[1+2*numseats+seat_num], 
                                                                                      average_aper_data[1+4*numseats+seat_num], 
                                                                                      average_aper_data[1+15*numseats+seat_num])
    else:
        text = ''
        if 'power' in render:
            text += 'Average\nPower: %.2f N\n' % average_aper_data[1+seat_num]
        if 'slip' in render:
            text += 'Slip: %.2f°\n' % average_aper_data[1+2*numseats+seat_num]
        if 'wash' in render:
            text += 'Wash: %.2f°\n' % average_aper_data[1+4*numseats+seat_num]
        if 'percentage' in render:
            text += 'Max Force: %.2f%%' % average_aper_data[1+15*numseats+seat_num]
    label = Label(x=np.min(theta3), y=np.min(thetadot3), x_units='data', y_units = 'data', 
        text=text,
            border_line_color='black', border_line_alpha=.5,
            background_fill_color='#fafafa', background_fill_alpha=0, text_color = '#0096FF')
    ax[peep].add_layout(label)
    


