fd = open("showstart2.txt")
line = fd.readline()
while not line.strip().startswith("Estimated"):
    line = fd.readline()
lineSplit = line.split(" ")
print lineSplit[5]
