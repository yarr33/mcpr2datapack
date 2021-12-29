import numpy
import zipfile
import os
import json
import shutil

#have fun using this tool

thisDir = os.getcwd()

def CatmullRomSpline(P0, P1, P2, P3, nPoints = 100, _3d = True):
    P0, P1, P2, P3 = map(numpy.array, [P0, P1, P2, P3])

    alpha = 0.5 / 2
    def tj(ti, Pi, Pj):
        if (_3d):
            xi, yi, zi = Pi
            xj, yj, zj = Pj
            return ((xj-xi)**2 + (yj-yi)**2 + (zj-zi)**2)**alpha + ti
        else:
            xi, yi = Pi
            xj, yj = Pj
            return ((xj-xi)**2 + (yj-yi)**2)**alpha + ti

    t0 = 0
    t1 = tj(t0, P0, P1)
    t2 = tj(t1, P1, P2)
    t3 = tj(t2, P2, P3)
    t = numpy.linspace(t1, t2, nPoints)
    t = t.reshape(len(t), 1)
    
    A1 = (t1-t)/(t1-t0)*P0 + (t-t0)/(t1-t0)*P1
    A2 = (t2-t)/(t2-t1)*P1 + (t-t1)/(t2-t1)*P2
    A3 = (t3-t)/(t3-t2)*P2 + (t-t2)/(t3-t2)*P3
    B1 = (t2-t)/(t2-t0)*A1 + (t-t0)/(t2-t0)*A2
    B2 = (t3-t)/(t3-t1)*A2 + (t-t1)/(t3-t1)*A3
    C = (t2-t)/(t2-t1)*B1 + (t-t1)/(t2-t1)*B2

    return C

def getKeyframe(index):
    keyframe = cameraKeyframes[index]
    properties = keyframe["properties"]
    return (int(round(keyframe["time"] / 50)),properties["camera:position"],properties["camera:rotation"][:2])

def promt(promt):
    result = None
    while result != "y" or result != "n":
        result = input(promt + " (y/n): ").lower()
    return result == "y"

print(""" > Thank you for using this tool! <

========== HOW TO USE ==========
Drag the recording file here, or enter its path. Press enter.
Enter a tag for the entity's selector.

Three files will be created: tick.mcfunction, stop.mcfunction and start.mcfunction.

 > start.mcfunction starts playing the recording. It will create a new scoreboard
  objective, summon an invisible armor stand with a chosen tag, and set the gamemode
  of every player to spectator.

 > stop.mcfunction will stop playing the recording. It will kill the invisible
  armor stand. It's not used in tick.mcfunction, but if you want to use it,
  change "kill" to "function <function name>" in the end of the last line.

 > tick.mcfunction has to run every tick. It updates the position and rotation of
  the armor stand, and kills it at the end. It also updates the objective created in
  start.mcfunction and forces players to spectate the armor stand.
   """)


recordingPath = input("Path: ").replace("\"", "")

while not os.path.exists(recordingPath):
    recordingPath = input(" ! This path does not exist. Please re-enter the path: ").replace("\"", "")

entityTag = input("Enter a custom tag for the armor stand selector: ")

print("\n > Extracting...")

with zipfile.ZipFile(recordingPath, 'r') as zip_ref:
    zip_ref.extractall(os.path.join(thisDir, "tempExtractMcpr"))

print("\n > Reading...")

recordingJsonFile = open(os.path.join(thisDir, "tempExtractMcpr", "timelines.json"))
recordingJson = json.loads(recordingJsonFile.read())
recordingJsonFile.close()

print("\n > Cleaning up...")

shutil.rmtree(os.path.join(thisDir, "tempExtractMcpr"))

cameraKeyframes = recordingJson[""][1]["keyframes"]

print("\n > Processing...")

_, startPosition, startRotation = getKeyframe(0)

tickMcfunctionPlain = ""
startMcfunctionPlain = """tp @s """ + str(startPosition[0]) + """ """ + str(startPosition[1]) + """ """ + str(startPosition[2]) + """ """ + str(startRotation[0]) + """ """ + str(startRotation[1]) + """
scoreboard objectives add """ + entityTag + """_timer dummy
summon armor_stand ~ ~ ~ {Invisible:1b,Tags:[\"""" + entityTag + """\"]}
gamemode spectator @a
execute as @a run spectate @e[tag=""" + entityTag + """,limit=1]"""
stopMcfunctionPlain = """kill @e[tag=""" + entityTag + """,limit=1,type=armor_stand]"""

lastTick = 0

cameraKeyframes[0]["properties"]["camera:rotation"][0] %= 360

for index, keyframe in enumerate(cameraKeyframes[1:]):
    thisKeyframe = getKeyframe(index + 1)
    _, _, rotation = thisKeyframe
    lastKeyframe = getKeyframe(index)
    _, _, lastRotation = lastKeyframe

    rotation[0] = rotation[0] % 360

    delta = rotation[0] - lastRotation[0]

    if (delta > 180):
        rotation[0] -= 360
    elif (delta < -180):
        rotation[0] += 360

    delta = rotation[0] - lastRotation[0]


    cameraKeyframes[index + 1]["properties"]["camera:rotation"][0] = rotation[0]

for index, keyframe in enumerate(cameraKeyframes[:-1]):
    thisKeyframe = getKeyframe(index)
    keyframeTime, position, rotation = thisKeyframe

    nextKeyframe = getKeyframe(index + 1)
    nextKeyframeTime, nextPosition, nextRotation = nextKeyframe

    delta = nextKeyframeTime - keyframeTime
    
    if (index == 0 or index == len(cameraKeyframes) - 2):
        for tick in range(delta):
            percentage = 1 / delta * (tick + 1)
            tickTime = keyframeTime + tick
            tickPosition = list(numpy.add(numpy.array(position) * (1 - percentage), numpy.array(nextPosition) * percentage))
            tickRotation = list(numpy.add(numpy.array(rotation) * (1 - percentage), numpy.array(nextRotation) * percentage))
            tickMcfunctionPlain += "execute as @e[tag=" + entityTag + ",scores={" + entityTag + "_timer=" + str(tickTime) + "}] run tp @s " + str(tickPosition[0]) + " " + str(tickPosition[1]) + " " + str(tickPosition[2]) + " " + str(tickRotation[0]) + " " + str(tickRotation[1]) + "\n"
            lastTick = tickTime
    else:
        lastKeyframe = getKeyframe(index - 1)
        lateKeyframe = getKeyframe(index + 2)

        cameraPositionArray = CatmullRomSpline(lastKeyframe[1], thisKeyframe[1], nextKeyframe[1], lateKeyframe[1], delta)
        cameraRotationArray = CatmullRomSpline(lastKeyframe[2], thisKeyframe[2], nextKeyframe[2], lateKeyframe[2], delta, False)

        for tick in range(delta):
            tickTime = keyframeTime + tick
            tickPosition = cameraPositionArray[tick]
            tickRotation = cameraRotationArray[tick]
            tickMcfunctionPlain += "execute as @e[tag=" + entityTag + ",scores={" + entityTag + "_timer=" + str(tickTime) + "}] run tp @s " + str(tickPosition[0]) + " " + str(tickPosition[1]) + " " + str(tickPosition[2]) + " " + str(tickRotation[0]) + " " + str(tickRotation[1]) + "\n"
        
    lastPosition = position
    lastRotation = rotation
    lastKeyframeTime = keyframeTime

tickMcfunctionPlain += """execute as @e[tag=""" + entityTag + """] at @s run scoreboard players add @s """ + entityTag + """_timer 1
execute as @e[tag=""" + entityTag + """,scores={""" + entityTag + """_timer=..""" + str(lastTick + 1) + """}] as @a run spectate @e[tag=""" + entityTag + """,limit=1]
execute as @e[tag=""" + entityTag + """,scores={""" + entityTag + """_timer=""" + str(lastTick + 1) + """}] run kill"""

print("\n > Saving...")

startMcfunctionFile = open(os.path.join(thisDir, "start.mcfunction"), "w")
startMcfunctionFile.write(startMcfunctionPlain)
startMcfunctionFile.close()

stopMcfunctionFile = open(os.path.join(thisDir, "stop.mcfunction"), "w")
stopMcfunctionFile.write(stopMcfunctionPlain)
stopMcfunctionFile.close()

tickMcfunctionFile = open(os.path.join(thisDir, "tick.mcfunction"), "w")
tickMcfunctionFile.write(tickMcfunctionPlain)
tickMcfunctionFile.close()

print("\n > Files saved:")
print("\n    -", os.path.join(thisDir, "start.mcfunction"))
print("\n    -", os.path.join(thisDir, "stop.mcfunction"))
print("\n    -", os.path.join(thisDir, "tick.mcfunction"))

print("\n\n\n")

os.system("pause")