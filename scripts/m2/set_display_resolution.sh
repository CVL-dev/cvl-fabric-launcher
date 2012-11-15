#!/bin/bash 
# James Wettenhall james.wettenhall@monash.edu 2012
 
# Some material copied from Paul McIntosh's /usr/local/desktop/massive_desktop script.
  
# check if we are called correctly and show usage if not 
if [ $# -lt 1 ] ; then
 echo "Usage: set_display_resolution.sh <WIDTHxHEIGHT>"
 echo "  Where:"
 echo "    <WIDTHxHEIGHT> Display resoultion e.g. 1440x900"
 exit 0
 fi
 
# check for .vnc dir and create if necessary 
if [ ! -d ~/.vnc ]; then
 mkdir ~/.vnc
 chmod 700 ~/.vnc
 fi
 
# Check whether ~/.vnc/turbovncserver.conf exists.
# If not, copy it from /etc/turbovncserver.conf
# Note:  We could use : sed 's/SCREEN_RESOLUTION/'"$GEOMETRY"'/' /common/desktop/.vnc/turbovncserver.conf > ~/.vnc/turbovncserver.conf
#            but this method overwrites the user's settings in their ~/.vnc/turbovncserver.conf, 
#            which is not acceptable to some users, based on early feedback from MASSIVE Launcher testers.
if ! [ -f ~/.vnc/turbovncserver.conf ]; then cp /etc/turbovncserver.conf ~/.vnc/; fi

# Check whether ~/.vnc/turbovncserver.conf already contains at least one line containing "$geometry"
if grep -q "\$geometry" ~/.vnc/turbovncserver.conf; then

  # Comment-out the existing (uncommented) $geometry=... lines in ~/.vnc/turbovncserver.conf
  sed -i -e 's/^\s*\$geometry/# $geometry/g' ~/.vnc/turbovncserver.conf
  
  # Delete any existing $geometry=... lines in ~/.vnc/turbovncserver.conf containing the string, "MASSIVE Launcher Display Resolution".
  sed -i -e "/MASSIVE Launcher Display Resolution/d" ~/.vnc/turbovncserver.conf
  
  # Find the last line containing "$geometry" in ~/.vnc/turbovncserver.conf
  LINES_FROM_END=$(tac ~/.vnc/turbovncserver.conf | grep -n "\$geometry" --max-count 1 | awk -F ":" '{print $1}')
  TOTAL_LINES=$(wc -l ~/.vnc/turbovncserver.conf | awk '{print $1}')
  LINE_NUMBER_OF_LAST_GEOMETRY=$(echo "$TOTAL_LINES $LINES_FROM_END - 1 + p" | dc)
 
  # Add the new geometry line
  sed -i $LINE_NUMBER_OF_LAST_GEOMETRY"a\$geometry = \"$1\"; # MASSIVE Launcher Display Resolution" ~/.vnc/turbovncserver.conf

else
  echo "\$geometry = \"$1\"; # MASSIVE Launcher Display Resolution" >> ~/.vnc/turbovncserver.conf
fi

