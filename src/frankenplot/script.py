''' a Script Block represents a single script command to move to a 
location and to do a scan represented by a string '''
class Scan(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.scan = 'default'

    def ToString(self):
        ans = 'mabs smx ' + str(self.x) + '\n'
        ans+= 'mabs smy ' + str(self.y) + '\n'
        ans+= 'scan ' + self.scan + '\n'

        return ans

''' a script represents a structured series of commands to be given to the mover command line utility '''
class Script(object):
    def __init__(self):
	self.default_name = ""
        self.scans = []

    ''' add a new blank block to the list of blocks '''
    def AddNewScan(self):
        scan = Scan(0,0)
	scan.scan = self.default_name

        self.scans.append(scan)

        return scan

    ''' get all of the script blocks int he script '''
    def GetScans(self):
        return self.scans

    def DeleteScan(self, scan):
	scans.remove(scan)

    ''' clear all scans from this script '''
    def ClearAllScans(self):
        self.scans = []
	return self.AddNewScan()

    ''' advance the target block toward the end of the list '''
    def MoveScanDown(self,target):
        success = False

        for index, scan in enumerate(self.scans):
            if index == len(self.scans) - 1:
                break
            if scan == target:
                success = True
                self.scans[index] = self.scans[index+1]
                self.scans[index+1] = target

        return success

    ''' advance the target block toward the beginning of the list '''
    def MoveScanUp(self,target):
        success = False

        for index, scan in enumerate(self.scans):
            if scan == target:
                if index == 0:
                    break
                success = True
                self.scans[index] = self.scans[index-1]
                self.scans[index-1] = target

        return success

    ''' write out the actual script to a string as a series of commands from each block '''
    def ToString(self):
        answer = ''

        for scan in self.scans:
            answer += scan.ToString()

        return answer

    def ChoiceList(self):
	answer = []

	for index, scan in enumerate(self.scans):
	    answer.append(str(index) + ": " +
	       scan.scan + " (" + str(scan.x) + ", " + str(scan.x) + ")")

	return answer

