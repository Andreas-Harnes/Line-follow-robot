from picamera.array import PiRGBArray
from easygopigo3 import EasyGoPiGo3
import picamera
import time
import cv2
import numpy as np
import math
import random

gpg = EasyGoPiGo3()

camera = picamera.PiCamera()
camera.resolution = (160, 120)

time.sleep(0.1)

#Bruker arrayen til å sjekke hendelser i veibanen flere ganger slik at flere feilkilder kan
#filtreres ut
findRadius = 1
prevRoadType = [0, 0, 0]

# Funksjon for å croppe bort deler av bildet
def crop_image(img):

    #Setter hvor bildet skal starte fra toppen
    startRow = int((img.shape[0]) * 0.60)
    #Setter hvor bildet skal slutte fra toppen
    endRow = int(img.shape[0] * 1.00)

    #Setter hvor bildet skal starte fra venstre
    startColumn = int(img.shape[1] * 0.05)
    #Setter hvor bildet skal slutte fra høyre
    endColumn = int(img.shape[1] * 0.95)
    #Har denne horisontale croppen da det virker som venstrefil ikke kan sees med denne når det er 2 filer.
    croppedImage = img[startRow:endRow, startColumn:endColumn]

    return croppedImage


# Funksjon for å finne linjene i bildet og lage et svart/hvitt versjon av det
def binary_image(img):

    imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    #Gjør threshold mindre for å enklere finne linjer.
    threshold1 = 100
    threshold2 = 150
    apertureSize = 3

    binaryPicture = cv2.Canny(imgGray, threshold1,threshold2, apertureSize = apertureSize)

    return binaryPicture


# Funksjon som deler bildet inn i fire kvadranter og kalkulerer verdier i hver av dem basert på svart hvitt bildet
def check_kvad(img):
    imgHeight, imgWidth = img.shape[0:2]
    kvad1 = img[0:int(imgHeight*0.5), 0:int(imgWidth*0.5)]
    kvad2 = img[0:int(imgHeight*0.5), int(imgWidth*0.5):imgWidth]
    kvad3 = img[int(imgHeight*0.5):imgHeight, 0:int(imgWidth*0.5)]
    kvad4 = img[int(imgHeight*0.5):imgHeight, int(imgWidth*0.5):imgWidth]
    kvads = [np.array(kvad1), np.array(kvad2), np.array(kvad3), np.array(kvad4)]

    imgArray = np.array(img)

    #antall hvite pixel i hver kvadrant
    kvadValues = [[],[],[],[]]

    #En array med en array per kvadrant. Legger inn koordinatene (x,y) per punkt
    #som ligger enten på bunnen, toppen, høyre eller venstre av kvadranten. axisCrossings[0] gir deg koordinatene
    #fra første kvadrant på formen (x,y)
    axisCrossings=[]

    leftAxis = []
    rightAxis = []
    topAxis = []
    bottomAxis = []

    roadType = 0

    #Denne løkken regner ut hvor mange hvite pixler er i hver kvadrant
    for x in range(0,4):
        kvadValue = 0
        for y in range(0, len(kvads[x])-1):
            z = 0
            while (z < len(kvads[x][y])):
                if(kvads[x][y][z] > 0):
                    kvadValue += 1
                z += 1
        kvadValues[x].append(kvadValue)

    #Denne løkken finner punkter som er helt i ytterkant (top, bunn, høyre, venstre)
    i = 0
    while(i < len(imgArray)):
        j = 0
        while(j < len(imgArray[i])):
            if(imgArray[i][j] > 0):
                if(i == 1 or i == (len(imgArray)-2) or j == 1 or j == len(imgArray[i])-2):
                    axisCrossings.append([j,i])
            j += 1
        i += 1


    #fjerner punkter i axisCrossings som er nesten helt like da alle punktene burde være nokså distinkte
    i=1
    while i < len(axisCrossings)-1:
        if(abs(axisCrossings[i][0] - axisCrossings[i-1][0]) < 20 and abs(axisCrossings[i][1]-axisCrossings[i-1][1] < 20 )):
            axisCrossings.pop(i)
            i-=1
        i+=1

    kvadHeight, kvadWidth = kvad1.shape[0:2]

    #Disse to løkkene deler ytterpunktene inn i arrayer basert på om det er top, bunn, venstre, eller høyre punktene "treffer"
    #Den første løkken tar x-akse topp og bunn. Den andre tar y-aksen
    for w in range(0, len(axisCrossings)):
        if(axisCrossings[w][0] == (len(imgArray[axisCrossings[w][1]])-2)):
            rightAxis.append(axisCrossings[w])
        elif(axisCrossings[w][0] == 1):
            leftAxis.append(axisCrossings[w])

    for q in range(0, len(axisCrossings)):
        if(axisCrossings[q][1] == len(imgArray) - 2):
            bottomAxis.append(axisCrossings[q])
        elif(axisCrossings[q][1] == 1):
            topAxis.append(axisCrossings[q])

    roadData = [len(topAxis),len(bottomAxis),len(leftAxis),len(rightAxis)]

    roadType = check_road_type(roadData, kvadValues)
    
    print(roadData)
    
    return kvadValues, roadType

# Funksjon for å håndtere rette veier
def straight_road(array):
    leftSide = array[0][0] + array[2][0]
    rightSide = array[1][0] + array[3][0]

    turningModes = [[(10,9.5),(10,9),(10,8.5),(10,8),(10,7.5),(10,7),(10,6.5),(10,6),(10,5.5),(10,5),(10,4.5),(10,4),(10,3.5),(10,3)],[(9.5,10),(9,10),(8.5,10),(8,10),(7.5,10),(7,10),(6.5,10),(6,10),(5.5,10),(5,10),(4.5,10),(4,10),(3.5,10),(3,10)]]

    sideRatio = 0

    stepLength = 1

    if(rightSide == leftSide):
        return(10,10)
    elif(rightSide == 0):
        return turningModes[1][10]
    elif(leftSide == 0):
        return turningModes[0][10]


    if(leftSide > rightSide):
        sideRatio = leftSide/rightSide
        mode = 1
    elif(rightSide > leftSide):
        sideRatio = rightSide/leftSide
        mode = 0

    if(sideRatio < 1.01):
        return (10,10)

    if(sideRatio > 1.01 + stepLength * (len(turningModes[mode])-1)):
        return turningModes[mode][13]

    for i in range(0, len(turningModes[mode]) - 1):
        if(sideRatio <= 1.01 + stepLength * i):
            return turningModes[mode][i]
    return(10,10)

# funksjon for å kjøre riktig i splittende veier
def diverging_road(array):
    return (10,7)

# Funksjon for å sjekke hva vei typen for roboten
def check_road_type(array, kvadValues):
    
    if(array[0] == 2 and array[1] == 2 and array[2] == 0 and array[3] == 0):
        return 0
    elif(array[0] >= 3):
        return 1
    elif(array[3] > 0):
        return 2
    elif(array[0] == 0 and array[1] == 0 and array[2] == 0 and array[3] == 0):
        return 3
    else:
        return 0

# programmets main-funksjon
def run(path):
    image = cv2.imread(path)
    croppedImg = crop_image(image)
    binearyImg = binary_image(croppedImg)
    kvadValues, roadType = check_kvad(binearyImg)
    
    global prevRoadType, findRadius
    #Kjører rett fram
    if(roadType == 0):
        if(prevRoadType[0] == 0 and prevRoadType[1] == 2):
            leftWheel, rightWheel = diverging_road(kvadValues)
            print(prevRoadType, roadType, "\n")
            gpg.steer(leftWheel, rightWheel)
        else:
            leftWheel, rightWheel = straight_road(kvadValues)
            gpg.steer(leftWheel/2, rightWheel/2)
            print(prevRoadType, roadType, "\n")
        #Flytter veitype inn i prevRoadType
            road_memory_handling(roadType)
        
    #Oppdager noe den tror er en splittende vei
    elif(roadType == 1):
        #Hvis forrige veitype er en splittende vei, og veien før der var et kryss vil jeg at det skal sees som et kryss
        if(prevRoadType[2] == roadType):
            #...høyresiden har et høyere antall enn venstresiden vil vi kjøre som det er en rett vei.
            #Dette er fordi jeg mener vi vil kunne følge veien uansett hvis den ser dette, og vil kunne følge den bedre.
            print("Veien deles 2")
            print(prevRoadType, roadType, "\n")
            leftWheel, rightWheel = diverging_road(kvadValues)
            gpg.steer(leftWheel, rightWheel-2)
            time.sleep(0.5)
            prevRoadType = [0, 0, 0]
        #Hvis den forrige veitypen ikke var en splittende vei, men forrige der igjen var det vil vi også registrere det
        #som en splittende vei.
        elif(prevRoadType[1] == roadType):
            print("Veien deles 2")
            print(prevRoadType, roadType, "\n")
            leftWheel, rightWheel = diverging_road(kvadValues)
            gpg.steer(leftWheel, rightWheel-2)
            time.sleep(0.5)
            prevRoadType = [0, 0, 0]
        
        #Hvis vi ser en splittende vei for første gang på 3 bilder vil vi kjøre veldig sakte, og litt mot høyre for å sjekke på nytt.
        else:
            gpg.steer(2,1)
            print(prevRoadType, roadType, "\n")
            road_memory_handling(roadType)
    #Ser et kryss
    elif(roadType == 2):
       #Hvis de to forrige veitypene også var kryss vil vi kjøre litt frem, deretter svinge til høyre.
        if((prevRoadType[2] == 2 and prevRoadType[1] ==  2)):
            print("Kryss registrert 1")
            print(prevRoadType, roadType, "\n")
            gpg.steer(4,4) #Denne må stilles så timingen til krysset er ca riktig
            time.sleep(3)
            gpg.turn_degrees(85)
            gpg.steer(10/2, 10/2)
            prevRoadType = [0, 0, 0]
        #Hvis forrige veitype var et kryss og en av de to foregående også er et kryss vil vi også utføre en "kryssmanøver"
        elif(prevRoadType[0] == 2 and (prevRoadType[2] == 2 or prevRoadType[1] == 2)):
            print("Kryss registrert 2")
            print(prevRoadType, roadType, "\n")
            gpg.steer(4,4) #Denne må stilles så timingen til krysset er ca riktig
            time.sleep(1)
            gpg.turn_degrees(85)
            gpg.steer(10/2, 10/2)
            prevRoadType = [0, 0, 0]
        elif(prevRoadType[1]):
            leftWheel, rightWheel = diverging_road(kvadValues)
            gpg.steer(leftWheel, rightWheel)
            print(prevRoadType, roadType, "\n")
            
            
    
       #Kjører sakte for å sjekke på nytt
        else:
            gpg.steer(2,2)
            print(prevRoadType, roadType, "\n")
            road_memory_handling(roadType)
    #Ser ingen vei
    elif(roadType == 3):
        #Hvis de to foregående veitypen er like vil vi lete etter bannen
        if(prevRoadType[1] == prevRoadType[0] == roadType):
            find(findRadius)
            findRadius += 1
            print(prevRoadType, roadType, "\n")
            road_memory_handling(roadType)
            prevRoadType = [0, 0, 0]
        #Hvis den forrige veitypen var et kryss vil vi utføre en "kryssmanøver"
        elif(prevRoadType[2] == 2):
            print("Kryss registrert 3")
            print(prevRoadType, roadType, "\n")
            gpg.steer(4,4) #Denne må stilles så timingen til krysset er ca riktig
            time.sleep(5.5)
            gpg.turn_degrees(85)
            gpg.steer(10/2, 10/2)
            prevRoadType = [0, 0, 0]
        #Kjører sakte for å sjekke på nytt
        else:
            gpg.steer(2,2)
            findRadius = 1
            print(prevRoadType, roadType, "\n")
            road_memory_handling(roadType)
            
    else:
        print(prevRoadType, roadType, "\n")
        gpg.steer(10/2,10/2)
     
# Funksjon for å håndtere hukommelse for tidligere vei typer
def road_memory_handling(roadType):
    global prevRoadType
    prevRoadType.append((roadType))
    prevRoadType.pop(0)

#Kjører i en voksende spiral. Vokser for hver gang bilen ikke ser noe vei
def find(r):
    if(r <= 50):
        gpg.steer(1+r,100-r)
    elif(r > 50):
        gpg.steer(random.random() * 100, random.random() * 100)
    


while True:
    camera.capture("bilde.jpeg")
    image = cv2.imread("bilde.jpeg")
    run('bilde.jpeg')
