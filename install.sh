#!/bin/bash

# BOK: I think this is for their LED driver as well, probably not needed.
echo "Enable SPI"
sudo sed -i 's/\#dtparam=spi=on/dtparam=spi=on/g' /boot/config.txt

# BOK: Not needed, due to their LED drivers. I tried using NeoPixel instead.
# echo "Disable Audio"
# sudo sed -i 's/\dtparam=audio=on/#dtparam=audio=on/g' /boot/config.txt
# sudo echo blacklist snd_bcm2835 > /etc/modprobe.d/raspi-blacklist.conf # FIXME: defensive


# BOK: A lot of this not needed, mostly for building drivers I don't use.
# Install dependencies
sudo apt-get update
sudo apt-get upgrade
sudo apt-get -y install git vim python3-pip gcc make build-essential
sudo apt-get -y install libatlas-base-dev 
sudo apt-get -y install python-dev swig scons # for building WS2811 drivers

# BOK: This requires the script to be run from /home/pi

echo "Install application"
test -d moonboard || git clone https://github.com/8cH9azbsFifZ/moonboard.git
cd moonboard
git pull

# BOK: CHeck these...
# Installing python dependencies
pip3 install -r requirements.txt
sudo pip3 install -r requirements.txt 
# pip3 uninstall -y -r requirements.txt # uninstall

# BOK: Also installs ./scripts/run.sh which is the main moonboard app?
# BOK: Disabled while I re-write the main app
# echo "Install service"
# cd /home/pi/moonboard/services
# sudo ./install_service.sh moonboard.service 
# cd /home/pi/moonboard


echo "Install DBUS service"
sudo cp /home/pi/moonboard/ble/com.moonboard.conf /etc/dbus-1/system.d
sudo cp /home/pi/moonboard/ble/com.moonboard.service /usr/share/dbus-1/system-services/


echo "Prepare logfiles"
sudo touch /var/log/moonboard
sudo chown pi:pi /var/log/moonboard
sudo chown pi:pi /var/log/moonboard


# BOK: THis uses serviced to install the dbus files
# BOK: Partly duplicates the "Install DBUS service" stage below, partly doing extra work.
# Prepare phase 2 to run at boot
sudo cp --verbose /home/pi/moonboard/services/moonboard-install.service /lib/systemd/system/moonboard-install.service
sudo chmod 644 /lib/systemd/system/moonboard-install.service
sudo systemctl daemon-reload
sudo systemctl enable moonboard-install.service

echo "Restarting in 5 seconds to finalize changes. CTRL+C to cancel."
sleep 1 > /dev/null
printf "."
sleep 1 > /dev/null
printf "."
sleep 1 > /dev/null
printf "."
sleep 1 > /dev/null
printf "."
sleep 1 > /dev/null
printf " Restarting"
sudo shutdown -r now
