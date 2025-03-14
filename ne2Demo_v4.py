from neEmu2 import neEmu2
from my_helper_functions import *
from ixnetwork_restpy import *
import time
import locale
locale.setlocale(locale.LC_ALL, '') 
import unittest


class NeTests(unittest.TestCase):

    def test_baseline(self):
        ## Test Variables
        myStep = Step()
        vport_dic = dict()
        t_vars = testVars()
        t_vars.net_emu_mgmt_ip = '192.168.123.227'
        t_vars.net_emu_user = 'admin'
        t_vars.net_emu_password = 'admin'
        t_vars.net_emu_port_1 = '1'
        t_vars.net_emu_port_2 = '2'
        
        t_vars.ixia_chassis_ip  = '192.168.123.100'
        t_vars.ixia_session_ip  = 'localhost' 
        t_vars.ixia_session_id  = '1'
        t_vars.ixia_port_1  = '1/1'
        t_vars.ixia_port_2 = '1/2'
        t_vars.ixia_port_media  = 'copper'
        t_vars.ixia_baseline_port_1  = '2/5'
        t_vars.ixia_baseline_port_2  = '2/6'
        t_vars.ixia_baseline_port_media  = 'copper'
        t_vars.ixia_baseline_pkt_sizes  = [64,512,1280,1500,'IMIX']

        t_vars.ixia_port_speed  = 'speed1000'

        # Only needed if running on Unix Enviroment
        t_vars.ixia_user = 'cris'
        t_vars.ixia_password = 'Keysight#12345'
        
        outLogFile : str = 'n2Demo_' + time.strftime("%Y%m%d-%H%M%S") + '.log'
        ## End of Variables

        # Test #1 - Baseline 
        # Objective : Find the baseline or INTRINSIC DELAY 
        # Using baseline ports that are connected back to back find the latency for 64 B packets / IMIX and 10K B 
        # repeat the test using ports that are connected to the NE-2 

        try:
            session = SessionAssistant(IpAddress= t_vars.ixia_session_ip,
                                    UserName= t_vars.ixia_user,
                                    Password= t_vars.ixia_password,
                                    SessionId= t_vars.ixia_session_id,
                                    ClearConfig=True,
                                    LogLevel='info',
                                    LogFilename=outLogFile)
        except Exception as errMsg:
            print(f"{errMsg}")

        ixnet_session = session.Ixnetwork
        ixnet_session.info(f"Step {myStep.add()} - Init - Rest Session {session.Session.Id} established.")
            
        #Set Latency Delay Mode to Store and Forward
        ixnet_session.info(f"Step {myStep.add()} - Init - Set delay variation mode to Cut Through - see user guide for definition.")
        ixnet_session.Traffic.Statistics.Latency.Mode = 'cutThrough'

        ixnet_session.info(f"Step {myStep.add()} - Init - Assign Ports to Session.")
        port_map = session.PortMapAssistant()
        mySlot, portIndex = t_vars.ixia_baseline_port_1 .split("/")
        vport_dic["base_port1"] =  port_map.Map(t_vars.ixia_chassis_ip, mySlot, portIndex, Name="base_port1")
        mySlot, portIndex = t_vars.ixia_baseline_port_2.split("/")
        vport_dic["base_port2"] =port_map.Map(t_vars.ixia_chassis_ip, mySlot, portIndex, Name="base_port2")
        port_map.Connect(ForceOwnership=True,IgnoreLinkUp=True)  

        for vport in vport_dic:
                thisPort = ixnet_session.Vport.find(Name=vport)
                #thisPort.Type = 'novusTenGigLanFcoe'
                portType = thisPort.Type[0].upper() + thisPort.Type[1:]
                ixnet_session.info(f"Step {myStep.add()} - Init - Setting port {vport} to Interleaved mode")
                thisPort.TxMode = 'interleaved'
                portObj = getattr(thisPort.L1Config, portType)
                ixnet_session.info(f" Step {myStep.add_minor()} - Init - setting media type to  {t_vars.ixia_baseline_port_media}")
                portObj.Media = t_vars.ixia_baseline_port_media
                portObj.SelectedSpeeds = [t_vars.ixia_port_speed]


            
        ixnet_session.info(f"Step {myStep.add()} - Init - Checking once more if all ports are up - Abort otherwise")
        portStats = StatViewAssistant(ixnet_session, 'Port Statistics')
        portStats.CheckCondition('Link State', StatViewAssistant.REGEX, 'Link\s+Up', Timeout=30,RaiseException=True)

        # Port1 
        ixnet_session.info(f"Step {myStep.add()} - Init - Setting up port1 topology")
        topo1 = ixnet_session.Topology.add(Name='Port 1', Ports=vport_dic["base_port1"])
        dev1 = topo1.DeviceGroup.add(Name='Port1 - DG', Multiplier='100')
        eth1 = dev1.Ethernet.add(Name='p1 ether')
        ip1 = eth1.Ipv4.add(Name='Ip1 172.16.0.1/16')
        ip1.Address.Increment(start_value="172.16.0.1", step_value="0.0.0.1")
        ip1.GatewayIp.Increment(start_value="172.16.100.1", step_value="0.0.0.1")
        ip1.Prefix.Single(16)
        ip1.ResolveGateway.Single(value=True)

        # Port2 
        ixnet_session.info(f"Step {myStep.add()} - Init - Setting up port2 topology")
        topo2 = ixnet_session.Topology.add(Name='Port 2', Ports=vport_dic["base_port2"])
        dev2 = topo2.DeviceGroup.add(Name='Port2 - DG', Multiplier='100')
        eth2 = dev2.Ethernet.add(Name='p2 ether')
        ip2 = eth2.Ipv4.add(Name='Ip1 172.16.100.1/16')
        ip2.Address.Increment(start_value="172.16.100.1", step_value="0.0.0.1")
        ip2.GatewayIp.Increment(start_value="172.16.0.1", step_value="0.0.0.1")
        ip2.Prefix.Single(16)
        ip2.ResolveGateway.Single(value=True)
        ixnet_session.info(f'Step {myStep.add()} - Init -  Staring Protocols')
        ixnet_session.StartAllProtocols(Arg1='sync')
        
        ixnet_session.info(f'Step{myStep.add()} - Verify -  IP sessions are UP')
        protocolsSummary = StatViewAssistant(ixnet_session, 'Protocols Summary')
        protocolsSummary.AddRowFilter('Protocol Type', StatViewAssistant.REGEX, '(?i)^IPv4?')
        protocolsSummary.CheckCondition('Sessions Not Started', StatViewAssistant.EQUAL, '0')
        ixnet_session.info(f'Step {myStep.add()} - Init -  Create Uni-directional Ipv4 Traffic Item for Baseline.')
        ixnet_session.Traffic.EnableMinFrameSize = True
        ixnet_session.Traffic.MinimumSignatureLength = 4
        etherTraffItem = ixnet_session.Traffic.TrafficItem.add(Name='BaseLine', BiDirectional=False,TrafficType='ipv4',TrafficItemType='l2L3')
        flow = etherTraffItem.EndpointSet.add(Sources= ip1 , Destinations=ip2)
        flow.Name = "BaseLine"
        configElement = etherTraffItem.ConfigElement.find()[0]
        configElement.FrameRate.update(Type='percentLineRate', Rate=100)
        etherTraffItem.Tracking.find()[0].TrackBy = ["trackingenabled0"]
        results = dict()
        results['baseline'] = dict()
        results['test'] = dict()
        for pkt_size in t_vars.ixia_baseline_pkt_sizes:
                ixnet_session.info(f'Step {myStep.add()} - Init -  Setting Baseline Traffic for size: {pkt_size}.')
                if isinstance(pkt_size, int):
                    configElement.FrameSize.update(Type='fixed', FixedSize = pkt_size)              
                elif isinstance(pkt_size, str):
                    if pkt_size == 'IMIX':
                        configElement.FrameSize.update(Type='presetDistribution', PresetDistribution='cisco')
                    else:
                        ixnet_session.info(f'ERROR - ONLY IMIX IS SUPPORTED at this time')
                        continue 
                else:
                    ixnet_session.info(f"ERROR - Unknown type: {pkt_size}")
                    continue
                ixnet_session.info(f'Step {myStep.add()} - Init -  Generate and Applying traffic item for size: {pkt_size}.')
                etherTraffItem.Generate()
                ixnet_session.Traffic.Apply()
                time.sleep(10)
                ixnet_session.info(f'Step {myStep.add()} - Test - Sending Traffic for 30 seconds')
                ixnet_session.Traffic.Start(async_operation=False)
                time.sleep(30)
                ixnet_session.Traffic.Stop(async_operation=False)
                traff_running = True
                while traff_running:
                    currentTrafficState = ixnet_session.Traffic.State
                    ixnet_session.info('Currently traffic is in ' + currentTrafficState + ' state')
                    if currentTrafficState == 'notRunning' or currentTrafficState == 'stopped' or currentTrafficState == 'unapplied':
                            traff_running = False
                    else:
                        time.sleep(3)
                time.sleep(5)
                ixnet_session.info(f'Step {myStep.add()} - Verify - All traffic sent was received and recording latency')
                traffItemStatistics = StatViewAssistant(ixnet_session, 'Traffic Item Statistics')
                for flowStat in traffItemStatistics.Rows: 
                    if compare_numbers(float(flowStat['Rx Frames']), float(flowStat['Tx Frames']), thresholdNum = 0.99):
                    #if abs(float(flowStat['Rx Frames']) - float(flowStat['Tx Frames'])) < 1 and float(flowStat['Tx Frames']) > 1:
                        ixnet_session.info(f"Tx Frames {int(flowStat['Tx Frames']):,} and Rx Frames {int(flowStat['Rx Frames']):,} -- PASS")
                        results['baseline'][str(pkt_size)] = float(flowStat['Cut-Through Avg Latency (ns)'])
                    else:
                        ixnet_session.info(f"Tx Frames {int(flowStat['Tx Frames']):,} and Rx Frames {int(flowStat['Rx Frames']):,} -- FAILED")
                        results['baseline'][str(pkt_size)] = -1 
        ixnet_session.info(f'Step {myStep.add()} - Init -  Stopping all Protocols')
        ixnet_session.StopAllProtocols()
        ixnet_session.info(f'Step {myStep.add()} - Init -  Releasing Baseline Ports and mapping testing ports.')
        basePort1 = ixnet_session.Vport.find(Name="base_port1")
        basePort1.ReleasePort()
        basePort2 = ixnet_session.Vport.find(Name="base_port2")
        basePort2.ReleasePort()
        port_map = session.PortMapAssistant()
        mySlot, portIndex = t_vars.ixia_port_1 .split("/")
        vport_dic["port1"] =  port_map.Map(t_vars.ixia_chassis_ip, mySlot, portIndex, Name="base_port1")
        mySlot, portIndex = t_vars.ixia_port_2.split("/")
        vport_dic["port2"] =port_map.Map(t_vars.ixia_chassis_ip, mySlot, portIndex, Name="base_port2")
        ixnet_session.info(f'Step {myStep.add()} - Init -  Connecting Test Ports.')
        port_map.Connect(ForceOwnership=True,IgnoreLinkUp=True)  
        for vport in vport_dic:
            thisPort = ixnet_session.Vport.find(Name=vport)
            #thisPort.Type = 'novusTenGigLanFcoe'
            portType = thisPort.Type[0].upper() + thisPort.Type[1:]
            ixnet_session.info(f"Step {myStep.add()} - Init - Setting port {vport} to Interleaved mode")
            thisPort.TxMode = 'interleaved'
            portObj = getattr(thisPort.L1Config, portType)
            ixnet_session.info(f" Step {myStep.add_minor()} - Init - setting media type to  {t_vars.ixia_port_media}")
            portObj.Media = t_vars.ixia_port_media
            portObj.SelectedSpeeds = [t_vars.ixia_port_speed]
        ixnet_session.info(f"Step {myStep.add()} - Init - Checking once more if all ports are up - Abort otherwise")
        portStats = StatViewAssistant(ixnet_session, 'Port Statistics')
        portStats.CheckCondition('Link State', StatViewAssistant.REGEX, 'Link\s+Up', Timeout=60,RaiseException=True)
        ixnet_session.info(f'Step {myStep.add()} - Init -  Staring Protocols')
        ixnet_session.StartAllProtocols(Arg1='sync')
            
        ixnet_session.info(f'Step{myStep.add()} - Verify -  IP sessions are UP')
        protocolsSummary = StatViewAssistant(ixnet_session, 'Protocols Summary')
        protocolsSummary.AddRowFilter('Protocol Type', StatViewAssistant.REGEX, '(?i)^IPv4?')
        protocolsSummary.CheckCondition('Sessions Not Started', StatViewAssistant.EQUAL, '0')
        ixnet_session.info(f'Step {myStep.add()} - Init -  Establish connection to Network Emulator: {t_vars.net_emu_mgmt_ip}')
        ne2 = neEmu2(t_vars.net_emu_mgmt_ip, t_vars.net_emu_user , t_vars.net_emu_password)
        ixnet_session.info(f'Step {myStep.add()} - Init - Checking all alarms are green, meaning green light to continue -- {ne2.checkAlarms()}')
        ixnet_session.info(f'Step {myStep.add()} - Init - Delete all profiles on all Ports - NOTE: The default profile cannot be deleted or disabled')
        ne2.deleteAllProfiles()
        for pkt_size in t_vars.ixia_baseline_pkt_sizes:
            ixnet_session.info(f'Step {myStep.add()} - Init -  Setting test traffic size to {pkt_size}.')         
            if isinstance(pkt_size, int):
                configElement.FrameSize.update(Type='fixed', FixedSize = pkt_size)              
            elif isinstance(pkt_size, str):
                if pkt_size == 'IMIX':
                    configElement.FrameSize.update(Type='presetDistribution', PresetDistribution='cisco')
                else:
                    ixnet_session.info(f'ERROR - ONLY IMIX IS SUPPORTED at this time')
                    continue 
            else:
                ixnet_session.info(f"ERROR - Unknown type: {pkt_size}")
                continue
            
            etherTraffItem.Generate()
            ixnet_session.Traffic.Apply()
            time.sleep(10)
            ixnet_session.info(f'Step {myStep.add()} - Test - Send Traffic and wait 30 seconds')
            ixnet_session.Traffic.Start(async_operation=False)
            time.sleep(30)
            ixnet_session.Traffic.Stop(async_operation=False)
            traff_running = True
            while traff_running:
                currentTrafficState = ixnet_session.Traffic.State
                ixnet_session.info('Currently traffic is in ' + currentTrafficState + ' state')
                if currentTrafficState == 'notRunning' or currentTrafficState == 'stopped' or currentTrafficState == 'unapplied':
                        traff_running = False
                else:
                    time.sleep(3)
            time.sleep(5)
            ixnet_session.info(f'Step {myStep.add()} - Verify - All traffic sent was received and recording latency results.')
            traffItemStatistics = StatViewAssistant(ixnet_session, 'Traffic Item Statistics')
            for flowStat in traffItemStatistics.Rows: 
                if compare_numbers(float(flowStat['Rx Frames']), float(flowStat['Tx Frames']), thresholdNum = 0.99):
                #if abs(float(flowStat['Rx Frames']) - float(flowStat['Tx Frames'])) < 1 and float(flowStat['Tx Frames']) > 1:
                    ixnet_session.info(f"Tx Frames {int(flowStat['Tx Frames']):,} and Rx Frames {int(flowStat['Rx Frames']):,} -- PASS")
                    results['test'][str(pkt_size)] = float(flowStat['Cut-Through Avg Latency (ns)'])
                else:
                    ixnet_session.info(f"Tx Frames {int(flowStat['Tx Frames']):,} and Rx Frames {int(flowStat['Rx Frames']):,} -- FAILED")
                    results['test'][str(pkt_size)] = -1 
         # Initialize an empty dictionary to store the differences
            differences = {}
            for key in results['test']:
            # Calculate the difference between the test and baseline values
                differences[key] = results['test'][key] - results['baseline'][key]
        ixnet_session.info(f"Delay introduced by having the NE-2 on the wire")
        for key, value in differences.items():
                ixnet_session.info(f"Pkt Size: {key}, Value: {value} in nanoseconds.")                  
             
        ixnet_session.info(f'Step {myStep.add()} - END -  Cleaning Up.')
        ixnet_session.info(f"Step {myStep.add_minor()} - Clean up - Stopping Protocols")
        ixnet_session.StopAllProtocols()
        ixnet_session.info(f"Step {myStep.add_minor()} - Clean up - Releasing Ports")
        basePort1.ReleasePort()
        basePort2.ReleasePort()
        ixnet_session.info(f"Step {myStep.add_minor()} - Clean up - Cleaning up session and leaving it up...bye")
        ixnet_session.NewConfig()
        self.assertTrue(True)

    def test_port_policing(self):
            myStep = Step()
            vport_dic = dict()
            t_vars = testVars()
            t_vars.net_emu_mgmt_ip = '10.80.81.8'
            t_vars.net_emu_user = 'cris'
            t_vars.net_emu_password = 'Keysight#12345'
            t_vars.net_emu_port_1 = '1'
            t_vars.net_emu_port_2 = '2'
            t_vars.ixia_chassis_ip  = '10.80.81.2'
            t_vars.ixia_session_ip  = 'localhost' 
            t_vars.ixia_session_id  = '1'
            t_vars.ixia_port_1  = '2/1'
            t_vars.ixia_port_2 = '2/2'
            t_vars.ixia_port_media  = 'copper'
            t_vars.ixia_port_speed  = 'speed1000'

            # Only needed if running on Unix Enviroment
            t_vars.ixia_user = 'cris'
            t_vars.ixia_password = 'Keysight#12345'
            
            outLogFile : str = 'n2Demo_' + time.strftime("%Y%m%d-%H%M%S") + '.log'
            ## End of Variables

            try:
                session = SessionAssistant(IpAddress= t_vars.ixia_session_ip,
                                        UserName= t_vars.ixia_user,
                                        Password= t_vars.ixia_password,
                                        SessionId= t_vars.ixia_session_id,
                                        ClearConfig=True,
                                        LogLevel='info',
                                        LogFilename=outLogFile)
            except Exception as errMsg:
                print(f"{errMsg}")

            ixnet_session = session.Ixnetwork
            ixnet_session.info(f"Step {myStep.add()} - Init - Rest Session {session.Session.Id} established.")
                
            #Set Latency Delay Mode to Store and Forward
            ixnet_session.info(f"Step {myStep.add()} - Init - Set delay variation mode to Cut Through - see user guide for definition.")
            ixnet_session.Traffic.Statistics.Latency.Mode = 'cutThrough'

            ixnet_session.info(f"Step {myStep.add()} - Init - Assign Ports to Session.")
            port_map = session.PortMapAssistant()
            mySlot, portIndex = t_vars.ixia_port_1 .split("/")
            vport_dic["port1"] =  port_map.Map(t_vars.ixia_chassis_ip, mySlot, portIndex, Name="port1")
            mySlot, portIndex = t_vars.ixia_port_2.split("/")
            vport_dic["port2"] =port_map.Map(t_vars.ixia_chassis_ip, mySlot, portIndex, Name="port2")
            port_map.Connect(ForceOwnership=True,IgnoreLinkUp=True)  

            for vport in vport_dic:
                    thisPort = ixnet_session.Vport.find(Name=vport)
                    #thisPort.Type = 'novusTenGigLanFcoe'
                    portType = thisPort.Type[0].upper() + thisPort.Type[1:]
                    ixnet_session.info(f"Step {myStep.add()} - Init - Setting port {vport} to Interleaved mode")
                    thisPort.TxMode = 'interleaved'
                    portObj = getattr(thisPort.L1Config, portType)
                    ixnet_session.info(f" Step {myStep.add_minor()} - Init - setting media type to  {t_vars.ixia_port_media}")
                    portObj.Media = t_vars.ixia_port_media
                    portObj.SelectedSpeeds = [t_vars.ixia_port_speed]


                
            ixnet_session.info(f"Step {myStep.add()} - Init - Checking once more if all ports are up - Abort otherwise")
            portStats = StatViewAssistant(ixnet_session, 'Port Statistics')
            portStats.CheckCondition('Link State', StatViewAssistant.REGEX, 'Link\s+Up', Timeout=30,RaiseException=True)

            # Port1 
            ixnet_session.info(f"Step {myStep.add()} - Init - Setting up port1 topology")
            topo1 = ixnet_session.Topology.add(Name='Port 1', Ports=vport_dic["port1"])
            dev1 = topo1.DeviceGroup.add(Name='Port1 - DG', Multiplier='1000')
            eth1 = dev1.Ethernet.add(Name='p1 ether')
            ip1 = eth1.Ipv4.add(Name='Ip1 172.16.0.1/16')
            ip1.Address.Increment(start_value="172.16.0.1", step_value="0.0.0.1")
            ip1.GatewayIp.Increment(start_value="172.16.100.1", step_value="0.0.0.1")
            ip1.Prefix.Single(16)
            ip1.ResolveGateway.Single(value=True)

            # Port2 
            ixnet_session.info(f"Step {myStep.add()} - Init - Setting up port2 topology")
            topo2 = ixnet_session.Topology.add(Name='Port 2', Ports=vport_dic["port2"])
            dev2 = topo2.DeviceGroup.add(Name='Port2 - DG', Multiplier='1000')
            eth2 = dev2.Ethernet.add(Name='p2 ether')
            ip2 = eth2.Ipv4.add(Name='Ip1 172.16.100.1/16')
            ip2.Address.Increment(start_value="172.16.100.1", step_value="0.0.0.1")
            ip2.GatewayIp.Increment(start_value="172.16.0.1", step_value="0.0.0.1")
            ip2.Prefix.Single(16)
            ip2.ResolveGateway.Single(value=True)
            ixnet_session.info(f'Step {myStep.add()} - Init -  Staring Protocols')
            ixnet_session.StartAllProtocols(Arg1='sync')
            
            ixnet_session.info(f'Step{myStep.add()} - Verify -  IP sessions are UP')
            protocolsSummary = StatViewAssistant(ixnet_session, 'Protocols Summary')
            protocolsSummary.AddRowFilter('Protocol Type', StatViewAssistant.REGEX, '(?i)^IPv4?')
            protocolsSummary.CheckCondition('Sessions Not Started', StatViewAssistant.EQUAL, '0')
            ixnet_session.info(f'Step {myStep.add()} - Init -  Create Uni-directional Ipv4 Traffic Item for Baseline.')
            etherTraffItem = ixnet_session.Traffic.TrafficItem.add(Name='Policing....1G to 100 Mbs', BiDirectional=False,TrafficType='ipv4',TrafficItemType='l2L3')
            flow = etherTraffItem.EndpointSet.add(Sources= ip1 , Destinations=ip2)
            flow.Name = "Port Policing"
            configElement = etherTraffItem.ConfigElement.find()[0]
            configElement.FrameRate.update(Type='percentLineRate', Rate=100)
            configElement.FrameSize.update(Type='fixed', FixedSize=1500)
            ipv4StackObj = configElement.Stack.find(DisplayName='IPv4')
            udpProtocolTemplate = ixnet_session.Traffic.ProtocolTemplate.find(StackTypeId='^udp$')
            ipv4StackObj.Append(Arg2=udpProtocolTemplate)
            udpFieldObj = configElement.Stack.find(StackTypeId='^udp$')
            udpSrcField = udpFieldObj.Field.find(DisplayName='UDP-Source-Port')
            udpSrcField.Auto = False
            udpSrcField.ValueType = 'nonRepeatableRandom'
            udpDstField = udpFieldObj.Field.find(DisplayName='UDP-Dest-Port')
            udpDstField.Auto = False
            udpDstField.ValueType = 'nonRepeatableRandom'
            etherTraffItem.Tracking.find()[0].TrackBy = ["trackingenabled0"]
            etherTraffItem.Generate()
            ixnet_session.Traffic.Apply()
            time.sleep(10)

            ixnet_session.info(f'Step {myStep.add()} - Init -  Establish connection to Network Emulator: {t_vars.net_emu_mgmt_ip}')
            ne2 = neEmu2(t_vars.net_emu_mgmt_ip, t_vars.net_emu_user , t_vars.net_emu_password)
            ixnet_session.info(f'Step {myStep.add()} - Init - Checking all alarms are green, meaning green light to continue -- {ne2.checkAlarms()}')
            ixnet_session.info(f'Step {myStep.add()} - Init - Delete all profiles on all Ports - NOTE: The default profile cannot be deleted or disabled')
            ne2.deleteAllProfiles()
            ne2.refreshInfo()
            strictPolicer  = {'excessBitRate': 0, 'excessBurstTolerance': 0, 'commitedBurstTolerance': 64000,\
                              'commitedBitRate': 100000, 'enabled': True }

            ixnet_session.info(f'Step {myStep.add()} - Init - Adding Policer to port {t_vars.net_emu_port_1}')

            ne2.addPortPolicer('1',strictPolicer)

            ixnet_session.info(f'Step {myStep.add()} - Test - Start Traffic')
            time.sleep(10)
            ixnet_session.Traffic.Start()
            time.sleep(20)
            traffItemStatistics = StatViewAssistant(ixnet_session, 'Traffic Item Statistics')
            flowStat = traffItemStatistics.Rows[0]
            self.assertTrue( compare_numbers(float(flowStat['Tx Rate (Mbps)']), 1000, thresholdNum=0.97) , "The TX rate is close to 1000 Mbps")
            self.assertTrue(compare_numbers(float(flowStat['Rx Rate (Mbps)']), 100, thresholdNum=0.99), "The RX rate is close to 100 Mbps")
            ixnet_session.info(f'Step {myStep.add()} - Test - Verify TX rate is close to 1_000 Mbps {flowStat['Tx Rate (Mbps)']}')
            ixnet_session.info(f'Step {myStep.add()} - Test - Verify RX rate is close to 100 Mbps {flowStat['Rx Rate (Mbps)']}')

            ixnet_session.info(f'Step {myStep.add()} - END -  Cleaning Up.')
            ixnet_session.info(f"Step {myStep.add_minor()} - Clean up - Stopping Traffic")
            ixnet_session.Traffic.Stop(async_operation=False)
            traff_running = True
            while traff_running:
                currentTrafficState = ixnet_session.Traffic.State
                ixnet_session.info('Currently traffic is in ' + currentTrafficState + ' state')
                if currentTrafficState == 'notRunning' or currentTrafficState == 'stopped' or currentTrafficState == 'unapplied':
                    traff_running = False
                else:
                    time.sleep(3)
            time.sleep(5)
            ixnet_session.info(f"Step {myStep.add_minor()} - Clean up - Stopping Protocols")
            ixnet_session.StopAllProtocols()
            ixnet_session.info(f"Step {myStep.add_minor()} - Clean up - Releasing Ports")
            vport_dic["port1"].ReleasePort()
            vport_dic["port2"].ReleasePort()
            ixnet_session.info(f"Step {myStep.add_minor()} - Clean up - Reset Network Emulator 2")
            ne2.deleteAllProfiles()
            ixnet_session.info(f"Step {myStep.add_minor()} - Clean up - Cleaning up session and leaving it up...bye")
            ixnet_session.NewConfig()

            self.assertTrue(True)

    def test_latency(self):
            '''
             source: https://www.verizon.com/business/solutions/business-continuity/weekly-latency-statistics/ 

             Data in ms from May 2024
                 Latency data: 
                    Within the   US :  32.296
                    Singapore to US : 174.656
                    Australia to US : 152.618
                    Argentina to US : 143.144
                    Chile to US     : 162.475
                    North America to India : 245.797     
            '''
            myStep = Step()
            vport_dic = dict()
            t_vars = testVars()
            t_vars.net_emu_mgmt_ip = '10.80.81.8'
            t_vars.net_emu_user = 'admin'
            t_vars.net_emu_password = 'admin'
            t_vars.net_emu_port_1 = '1'
            t_vars.net_emu_port_2 = '2'
            t_vars.ixia_chassis_ip  = '10.80.81.2'
            t_vars.ixia_session_ip  = 'localhost' 
            t_vars.ixia_session_id  = '1'
            t_vars.ixia_port_1  = '2/3'
            t_vars.ixia_port_2 = '2/4'
            t_vars.ixia_port_media  = 'fiber'
            t_vars.ixia_port_speed  = 'speed10g'

            # Only needed if running on Unix Enviroment
            t_vars.ixia_user = 'cris'
            t_vars.ixia_password = 'Keysight#12345'
            
            outLogFile : str = 'n2Demo_latency_test' + time.strftime("%Y%m%d-%H%M%S") + '.log'
            t_vars.ixia_latency_tests = {'Singapore' : {'latency': '174.656', 'direction': 'to', 'ip':'101.127.0.1/16' },
                                         'Australia' : {'latency': '152.618', 'direction': 'to', 'ip':'101.103.0.1/16'},
                                         'Argentina' : {'latency': '143.144', 'direction': 'to', 'ip':'140.191.0.1/16'},
                                         'Chile' : {'latency': '162.475', 'direction': 'to', 'ip':'146.155.0.1/16'},
                                         'US' : {'latency': '32.296', 'direction': 'to', 'ip':'104.154.0.1/16'},
                                         'India' : {'latency': '245.797', 'direction': 'from', 'ip':'1.187.0.1/16'}
                                        }
            

            
            ## End of Variables

            try:
                session = SessionAssistant(IpAddress= t_vars.ixia_session_ip,
                                        UserName= t_vars.ixia_user,
                                        Password= t_vars.ixia_password,
                                        SessionId= t_vars.ixia_session_id,
                                        ClearConfig=True,
                                        LogLevel='info',
                                        LogFilename=outLogFile)
            except Exception as errMsg:
                print(f"{errMsg}")

            ixnet_session = session.Ixnetwork
            ixnet_session.info(f"Step {myStep.add()} - Init - Rest Session {session.Session.Id} established.")
            self.assertIsNotNone(session.Session.Id, 'We established session')
            #Set Latency Delay Mode to Store and Forward
            ixnet_session.info(f"Step {myStep.add()} - Init - Set delay variation mode to Cut Through - see user guide for definition.")
            ixnet_session.Traffic.Statistics.Latency.Mode = 'cutThrough'

            ixnet_session.info(f"Step {myStep.add()} - Init - Assign Ports to Session.")
            port_map = session.PortMapAssistant()
            mySlot, portIndex = t_vars.ixia_port_1 .split("/")
            vport_dic["port1"] =  port_map.Map(t_vars.ixia_chassis_ip, mySlot, portIndex, Name="port1")
            mySlot, portIndex = t_vars.ixia_port_2.split("/")
            vport_dic["port2"] =port_map.Map(t_vars.ixia_chassis_ip, mySlot, portIndex, Name="port2")
            port_map.Connect(ForceOwnership=True,IgnoreLinkUp=True)  

            for vport in vport_dic:
                    thisPort = ixnet_session.Vport.find(Name=vport)
                    #thisPort.Type = 'novusTenGigLanFcoe'
                    portType = thisPort.Type[0].upper() + thisPort.Type[1:]
                    ixnet_session.info(f"Step {myStep.add()} - Init - Setting port {vport} to Interleaved mode")
                    thisPort.TxMode = 'interleaved'
                    portObj = getattr(thisPort.L1Config, portType)
                    ixnet_session.info(f" Step {myStep.add_minor()} - Init - setting media type to  {t_vars.ixia_port_media}")
                    portObj.Media = t_vars.ixia_port_media
                    portObj.SelectedSpeeds = [t_vars.ixia_port_speed]


                
            ixnet_session.info(f"Step {myStep.add()} - Init - Checking once more if all ports are up - Abort otherwise")
            portStats = StatViewAssistant(ixnet_session, 'Port Statistics')
            self.assertTrue(portStats.CheckCondition('Link State', StatViewAssistant.REGEX, 'Link\s+Up', Timeout=30,RaiseException=True),\
                            "Test ports are up")
            # Port1 
            ixnet_session.info(f"Step {myStep.add()} - Init - Setting up port1 topology")
            topo1 = ixnet_session.Topology.add(Name='Port 1', Ports=vport_dic["port1"])
            dev1 = topo1.DeviceGroup.add(Name='North America - US', Multiplier='1000')
            eth1 = dev1.Ethernet.add(Name='na/us ether')
            eth1.Mac.Increment(start_value='00:12:ca:ff:ee:01', step_value='00:00:00:00:00:01' )
            ip1 = eth1.Ipv4.add(Name='Ip 101.45.x.x/16')
            ip1.Address.Increment(start_value="101.45.0.1", step_value="0.0.0.1")
            ip1.GatewayIp.Single(value="0.0.0.0")
            ip1.Prefix.Single(16)
            ip1.ResolveGateway.Single(value=False)
            ip1.ManualGatewayMac.Single(value='00:00:00:00:00:00')


            # Port2 
            ixnet_session.info(f"Step {myStep.add()} - Init - Setting up port2 topology")
            topo2 = ixnet_session.Topology.add(Name='Port 2', Ports=vport_dic["port2"])
            for country, info in t_vars.ixia_latency_tests.items():
                dev2 = topo2.DeviceGroup.add(Name=country, Multiplier='1000')
                eth2 = dev2.Ethernet.add(Name= country + 'ether')
                ip2 = eth2.Ipv4.add(Name= info['ip'] )
                ip_addr , mask = info['ip'].split('/')
                ip2.Address.Increment(start_value=ip_addr, step_value="0.0.0.1")
                ip2.GatewayIp.Single(value="0.0.0.0")
                ip2.Prefix.Single(mask)
                ip2.ResolveGateway.Single(value=False)
                ip2.ManualGatewayMac.Single(value='00:00:00:00:00:00')
                info['ip_handle'] = ip2

            ixnet_session.info(f'Step {myStep.add()} - Init -  Staring Protocols')
            ixnet_session.StartAllProtocols(Arg1='sync')
            ixnet_session.info(f'Step{myStep.add()} - Verify -  IP sessions are UP')
            protocolsSummary = StatViewAssistant(ixnet_session, 'Protocols Summary')
            protocolsSummary.AddRowFilter('Protocol Type', StatViewAssistant.REGEX, '(?i)^IPv4?')
            protocolsSummary.CheckCondition('Sessions Not Started', StatViewAssistant.EQUAL, '0')
            self.assertTrue(protocolsSummary.CheckCondition('Sessions Down', StatViewAssistant.EQUAL, '0'),\
                            "All ip clients are up")

            ixnet_session.info(f'Step {myStep.add()} - Init -  Establish connection to Network Emulator: {t_vars.net_emu_mgmt_ip}')
            ne2 = neEmu2(t_vars.net_emu_mgmt_ip, t_vars.net_emu_user, t_vars.net_emu_password)
            ixnet_session.info(f'Step {myStep.add()} - Init - Checking all alarms are green, meaning green light to continue -- {ne2.checkAlarms()}')
            ixnet_session.info(f'Step {myStep.add()} - Init - Delete all profiles on all Ports - NOTE: The default profile cannot be deleted or disabled')
            ne2.deleteAllProfiles()
            ne2.refreshInfo()


            for country, info in t_vars.ixia_latency_tests.items():
                traff_item_name = country + '_traffic_' + info['direction'] + '_US'
                etherTraffItem = ixnet_session.Traffic.TrafficItem.add(Name=traff_item_name, BiDirectional=False,TrafficType='ipv4',TrafficItemType='l2L3')
                flow = None
                if info['direction'] == 'to':
                    flow = etherTraffItem.EndpointSet.add(Sources= info['ip_handle'] , Destinations=ip1)
                else:
                    flow = etherTraffItem.EndpointSet.add(Sources=ip1, Destinations=info['ip_handle'])
                flow.Name = traff_item_name
                configElement = etherTraffItem.ConfigElement.find()[0]
                configElement.FrameRate.update(Type='percentLineRate', Rate=1)
                configElement.FrameSize.update(Type='fixed', FixedSize=1500)
                etherTraffItem.Tracking.find()[0].TrackBy = ["trackingenabled0"]
                etherTraffItem.Generate()
            ixnet_session.Traffic.Apply()
            time.sleep(10)
            ixnet_session.Traffic.Start()

            for country, info in t_vars.ixia_latency_tests.items():
                ingress_port = t_vars.net_emu_port_2 if info['direction'] == 'to' else t_vars.net_emu_port_1
                filter_name = country + '_traffic_' + info['direction'] + '_US'
                srcAddr =  info['ip'] if info['direction'] == 'to' else '101.45.0.0/16'
                srcAddr =  get_network_address(srcAddr)
                ne2.createProfile(ingress_port, filter_name)
                ne2.addCommonIpv4Rule(port_id=ingress_port, profile=filter_name, srcAddr=srcAddr)
                time.sleep(10)
                if ne2.checkIfFilterIsWorking(port_id=ingress_port, profile=filter_name):
                    ixnet_session.info(f'Filter {filter_name} applied to port {srcAddr} is working')
                else:
                    self.assertTrue(False)
                currVal = ne2.getProfileStats(ingress_port, filter_name)
                currValue = round(currVal['ETH_PROFILE_RX_PACKETS']['current'])
                ixnet_session.info(f' Current RX packets {currValue}')
                self.assertGreater(currValue, 0, "The value should be greater than 0.")
                ne2.addConstantEthernetDelay(port_id=ingress_port, profile=filter_name, delayValue= info['latency'], delayUnit='ms')

            stop_ixia_traffic(ixnet_session)
            time.sleep(10)
            ixnet_session.Traffic.Start()
            time.sleep(30)
            traffItemStatistics = StatViewAssistant(ixnet_session, 'Traffic Item Statistics')

            for flowStat in traffItemStatistics.Rows:
                traff_name = flowStat['Traffic Item']
                tx_rate =  flowStat['Tx Frame Rate']
                rx_rate =  flowStat['Rx Frame Rate']
                ixnet_session.info(f'Step {myStep.add()} - Test - for traffic {traff_name} - TX rate and Rx rate match and it is greater than zero')
                ixnet_session.info(f'Tx rate {tx_rate} and Rx rate {rx_rate}')
                self.assertTrue(compare_numbers(float(tx_rate), float(rx_rate), thresholdNum=0.99), "The TX rate matches Rx Rate")
                _location  = traff_name.split('_')[0]
                expected_latency = float(t_vars.ixia_latency_tests[_location]['latency']) * 1_000_000
                actual_latency = flowStat['Cut-Through Avg Latency (ns)']
                ixnet_session.info(f'Step {myStep.add()} - Test - for traffic {traff_name} - Check expected latency vc actual')
                ixnet_session.info(f'Expected {expected_latency} ns and Actual {actual_latency} ns')
                self.assertTrue(compare_numbers(float(expected_latency), float(actual_latency), thresholdNum=0.99),"The expected and actual latency matches")

            ixnet_session.info(f'Step {myStep.add()} - END -  Cleaning Up.')
            ixnet_session.info(f"Step {myStep.add_minor()} - Clean up - Stopping Traffic")
            stop_ixia_traffic(ixnet_session)

            time.sleep(5)
            ixnet_session.info(f"Step {myStep.add_minor()} - Clean up - Stopping Protocols")
            ixnet_session.StopAllProtocols()
            ixnet_session.info(f"Step {myStep.add_minor()} - Clean up - Releasing Ports")
            vport_dic["port1"].ReleasePort()
            vport_dic["port2"].ReleasePort()
            ixnet_session.info(f"Step {myStep.add_minor()} - Clean up - Reset Network Emulator 2")
            ne2.deleteAllProfiles()
            ixnet_session.info(f"Step {myStep.add_minor()} - Clean up - Cleaning up session and leaving it up...bye")
            ixnet_session.NewConfig()

            self.assertTrue(True)


def suite():
    suite = unittest.TestSuite()
    #suite.addTest(NeTests('test_baseline'))
    #suite.addTest(NeTests('test_port_policing'))
    suite.addTest(NeTests('test_latency'))

    
    return suite

if __name__ == '__main__':
    # Run the test suite
    runner = unittest.TextTestRunner()
    runner.run(suite())

