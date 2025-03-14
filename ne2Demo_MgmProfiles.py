from neEmu2 import neEmu2
import time
import locale
locale.setlocale(locale.LC_ALL, '')  # Use '' for auto, or force e.g. to 'en_US.UTF-8'


def main():

    netEmu2Ip = '10.80.81.8'
    user = 'admin'
    password = 'admin'

    # Topology
    # IxNetwork Port 1 -------- A-1  Network Emulator A-2 -------- IxNetwork Port 2
    port1 = '1' # A-1
    port2 = '2' # A-2
    ## End of Variables

    # Create Network Emulator Object and connect
    print(f"Init Phase -- Establish connection to Network Emulator: {netEmu2Ip}")
    ne2 = neEmu2(netEmu2Ip,user,password)
    print(f"Init Phase -- Checking all alarms are green, meaning green light to continue -- {ne2.checkAlarms()}")

    my_list = ne2.get_list_of_all_profiles(port2)

    for this_profile in my_list:
        ne2.ModifyProfile(port2, this_profile, 'ethernetDelay', {'delay':200.00})



if __name__=='__main__':
    main()
