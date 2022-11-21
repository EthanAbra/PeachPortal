# structures.py
import datetime
from helpers import averageOfOne, averageOfAll, autoTitle

class Workout:
    """ an individual athlete's workout. Composed of an athlete's ID (int) and 
        pieces (list of Piece objects). e.g. a 6x2000m workout by athlete 
        no. 69 is a Workout with id = 69 and scores = [Piece(2000m), Piece(2000m)... x6]"""

    def __init__(self, athleteId, scores, dnf=False, mod=None):
        self.athleteId = athleteId # int : ID of athlete doing the workout
        self.scores = scores # list of Piece objects 
        self.mod = mod
        try:
            if not dnf:
                self.split = averageOfAll(scores) # datetime.time average split
            else:
                self.split = datetime.time(minute=9, second=59, microsecond=900000)
        except Exception as e:
            for score in scores:
                print(score)
            raise e

    """ append a Piece object """
    def addPiece(self, piece):
        self.scores.append(piece)
        if piece.dnf:
            self.dnf = True
            self.split = datetime.time(minute=9, second=59, microsecond=900000)

    def watts(self):
        totalDist = 0
        totalSec = 0
        for piece in self.scores:
            totalSec += piece.time.minute * 60 + piece.time.second + (piece.time.microsecond/1000000)
            totalDist += piece.meters

        pace = totalSec/totalDist
        watts = 2.80 / (pace**3)
        return watts // 1

    def __str__(self):
        s = f'Workout({self.athleteId}, {self.scores}, {self.split})'
        return s

    def __lt__(self,other):
        return self.split < other.split

    def __gt__(self,other):
        return self.split > other.split

    def __eq__(self,other):
        return self.split == other.split

    def __le__(self,other):
        return self.split <= other.split

    def __ge__(self,other):
        return self.split >= other.split


class Piece:
    """ a single unit of erging, e.g. a 2000m or 5:00 piece. """ 
    def __init__(self, meters, time, isDistance, dnf=False):
        try:
            # if did not finish, set this to True
            if meters == 0:
                self.dnf = True
            else:
                self.dnf = dnf

            if not self.dnf:
                self.meters = meters
                self.time = datetime.datetime.combine(datetime.date(2000, 2, 26), time)
                self.split = datetime.datetime.combine(datetime.date(2000, 2, 26), averageOfOne(meters, time))
                # Bool: True if the workout was a distance workout, e.g. a 2000m or 6000m piece. 
                # False if it's a timed piece, e.g. 30:00, 10:00
                self.isDistance = isDistance
            else:
                self.meters = 0
                self.time = datetime.datetime.combine(datetime.date(2000, 2, 26), datetime.time(0,0,0,0))
                self.split = time
                self.isDistance = isDistance
        except Exception as e:
            print(str(e), ': in class Piece. Is the time a datetime.time?')
            return


    def score(self, as_string=False):
        """ returns the 'score', i.e. how the athlete performed over the prescribed
            distance or time, in a tuple with the split. e.g for a 2000m piece, 
            returns (6:20, 1:35), for a 30:00, returns (8411, 1:47)"""
        if self.dnf:
            if as_string:
                return "DNF" , "DNF"
            else:
                return self.meters, self.split

        if not as_string:   
            if self.isDistance:
                return (self.time, self.split)
            else:
                return (self.meters, self.split)
        else:
            splitStr = self.split.strftime('%-M:%S.%f')[:-5]
            if self.isDistance:
                return (self.time.strftime('%-M:%S'), splitStr)
            else:
                return (str(self.meters), splitStr)

    def watts(self):
        try:
            # from https://www.concept2.com/indoor-rowers/training/calculators/watts-calculator : 
            # watts = 2.80/pace**3, where pace = total seconds / meters 
            totalSec = self.time.minute * 60 + self.time.second + (self.time.microsecond/1000000)
            pace = totalSec / self.meters

            watts = 2.80/(pace**3)

            return int(watts//1)
        except ZeroDivisionError as e:
            # caused if DNF
            return 0 


    def __str__(self):
        if self.isDistance:
            s = f"Piece: Distance: {self.meters}, Time: {self.time}"
        else:
            s = f"Piece: Time: {self.time}, Distance: {self.meters}"
        return s


    def __lt__(self,other):
        return self.split < other.split

    def __gt__(self,other):
        return self.split > other.split

    def __eq__(self,other):
        return self.split == other.split

    def __le__(self,other):
        return self.split <= other.split

    def __ge__(self,other):
        return self.split >= other.split
