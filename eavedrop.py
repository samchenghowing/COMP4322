from scapy.all import *
from scapy.layers.inet import TCP

def packet_callback(packet):
    if packet.haslayer(TCP):
        print(packet.summary())
        print(packet.show())
        
if __name__ == "__main__":
    pkts = sniff(filter="port 12345", prn=packet_callback, count=20)
    wrpcap('eavedrop.pcap', pkts)