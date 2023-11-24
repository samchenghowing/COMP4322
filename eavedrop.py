from scapy.all import *

def packet_callback(packet):
    # Process the captured packet here
    # You can access packet fields and perform actions based on your requirements
    # For example, you can check if the packet has a specific source or destination port
    if packet.haslayer(TCP) and (packet[TCP].sport == "127.0.0.1" or packet[TCP].dport == 12345):
        print(packet.summary())
        
sniff(filter="tcp", prn=packet_callback)