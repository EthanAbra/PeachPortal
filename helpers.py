import datetime
# from structures import Piece

def autoTitle(pieces):
    """ takes a list of pieces, e.g. ['2000m', '2000m', '1000m']
        and converts it to a pretty title -> '2x2000m, 1000m']
    """
    if len(pieces) == 1: return pieces[0]

    count = 0
    out = ''
    last = pieces[0]
    for i in range(len(pieces)):
        if pieces[i] == last:
            count += 1
            last = pieces[i]
        else:
            if count == 1:
                out += last + ', '
                last = pieces[i]
            else:
                out += str(count)+'x'+ last + ', '
                count = 0
                last = pieces[i]

    if count == 1:
        out += str(count)+'x'
        final = ', '.join((out + last).split(',')[:-1])
    else:
        final =  str(count) + 'x'+last

    return final


def averageOfOne(meters, time):
    """ Computes a split from meters and time """
    try:
        h = time.hour
        m = time.minute
        s = time.second
        ms = time.microsecond
    except Exception as e:
        print(str(e), ': in averageSplit. Was <time> a datetime.time?')
    finally:
        d = (meters / 500)
        totalSec = (((h * 3600) + (m * 60) + s ) / d)

        splitMin =  int(totalSec // 60)
        splitSec = int((totalSec % 60) // 1)
        splitTenth = int(((totalSec % 60) % 1) * 1000000)

        out = datetime.time(minute=splitMin, second=splitSec, microsecond=splitTenth)
        return out


def averageOfAll(scores):
    """ Computes the average split of a list of Pieces """
    totalMeters = 0
    totalSec = 0
    for piece in scores:
        totalMeters += piece.meters
        totalSec += piece.time.minute * 60 + piece.time.second

    m, s = divmod(totalSec, 60)
    h, m = divmod(m, 60)

    totalTime = datetime.time(hour=h, minute=m, second=s)

    return averageOfOne(totalMeters, totalTime)



# if __name__ == "__main__":
        # p1 = ['2000m']
        # p2 = ['2000m','2000m','2000m']
        # p3 = ['4000m', '3000m','2000m', '2000m']

        #print(autoTitle(p1))
        #print(autoTitle(p2))
        #print(autoTitle(p3))
#     time6k = datetime.time(minute=20, second=32, microsecond=500000)
#     distance6k = 6000
#     ## should be 1:42.5

#     time30min = datetime.time(minute=30)
#     distance30min = 8492
#     # should be 1:45.9

#     print(averageOfOne(distance6k, time6k))
#     print(averageOfOne(distance30min, time30min))

#     workout = [Piece(2000, datetime.time(minute=7, second=0)), Piece(2000, datetime.time(minute=7, second=0)), Piece(2000, datetime.time(minute=6, second=30))]
#     print(averageOfAll(workout))