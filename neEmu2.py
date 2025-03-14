import time
import ipaddress
import requests
import json
import copy
"""
This is a sample class to control Network Emualtor 2 via REST/HTTPs calls
Author: Cris Fernandes - Keysight Technologies 
Version Control: 
   1.0 - Initial Commit 
"""

class neEmu2:
    def __init__(self,ip,user='Admin',password='admin'):
        """
        Description
           Initialze class and gets information for session.

        Parameters
           ip: <str>: '10.10.10.1'
           user: <str>:  'admin' ( default )
           password: <str> 'admin' ( default )

        """
        try:
            checkIp = ipaddress.ip_address(ip)
            self.ip = str(checkIp)
        except:
            self.ip = ''
        assert self.ip, "Empty or Invalid Ip Address"
        self.user = user
        self.password = password
        self.headers = {'content-type': 'application/json'}
        self.banks = False
        response = requests.get("http://" + self.ip + "/api/hw/Banks", auth=(self.user, self.password))
        if str(response.status_code)[0:2] == '20':
            if 'X-Auth-Token' in response.headers:
                self.headers['Authorization'] = f"Token {response.headers['X-Auth-Token']}"
            self.banks = json.loads(response.text)
        assert self.banks, "Empty Banks"
        self.refreshInfo()

    def refreshInfo(self):
        """
        Description:
        Grabs the latest info from Session.
        """
        #self.banks = self._getBanks()
        #assert self.banks, "Empty Banks"
        self.ports = self._getPorts()
        assert self.ports, "No ports found"
        self.port = dict()
        for port in self.ports:
            portId = str(port['logicalId'])
            self.port[portId] = port

    def get_list_of_all_profiles(self,port,exclude_default : bool = True):
        self.refreshInfo()
        retVal_list = ['defaultProfile']
        if exclude_default:
            retVal_list = []
        lProfiles = self.port[port]['profiles']
        for profile in lProfiles:
            retVal_list.append(profile['tag'])
        return retVal_list

    def getProfile(self,port,name):
        """
        Description
           Grabs a profile by exact name on a port.

        Parameters
           port: <str>: '1'
           user: <str>:  'profile 1'

        :return <Profile handle as dic> or False if not found

        """
        self.refreshInfo()
        if name == 'defaultProfile':
            return self.port[port]['defaultProfile']
        lProfiles = self.port[port]['profiles']
        for profile in lProfiles:
            if profile['tag'] == name:
                return profile
        return False

    def disableAllProfiles(self,port=False):
        """
        Description
           Disable all profiles found on a port or all the non-default profiles
        Parameters
           port: <str>: '1' ( default = False )
        """
        if port:
            self.refreshInfo()
            lProfiles = self.port[port]['profiles']
            for profile in lProfiles:
                self.disableProfile(port,profile['tag'])
        else:
            for port in self.ports:
                self.disableAllProfiles(str(port['logicalId']))

    def deleteAllProfiles(self,port=False):
        """
        Description
           Delete all profiles found on a port or all the profiles.

        Parameters
           port: <str>: '1'
        """
        if port:
            self.refreshInfo()
            for profile in self.port[port]['profiles']:
                self.deleteProfile(port,profile['tag'])
            self.clearDefaultProfile(port)
        else:
            for port in self.ports:
                self.deleteAllProfiles(str(port['logicalId']))

    def _getBanks(self):
        """
        Description
           Internal routine to grab Banks information.

        Parameters
           port: <str>: '1'
        """
        banks = requests.get("http://" + self.ip + "/api/hw/Banks", auth=(self.user, self.password))
        if banks.status_code == 200:
            return json.loads(banks.text)
        return False

    def _getPorts(self):
        """
        Description
           Internal routine to grab Banks information.

        Parameters
           port: <str>: '1'
        """
        #ports = requests.get(url= "http://" + self.ip + "/api/hw/Ports", auth=(self.user, self.password))
        ports = requests.get(url="http://" + self.ip + "/api/hw/Ports", headers=self.headers)
        if ports.status_code == 200:
            return json.loads(ports.text)
        return False

    def _getPort(self, port_id):
        """
        Description
           Internal routine to grab port dictionary information.

        Parameters
           port_id: <str>: '1'
        """
        port = requests.get("http://" + self.ip + "/api/hw/Port/" + str(port_id), auth=(self.user, self.password))
        return json.loads(port.text)

    def enableProfile(self, port_id, profile_name, state=True):
        status = False
        self.refreshInfo()
        pFound = self.getProfile(port_id,profile_name)
        if pFound:
            pFound['enabled'] = state
            upload = requests.put("http://" + self.ip + "/api/hw/Port/" + str(port_id), data=json.dumps(self.port[port_id]), auth=(self.user, self.password))
            if upload.status_code == 200:
                status = True
            else:
                print("Failed")
        return status

    def disableProfile(self, port_id, profile_name):
        return self.enableProfile(port_id,profile_name,False)

    def createProfile(self,port_id,profile_name):
        status = False
        self.refreshInfo()
        profExist = self.getProfile(port_id,profile_name)
        assert (profExist is False), "Duplicate Profile found"
        #defaultProfile = self.getProfile(port_id,'defaultProfile')
        #baseProf = copy.deepcopy(defaultProfile)
        defaultProfile = self._getEmptyProfile()
        baseProf = copy.deepcopy(defaultProfile)
        baseProf['tag'] = profile_name
        self.port[port_id]['profiles'].append(baseProf)
        upload = requests.put("http://" + self.ip + "/api/hw/Port/" + str(port_id), data=json.dumps(self.port[port_id]), auth=(self.user, self.password))
        if upload.status_code == 200:
            status = True
        return status

    def dupProfile(self,from_port_id,profile_name,to_port_id):
        status = False
        self.refreshInfo()
        profExist = self.getProfile(to_port_id,profile_name)
        assert (profExist is False), "Duplicate Profile found"
        fromProfile = self.getProfile(from_port_id,profile_name)
        baseProf = copy.deepcopy(fromProfile)
        self.port[to_port_id]['profiles'].append(baseProf)
        upload = requests.put("http://" + self.ip + "/api/hw/Port/" + str(to_port_id), data=json.dumps(self.port[to_port_id]), auth=(self.user, self.password))
        if upload.status_code == 200:
            status = True
        return status

    def addAnythingToProfile(self,port_id,profile_name,attribute,value):
        status = False
        profile = self.getProfile(port_id, profile_name)
        if (isinstance(profile[attribute],list)):
            profile[attribute].append(value)
        elif (isinstance(profile[attribute],dict)):
            profile[attribute] = value
        upload = requests.put("http://" + self.ip + "/api/hw/Port/" + str(port_id), data=json.dumps(self.port[port_id]), auth=(self.user, self.password))
        if upload.status_code == 200:
            status = True
        return status

    def ModifyProfile(self,port_id,profile_name,attribute,value):
        status = False
        profile = self.getProfile(port_id, profile_name)
        if (isinstance(profile[attribute],list)):
            profile[attribute].append(value)
        elif (isinstance(profile[attribute],dict)):
            self.update_dict(profile[attribute],value)
        upload = requests.put("http://" + self.ip + "/api/hw/Port/" + str(port_id), data=json.dumps(self.port[port_id]), auth=(self.user, self.password))
        if upload.status_code == 200:
            status = True
        return status

    def update_dict(self, d, updates):
        """Update dictionary d with key-value pairs from updates if keys exist in d."""
        for key, value in updates.items():
            if key in d:
                d[key] = value
            else:
                raise KeyError(f"Key '{key}' not found in the dictionary.")
        return d

    def addPortPolicer(self,port_id,attribute):
        status = False
        profile = self.port[port_id]['policer']
        for key, value in attribute.items():
            if key in profile:
                profile[key] = value
        upload = requests.put("http://" + self.ip + "/api/hw/Port/" + str(port_id), data=json.dumps(self.port[port_id]), auth=(self.user, self.password))
        if upload.status_code == 200:
            status = True
        return status


    def _getEmptyProfile(self):
        emptyProf = {'dramAllocation': {'mode': 'AUTO', 'fixedSize': 1700352}, \
                     'reorder': {'rdmSel': {'dist': 'PERIODIC', 'interval': 10, \
                     'burstlen': 1, 'stddev': 10.0}, 'reorderByMin': 1, 'reorderByMax': 5, \
                    'enabled': False}, 'rules': [], 'modificationCorrection': \
                    {'enableCorrection': False, 'enableTcp': True, 'enableUdp': True,\
                    'enableRsvp': True, 'correctionMode': 'ALL_PACKETS', 'enableIpv4': True, \
                    'enablePacketCrc': True, 'enabled': False, 'modifications': []}, 'packetDrop': \
                    {'rdmSel': {'dist': 'PERIODIC', 'interval': 10, 'burstlen': 1, 'stddev': 10.0}, \
                    'enabled': False}, 'ethernetDelay': {'delay': 10.0, 'isUncorrelated': False,\
                    'delayMax': 15.0, 'maxNegDelta': 0.1, 'pdvMode': 'NONE', 'delayMin': 5.0, 'units': 'MS',\
                    'maxPosDelta': 0.1, 'enabled': False, 'spread': 1.0}, 'enabled': True, 'duplication': \
                    {'duplicateCountMax': 5, 'rdmSel': {'dist': 'PERIODIC', 'interval': 10, \
                    'burstlen': 1, 'stddev': 10.0}, 'enabled': False, 'duplicateCountMin': 1}, \
                    'policer': {'excessBurstTolerance': 64000, 'excessBitRate': 100, \
                    'commitedBurstTolerance': 64000, 'commitedBitRate': 100, 'enabled': False, \
                    'enableRateCoupling': False}, 'shaper': {'burstTolerance': 64000, 'bitRate': 100,\
                    'enabled': False}, 'accumulateBurst': {'mode': 'MODE_N_OR_T', 'interBurstGap': 0.0, \
                    'waitingTime': 1.0, 'packetNumber': 10, 'enabled': False}, 'ipv4Fragmentation': \
                    {'rdmSel': {'dist': 'PERIODIC', 'interval': 10, 'burstlen': 1, 'stddev': 10.0}, \
                    'ipv4Correction': True, 'honorDoNotFragmentBit': True, 'enabled': False, \
                    'crcCorrection': True, 'mtuSize': 1500}, 'tag': 'emptyProfile', 'filterWarning': ''}
        return emptyProf

    def _getEmptyDefaultProfile(self):
        emptyProf = {'policer': {'excessBurstTolerance': 64000, 'excessBitRate': 100, 'commitedBurstTolerance': 64000,\
                                 'commitedBitRate': 100, 'enabled': False, 'enableRateCoupling': False},\
                     'shaper': {'burstTolerance': 64000, 'bitRate': 100, 'enabled': False},\
                     'accumulateBurst': {'mode': 'MODE_N_OR_T', 'interBurstGap': 0.0, 'waitingTime': 1.0,\
                                         'packetNumber': 10, 'enabled': False}, \
                     'dramAllocation': {'mode': 'AUTO', 'fixedSize': 3400704}, \
                     'ipv4Fragmentation': {'rdmSel': {'dist': 'PERIODIC', 'interval': 10, 'burstlen': 1,\
                                                      'stddev': 10.0}, 'ipv4Correction': True,\
                                           'honorDoNotFragmentBit': True, 'enabled': False, \
                                           'crcCorrection': True, 'mtuSize': 1500}, \
                     'reorder': {'rdmSel': {'dist': 'POISSON', 'interval': 50, 'burstlen': 9, 'stddev': 30.0},\
                                 'reorderByMin': 5, 'reorderByMax': 5, 'enabled': False}, \
                     'modificationCorrection': {'enableCorrection': False,\
                                                'enableTcp': True, 'enableUdp': True, 'enableRsvp': True,\
                                                'correctionMode': 'ALL_PACKETS', 'enableIpv4': True,\
                                                'enablePacketCrc': True, 'enabled': False, 'modifications': []},\
                     'tag': 'defaultProfile', 'packetDrop': {'rdmSel': {'dist': 'PERIODIC', \
                                                                        'interval': 10, 'burstlen': 1, 'stddev': 10.0},\
                                                             'enabled': False}, \
                     'ethernetDelay': {'delay': 350.0, 'isUncorrelated': False, 'delayMax': 15.0, 'maxNegDelta': 0.1,\
                                       'pdvMode': 'NONE', 'delayMin': 5.0, 'units': 'MS', 'maxPosDelta': 0.1,\
                                       'enabled': False, 'spread': 1.0},\
                     'duplication': {'duplicateCountMax': 5,\
                                     'rdmSel': {'dist': 'PERIODIC', 'interval': 10, 'burstlen': 1, 'stddev': 10.0},\
                                     'enabled': False, 'duplicateCountMin': 1}}
        return emptyProf

    def deleteProfile(self,port_id,name):
        status = False
        self.refreshInfo()
        lProfiles = self.port[port_id]['profiles']
        for profile in lProfiles:
            if profile['tag'] == name:
                lProfiles.remove(profile)
                break
        upload = requests.put("http://" + self.ip + "/api/hw/Port/" + str(port_id), data=json.dumps(self.port[port_id]), auth=(self.user, self.password))
        if upload.status_code == 200:
            status = True
        return status

    def clearDefaultProfile(self,port_id):
        status = False
        self.refreshInfo()
        defaultProfile = self._getEmptyDefaultProfile()
        self.port[port_id]['defaultProfile'] = copy.deepcopy(defaultProfile)
        upload = requests.put("http://" + self.ip + "/api/hw/Port/" + str(port_id), data=json.dumps(self.port[port_id]), auth=(self.user, self.password))
        if upload.status_code == 200:
            status = True
        return status

    def getPortStats(self, port_id):
        status = False
        self.refreshInfo()
        statsRt = requests.get("http://" + self.ip + "/api/stats/Port/" + str(port_id), auth=(self.user, self.password))
        if statsRt.status_code == 200:
            return json.loads(statsRt.text)

    def getProfileStats(self, port_id, profile):
        pstats  = self.getPortStats(port_id)
        portTag = self._getPortTag(port_id)
        if profile in pstats[portTag]:
            return pstats[portTag][profile]
        else:
            return False

    @staticmethod
    def _getPortTag(port_id):
        return 'Port'+port_id

    def clearPortStats(self, port_id):
        status = False
        statsRt = requests.put("http://" + self.ip + "/api/stats/Port/" + str(port_id), auth=(self.user, self.password))
        if statsRt.status_code == 200:
            return json.loads(statsRt.text)

    def clearAllPortsStats(self):
        """
        Description
           Clear port stats on all ports .
        Parameters
        """
        for port in self.ports:
                self.clearPortStats(str(port['logicalId']))

    @staticmethod
    def _hexMe(val):
        return '{:#x}'.format(val)[2:]

    def addCommonIpv4Rule(self,port_id,profile,version=False,srcAddr=False,\
                          destAddr=False,diffServTos=False,protocol=False,srcPort=False,destPort=False):
        rulesToImplement = []
        if version:
            rulesToImplement.append({'bitRange': 'L3@0[7]+3', 'field': 'Common::IPv4::Version',
                                     'value': str(version), 'mask': 'f'})
        if srcAddr:
            net = ipaddress.ip_network(srcAddr, strict=False)
            hexIpv4 = self._hexMe(net.network_address)
            netMask = self._hexMe(net.netmask)
            rulesToImplement.append({'bitRange': 'L3@12[7]+31', 'field': 'Common::IPv4::Source Address',
                                     'value': hexIpv4,'mask': netMask})
        if destAddr:
            net = ipaddress.ip_network(destAddr, strict=False)
            hexIpv4 = self._hexMe(net.network_address)
            netMask = self._hexMe(net.netmask)
            rulesToImplement.append({'bitRange': 'L3@16[7]+31', 'field': 'Common::IPv4::Destination Address',
                                     'value': hexIpv4,'mask': netMask})
        if diffServTos is not False:
            rulesToImplement.append({'bitRange': 'L3@1[7]+5', 'field': 'Common::IPv4::DiffServ/TOS',
                                     'value': str(diffServTos), 'mask': '3f'})
        if protocol:
            rulesToImplement.append(
                {'bitRange': 'L3@9[7]+7', 'field': 'Common::IPv4::Protocol', 'value': str(protocol), 'mask': 'ff'}
            )
        if srcPort:
            rulesToImplement.append(
                {'bitRange': 'L3@20[7]+15', 'field': 'Common::IPv4::TCP/UDP Source Port',
                 'value': str(srcPort), 'mask': 'ffff'}
            )
        if destPort:
            rulesToImplement.append(
                {'bitRange': 'L3@22[7]+15', 'field': 'Common::IPv4::TCP/UDP Destination Port',
                 'value': str(destPort), 'mask': 'ffff'}
            )
        for ruleToAdd in rulesToImplement:
            self.addAnythingToProfile(port_id, profile, 'rules', ruleToAdd)


    def checkIfFilterIsWorking(self,port_id, profile):
        retVal = self.getProfileStats(port_id,profile)
        returnFlag = False
        if 'ETH_PROFILE_TX_PACKETS' in retVal:
            if retVal['ETH_PROFILE_TX_PACKETS']['current'] > 0:
                returnFlag = True

        if 'ETH_PROFILE_RX_PACKETS' in retVal:
            if retVal['ETH_PROFILE_RX_PACKETS']['current'] > 0:
                returnFlag = True

        return returnFlag

    def addConstantEthernetDelay(self, port_id, profile, delayValue, delayUnit):
        callStatus = False
        validDelayUnits = ['KM', 'M', 'S', 'MS', 'US', 'NS']
        if delayUnit.upper() in validDelayUnits:
            etherDelayDict = {'delay': delayValue, 'units': delayUnit.upper(), 'enabled': True, 'pdvMode':'NONE'}
            self.addAnythingToProfile(port_id, profile, 'ethernetDelay', etherDelayDict)
            callStatus = True
        else:
            print(f"Invalid delay unit passed in {delayUnit} - Valid types are {validDelayUnits}")
        return callStatus

    def addCommonByteOffset(self, port_id, profile, offsetType, offset, mask, value ):
        # Offset Supported Values
        # L2_1Byte L2_4Bytes L3_1Byte L3_4Bytes
        sendDict = {'field':'', 'value' : value, 'mask': mask }
        if offsetType.upper() == 'L3_4Bytes'.upper() or offsetType.lower() == 'L3_4Bytes'.lower():
            sendDict['bitRange'] = 'L3@' + str(offset) + '[7]+31'
        elif offsetType.upper() == 'L3_1Byte'.upper() or offsetType.lower() == 'L3_1Byte'.lower():
            sendDict['bitRange'] = 'L3@' + str(offset) + '[7]+7'
        elif offsetType.upper() == 'L2_4Bytes'.upper() or offsetType.lower() == 'L2_4Bytes'.lower():
            sendDict['bitRange'] = 'L2@' + str(offset) + '[7]+31'
        elif offsetType.upper() == 'L2_1Byte'.upper() or offsetType.lower() == 'L2_1Byte'.lower():
            sendDict['bitRange'] = 'L2@' + str(offset) + '[7]+7'
        else:
            print(f"Unable to understand the offset type valid types are L2_1Byte L2_4Bytes L3_1Byte L3_4Bytes")
            return False
        self.addAnythingToProfile(port_id, profile, 'rules', sendDict)
        return True

    def addUniformPacketDrop(self,port_id, profile, dropPerct):
        # PERIODIC, UNIFORM, GAUSSIAN, POISSON
        sendDict = {'rdmSel': {'dist': 'UNIFORM', 'interval': 100,'stddev': 10.0}, 'enabled': True}
        num, _ = dropPerct.split('%')
        sendDict['rdmSel']['burstlen'] = int(num)
        self.addAnythingToProfile(port_id, profile, 'packetDrop', sendDict)
        return True

    def addPeriodicPacketDrop(self,port_id, profile, dropPerct):
        # PERIODIC, UNIFORM, GAUSSIAN, POISSON
        sendDict = {'rdmSel': {'dist': 'PERIODIC', 'interval': 100,'stddev': 10.0}, 'enabled': True}
        num, _ = dropPerct.split('%')
        sendDict['rdmSel']['burstlen'] = int(num)
        self.addAnythingToProfile(port_id, profile, 'packetDrop', sendDict)
        return True



    def checkAlarms(self):
        for port in self.ports:
            port_id = str(port['logicalId'])
            portTag = self._getPortTag(port_id)
            statsRt = requests.put("http://" + self.ip + "/api/alarms/Port/" + str(port_id), headers=self.headers)
            if str(statsRt.status_code)[:2] == '20':
                time.sleep(2)
                statsRt = requests.get("http://" + self.ip + "/api/alarms/Port/" + str(port_id), headers=self.headers)
                if statsRt.status_code == 200:
                    retVal = json.loads(statsRt.text)
                    if portTag in retVal:
                        for key in retVal[portTag]:
                            if isinstance(key, str) and isinstance(retVal[portTag][key], str):
                                if retVal[portTag][key] == 'green':
                                    continue
                                else:
                                    print(f"WARNING : Alarm {key} on {portTag} -- {retVal[portTag][key]} after reset")
                                    return False
        return True


