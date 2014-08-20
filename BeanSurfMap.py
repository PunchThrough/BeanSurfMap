# Surf Report Parser
# Written by Colin Karpfinger
# Uses a LightBlue Bean to display report in LEDs on a surf-map
# http://punchthrough.com/bean
# http://punchthrough.com/bean/examples/surf-report-notifier/
# https://github.com/PunchThrough/BeanSurfMap
import datetime
import urllib2
import simplejson as json
import time
import serial
from decimal import *
import config

daysInReport = 6
readingsToAverage = 4
earliestSurfHour=5 #ignore tide times earlier than 5am
latestSurfHour=21   #and later than 9pm
conditionTypes=["","flat", "very poor", "poor","poor to fair","fair","fair to good","good","very good","good to epic","epic"]

lowTides=[]
highTides=[]

tideUrl="http://api.wunderground.com/api/APIKEY/tide/settings/q/CA/94019.json"
tideUrl=tideUrl.replace("APIKEY",config.wundergroundApiKey)
webreq = urllib2.Request(tideUrl)
opener = urllib2.build_opener()
f = opener.open(webreq)
fstr = f.read()
fstr = fstr.strip() #remove any whitespace in start/end
tideReport=json.loads(fstr)	

for eachDay in tideReport["tide"]["tideSummary"]:
	if int(eachDay["date"]["mday"])==datetime.datetime.now().day and int(eachDay["date"]["hour"])>earliestSurfHour and int(eachDay["date"]["hour"])<latestSurfHour: #only add tide times during the day
		if eachDay["data"]["type"]=="Low Tide":
			lowTides.append(eachDay)
		elif eachDay["data"]["type"]=="High Tide":
			highTides.append(eachDay)

if len(lowTides)>0:

	#print "low tides: "+str(self.lowTides)
	print "Low Tide at: "+str(lowTides[0]["date"]["hour"])+":"+str(lowTides[0]["date"]["min"])
if len(highTides)>0:
	#print "Number of high tides: "+str(len(self.highTides))
	#print "high tides: "+str(self.highTides)
	print "High Tide at: "+str(highTides[0]["date"]["hour"])+":"+str(highTides[0]["date"]["min"])



class SurfSpot:
	baseUrl="http://api.surfline.com/v1/forecasts/0000?resources=surf,analysis&days=6&getAllSpots=false&units=e&interpolate=false&showOptimal=false"
	heightsMax=[]
	heightsMin=[]

	surflineUrl=""
	tideUrl=""
	surflineRegionalUrl=""
	surflineName=""
	textConditions=[]
	spotName =""
	todaysLocalCondition=0
	regionalConditions=[]
	def __init__(self, spotName, spotID, regionalID):
		self.spotName = spotName
		self.surflineUrl=self.baseUrl.replace("0000",spotID)
		self.surflineRegionalUrl=self.baseUrl.replace("0000",regionalID)

		self.heightsMax=[]
		self.heightsMin=[]
		self.regionalConditions=[]
	def getReport(self):
		webreq = urllib2.Request(self.surflineUrl, None, {'user-agent':'syncstream/vimeo'})
		opener = urllib2.build_opener()
		f = opener.open(webreq)
		fstr = f.read()
		fstr = fstr.replace(')','') #remove closing )
		fstr = fstr.replace(';','') #remove semicolon
		fstr = fstr.strip() #remove any whitespace in start/end
		rep = json.loads(fstr)

		webreq = urllib2.Request(self.surflineRegionalUrl, None, {'user-agent':'syncstream/vimeo'})
		opener = urllib2.build_opener()
		f = opener.open(webreq)
		fstr = f.read()
		fstr = fstr.replace(')','') #remove closing )
		fstr = fstr.replace(';','') #remove semicolon
		fstr = fstr.strip() #rem3ove any whitespace in start/end
		regionalReport=json.loads(fstr)


		self.surflineName=rep["name"]
		for day in range(0,daysInReport):
			daysAvgMax=0
			daysAvgMin=0
			self.regionalConditions.append(conditionTypes.index(regionalReport["Analysis"]["generalCondition"][day]))
			if len(rep["Surf"]["surf_max"])==6:
				for reading in range(0,readingsToAverage):
					if daysAvgMax==0:
						daysAvgMax=rep["Surf"]["surf_max"][day][reading]
					else:
						daysAvgMax=(daysAvgMax+rep["Surf"]["surf_max"][day][reading])/2.0
					if daysAvgMin==0:
						daysAvgMin=rep["Surf"]["surf_min"][day][reading]
					else:
						daysAvgMin=(daysAvgMin+rep["Surf"]["surf_min"][day][reading])/2.0
			else: #don't need to average, since the report doesn't have multiple readings. 
				daysAvgMax=rep["Surf"]["surf_max"][0][day]
				daysAvgMin=rep["Surf"]["surf_min"][0][day]
 
			self.heightsMax.append(Decimal(daysAvgMax).quantize(Decimal('1'), rounding=ROUND_UP))
			self.heightsMin.append(Decimal(daysAvgMin).quantize(Decimal('1'), rounding=ROUND_UP))
	def printReport(self):
		reportText=self.spotName+" Forecast: "
		for day in range(0,daysInReport):
			reportText=reportText+str(self.heightsMin[day])+"-"+str(self.heightsMax[day])+" ft. "+str(conditionTypes[self.regionalConditions[day]])+"  "
		print reportText
	
bolinas = SurfSpot("Bolinas", "5091","2949")
lindamar = SurfSpot("Linda Mar", "5013","2957")
mavericks = SurfSpot("Mavericks", "4152", "2957")
oceanBeach = SurfSpot("Ocean Beach", "4127", "2957")
fourMile = SurfSpot("Four Mile", "2958", "2958")
steamerLane = SurfSpot("Steamer Lane", "4188", "2958")
pleasurePoint = SurfSpot("Pleasure Point","4190", "2958")

spots = [lindamar,bolinas,mavericks,oceanBeach,fourMile,steamerLane,pleasurePoint] #same order as the surf artwork

ser = serial.Serial('/tmp/tty.LightBlue-Bean', 9600, timeout=0.25)
spotindex=0
for spot in spots:
	sendBytes=[]
	spot.getReport()
	sendBytes.append(spotindex)
	sendBytes.append(0)
	sendBytes.append(daysInReport)
	for dayindex in range(0,daysInReport):
		sendBytes.append(spot.heightsMax[dayindex])
	sendBytes.append(1)
	for dayindex in range(0,daysInReport):
		sendBytes.append(spot.regionalConditions[dayindex])
	buff=[chr(i) for i in sendBytes]
	if ser:
		ser.write(buff)
		ser.flush()
	else:
		print "Serial port not open."
	time.sleep(.1)
	spot.printReport()
	spotindex+=1


#now send tides 
#[0,0,6,1,2,3,4,5,5,1,4,5,5,7,5,5]
#[4,2,length of tides(2), low tide hour, low tide min, high tide hour, high tide min, 0,0, remainder zeros ]

sendBytes=[]
sendBytes.append(4)  #starts at 4th neopixel array	
sendBytes.append(2)  #tide iD is 2
sendBytes.append(len(lowTides)+len(highTides))
if (len(lowTides)>0):
	sendBytes.append(int(lowTides[0]["date"]["hour"]))
	sendBytes.append(int(lowTides[0]["date"]["min"]))
else:
	sendBytes.append(0)
	sendBytes.append(0)
if (len(highTides)>0):
	sendBytes.append(int(highTides[0]["date"]["hour"]))
	sendBytes.append(int(highTides[0]["date"]["min"]))
else:
	sendBytes.append(0)
	sendBytes.append(0)
while len(sendBytes)< 16:
	sendBytes.append(0) #fill reaminder with zeros 

buff=[chr(i) for i in sendBytes]
ser.write(buff)
ser.flush()

# sendBytes=[0,3,1,11]
# while len(sendBytes)< 16:
# 	sendBytes.append(0) #fill reaminder with zeros 
# buff=[chr(i) for i in sendBytes]
# print buff #debug
# ser.write(buff)
# ser.flush()

time.sleep(.25)
ser.close()
print "Finished."