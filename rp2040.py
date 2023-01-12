#! /usr/bin/python3
import time
import serial
import json
import re
import subprocess
import pyudev
import pprint
import os
import psutil

rpi_VID = "2e8a"
rpi_boot_PID = "0003"
rpi_probe_PID = "0004"
rpi_cdc_uart_PID = "000a"

def usb_reset():
    context = pyudev.Context()
    for device in context.list_devices(ID_BUS='usb'):
        # Find all appropriate RP2040 based devices
        if device.get('ID_VENDOR_ID') == rpi_VID and device.get('DEVTYPE') == 'usb_device':
            device_name = device.get('DEVNAME')
            print("RP2040 device found at: " + str(device_name))
            subprocess.run(["sudo", "/home/pi/PirateMIDI/build-station/usbreset", device_name])

def usb_powercycle():
    subprocess.run(["sudo", "uhubctl", "-l", "1-1", "-a", "off", "-r", "10"])
    time.sleep(0.05)
    subprocess.run(["sudo", "uhubctl", "-l", "1-1", "-a", "on", "-r", "10"])

def enter_bootloader():
    context = pyudev.Context()
    device_found = False
    for device in context.list_devices(ID_BUS='usb'):
        # Find all appropriate RP2040 based devices
        if device.get('ID_VENDOR_ID') == rpi_VID and device.get('ID_MODEL_ID') == rpi_cdc_uart_PID:
            # Find the CDC device under 'tty'
            if(device.get('SUBSYSTEM') == 'tty'):
                device_found = True
                device_name = device.get('DEVNAME')
                print("RP2040 device found at: " + str(device_name))

                # Enter the bootloader
                print("Forcing rp2040 into bootloader") 
                ser = serial.Serial(
                        port=device_name,
                        baudrate=1200,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS,
                        timeout=0.5
                    )
                ser.isOpen()
                return
        if device.get('ID_VENDOR_ID') == rpi_VID and device.get('ID_MODEL_ID') == rpi_boot_PID:
            print("Device is already in bootloader mode")
            return
    # If no suitable device was found
    if device_found == False:
        print("No available devices found")

def list_all():
    context = pyudev.Context()
    for device in context.list_devices(ID_BUS='usb'):
        # Find all appropriate RP2040 based devices
        if device.get('ID_VENDOR_ID') == rpi_VID:
            pprint.pprint(dict(device.properties)) 

# Finds the status of a connected RP2040 device
# Returns 'BOOT' for bootloader, 'RUNNING' for running firmware, and 'NONE' if no device is found
def get_status():
    context = pyudev.Context()
    for device in context.list_devices(ID_BUS='usb'):
        # Check for bootloader device
        if device.get('ID_VENDOR_ID') == rpi_VID and device.get('ID_MODEL_ID') == rpi_boot_PID:
            return "BOOT"
        if device.get('ID_VENDOR_ID') == rpi_VID and device.get('ID_MODEL_ID') == rpi_cdc_uart_PID:
            return "RUNNING"
    return "NONE"

# Returns the disk device name of the rp2040 boot drive
def get_disk():
    context = pyudev.Context()
    device_found = False
    for device in context.list_devices(ID_BUS='usb'):
        # Find all appropriate RP2040 based devices
        if device.get('ID_VENDOR_ID') == rpi_VID and device.get('ID_MODEL_ID') == rpi_boot_PID:
            if device.get('DEVTYPE') == 'partition':
                device_found = True
                return device.get('DEVNAME')
    if device_found == False:
        print("No suitable device was found")
        return "NONE"
            

def flash_uf2(file_name):
    # Check for a valid uf2 file extension
    if file_name.endswith(".uf2") == False:
        print("Invalid file format")
        return
    if not os.path.exists(file_name):
        print("File does not exist")
        #return

    enter_bootloader()
    dev_name = get_disk()

    # Check the RP2040 isn't already mounted
    partitions = psutil.disk_partitions()
    disk_p = None
    for p in partitions:
        if p.device == dev_name:
            disk_p = p
            print("Device already mounted")

    # If the device is not already mounted, mount it
    if disk_p is None:
        print("Mounting device...")
        subprocess.run(["sudo", "mkdir", "/media/rp2040"])
        subprocess.run(["sudo", "mount", dev_name, "/media/rp2040"])

    output = subprocess.run(["sudo", "cp", file_name, "/media/rp2040"], capture_output=True)
    if output.returncode != 0:
        print("An error occured. Copying file to mounted volume as not successful")
        return
    print("Flashing complete! Unmounting drive")
    # Once the file transfer has completed, unmount the drive and cleanup
    subprocess.run(["sudo", "umount", "-l", "/media/rp2040"])
    subprocess.run(["sudo", "rmdir", "/media/rp2040"])
    
    
    
