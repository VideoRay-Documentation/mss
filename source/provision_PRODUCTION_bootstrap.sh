#!/usr/bin/env bash

#Top level script to get general provisioning scripts

#The provisioning process bootstrap requires the following steps:
#    Elevate to root if needed
#    Erase any local debs with the same name so that there are not naming collisions when installing
#    Pull the deb(s) from the ftp server
#    Install the deb(s)
#    Run the proper provision script


while getopts ':n' option; do
  case "$option" in
    n) SKIP_PROVISION_TASKS="true"   
       ;;   
  esac
done

USERNAME=$(logname)

INSTALL_DIR="vrinstall"
FILENAME="videoray-production-tools*.deb"

#insure that the vr_install dir is there for any bits we copy down
mkdir $INSTALL_DIR -p

#Check if run as root
if [[ $EUID -ne 0 ]] 
then
    #need to elevate to root
    echo "INFO: Elevating to root"
    #elevate to root
    sudo $0 $*
else
    #change to the install dir so we dont pollute with all the files we download
    cd $INSTALL_DIR

    #erase any local versions so that we can install using *
    rm $FILENAME -f

    echo "INFO: Getting provisioning from ftp.videoray.com"
    wget ftp.videoray.com:/install/$FILENAME --user production_tool --password 2qMWZvmSxVRjTFgh     

    echo "INFO: installing: "
    dpkg -i $FILENAME


    if [ -z "$SKIP_PROVISION_TASKS" ]  
    then
        echo "INFO: Running provisioning for PRODUCTION"
        /opt/videoray/PRODUCTION/provisioning/provision.py PRODUCTION/production.config #2>&1 | tee -a /tmp/vr_error_production_provision.txt
    fi

    #make sure that the original owner can delete any artifacts we download
    chown $USERNAME *
fi