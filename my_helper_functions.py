

## Class used for storage of test variables - Seeing here as example, but most of them will be re-assigned by the user input
import time
import ipaddress

class testVars: pass


class Step:
    def __init__(self):
        self.counter = 1.0

    def add(self):
        int_part = int(self.counter)
        if self.counter - int_part > 0 :
           self.counter = int_part
           self.counter += 1
           result = self.counter
        else:            
           result = self.counter
           self.counter += 1 
        return result

    def add_minor(self):
        self.counter += 0.1
        return self.counter


def compare_numbers(num1 : float , num2: float , thresholdNum = 0.99) -> bool:
    threshold = thresholdNum
    difference = abs(num1 - num2)
    avg = (num1 + num2) / 2
    percent_difference = difference / avg
    
    if percent_difference <= (1 - threshold):
        return True
    else:
        return False


def get_network_address(ip_cidr):
    # Create an IPv4 network object
    network = ipaddress.ip_network(ip_cidr, strict=False)
    # Return the network address in the form of a string
    return str(network.network_address) + '/' + str(network.prefixlen)


def stop_ixia_traffic(session):
    session.Traffic.Stop()
    traff_running = True
    start_time = time.time()  # Record the start time
    timeout = 60  # Timeout limit in seconds (1 minute)

    while traff_running:
        # Check if the timeout has been reached
        if time.time() - start_time > timeout:
            return False

        currentTrafficState = session.Traffic.State
        session.info('Currently traffic is in ' + currentTrafficState + ' state')

        if currentTrafficState in ['notRunning', 'stopped', 'unapplied']:
            traff_running = False
        else:
            time.sleep(3)
        time.sleep(5)

    return True