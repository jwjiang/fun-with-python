#! /usr/bin/env python

__author__ = 'jjiang'

import sys
import os
import time
import signal
import threading
import re
import subprocess
import pexpect
from subprocess import PIPE, Popen

connected = '(List of devices attached)(\\s)+(emulator-(\\d)+)(\\s)+(device)'
package_dict = ''

def get_dict(namefile):
    return open(namefile)

def uninstall(package_name):
    # uninstall the apk
    shell = pexpect.spawn(''.join(['adb uninstall ', package_name]))
    print(''.join([':: adb uninstall ', package_name]))
    shell.expect('Success\\r\\r\\n', timeout=60)
    shell.kill(signal.SIGINT)
    return

def pull_pcap(apkname, shell):
    # pull the packet capture file
    download = subprocess.Popen(''.join(['adb pull /sdcard/', apkname[:len(apkname)-4], '.pcap', ' ./captures']),
                                shell=True, universal_newlines=True)
    print(''.join([':: adb pull /sdcard/', apkname[:len(apkname)-4], '.pcap', ' ']))
    time.sleep(10)
    shell.sendline('rm /sdcard/*.pcap')
    print(':: rm /sdcard/*.pcap')
    return

def do_stuff(apkname, package_name, pathname):
    # installapk = subprocess.Popen(''.join(['adb install ', apkname]), shell=True, universal_newlines=True)

    shell = pexpect.spawn(''.join(['adb install ', pathname]))
    print(''.join([':: adb install ', apkname]))
    # wait for apk to install
    shell.expect('Success\\r\\r\\n', timeout=120)
    shell.kill(signal.SIGINT)

    shell = pexpect.spawn('adb shell')
    time.sleep(1)

    # start tcpdump
    shell.sendline(''.join(['tcpdump -n -s 0 -w /sdcard/', apkname[:len(apkname)-4], '.pcap', ' &']))
    print(''.join([':: ', 'tcpdump -n -s 0 -w /sdcard/', apkname[:len(apkname)-4], '.pcap', ' &']))
    time.sleep(1)

    # launch app using package name
    shell.sendline(''.join(['monkey -p ', package_name, ' --pct-majornav 0', ' --throttle 30',
                            ' -c android.intent.category.LAUNCHER 200']))
    print(''.join([':: ', 'monkey -p ', package_name, ' --pct-majornav 0', ' --throttle 30',
                   '-c android.intent.category.LAUNCHER 200']))

    # wait some time... ideally use monkey to randomize some interaction here
    time.sleep(60)

    # kill tcpdump
    shell.sendline('ps tcpdump')
    print(':: ps tcpdump')
    time.sleep(1)
    shell.readline()
    ps_lines = shell.readline().rstrip()
    tcpdump_pid = ps_lines.split(' ')
    for string_part in tcpdump_pid[1:]:
        if string_part != ' ':
            tcpdump_pid = string_part

    shell.sendline(''.join(['kill ', tcpdump_pid]))
    print(''.join([':: kill ', tcpdump_pid]))
    time.sleep(1)

    # uninstall the apk and pull the packet capture file
    uninstall_thread = threading.Thread(target=uninstall(package_name))
    pcap_thread = threading.Thread(target=pull_pcap(apkname, shell))
    uninstall_thread.start()
    pcap_thread.start()
    while uninstall_thread.is_alive() or pcap_thread.is_alive():
        time.sleep(0.5)

    shell.kill(signal.SIGINT)

def start(namefile):
    # read the csv of package names
    global package_dict
    package_dict = get_dict(namefile)

    # make folder to hold pcaps
    captures = os.path.abspath('./captures')
    if not os.path.exists(captures):
        os.makedirs(captures)
    startadb = subprocess.Popen('adb start-server', shell=True, universal_newlines=True, stdout=PIPE)
    print(startadb.communicate())
    emulator = os.system('/usr/share/android-sdk/sdk/tools/emulator -avd santoku -no-boot-anim &')


    devices = subprocess.Popen('adb devices', shell=True, universal_newlines=True, stdout=PIPE)
    output = devices.communicate()[0]
    regex_match = re.match(connected, output)

    while not regex_match:
        print('Waiting for device to connect...')
        time.sleep(5)
        devices = subprocess.Popen('adb devices', shell=True, universal_newlines=True, stdout=PIPE)
        output = devices.communicate()[0]
        regex_match = re.match(connected, output)

    print('Device connected! Waiting 30 seconds...')
    time.sleep(30)

    for line in package_dict:
        array = line.split(',')
        apkname = array[0]
        print('apkname: ' + apkname)
        package_name = array[1]
        print('pkg name: ' + package_name)
        pathname = array[2]
        print('pathname: ' + pathname)
        do_stuff(apkname, package_name, pathname)

        monkeythread = threading.Thread(target=do_stuff(apkname, package_name, pathname))
        monkeythread.start()
        while monkeythread.is_alive():
            time.sleep(0.5)

def main():
    # check for path as argument
    if len(sys. argv) < 2:
        print('Please specify the location of the .csv containing package names (generated by apkshark.py)')
        sys.exit(-1)
    elif len(sys.argv) > 2:
        print('Please specify only the directory of the .csv file')
        sys.exit(-1)
    else:
        namefile = sys.argv[1]

    if not os.path.isabs(namefile):
        namefile = os.path.abspath(namefile)
        print(namefile)
    if not os.path.isfile(namefile):
        print(namefile)
        print('File is invalid.')
        sys.exit(-1)

    start(namefile)

if __name__ == "__main__":
    main()