from socket import *
from datetime import date
import threading, logging, os

class clientThread(threading.Thread):
    """This class is use to create a client thread to listen connection from others"""

    def __init__(self, ip, port, socket):
        """Overriding the thread init funtion, added ip, port, socket parameter for this thread"""
        
        threading.Thread.__init__(self)
        self.ip = ip
        self.port = port
        self.socket = socket
        self.live = True
        logging.getLogger('secureChat').info("[+] New thread started for "+ip+":"+str(port))

    def run(self):
        """Overriding the thread run funtion, this fuction will get the client's request and response"""
        
        while (self.live == True):
            clientStr = self.socket.recv(1024).decode()
            logging.getLogger('secureChat').info("Receive the folling message from sender with IP:", self.ip + "\n" + clientStr)
            print("Receive the folling message from sender with IP:", self.ip + "\n" + clientStr)

        self.socket.close()
        logging.getLogger('secureChat').info("Disconnected to client ..., killing thread for: " +self.ip+":"+str(self.port)) 
        return

class inputThread(threading.Thread): 
    """This class is use to create a input thread to receive input from terminal"""

    def __init__(self):
        """Overriding the thread init funtion, added destination's IP parameter for this thread"""

        threading.Thread.__init__(self)
        self.destIP = ""
    
    def run(self):
        while (1):
            if self.destIP == "":
                self.destIP = input("please input your target receiver's IP address")
                self.udpSock = socket(AF_INET, SOCK_STREAM)
                self.udpSock.connect((self.destIP, 12345)) # input 127.0.0.1 for localhost testing
            else:
                dataSend = input("please input the message you want to send to:" + self.destIP) + "\n"
                self.udpSock.send(dataSend.encode("utf-8"))

def initLogger():
    """Create a logger and log file named with today's day + connectionLog.txt """
    today = date.today()
    if not os.path.exists("Logs"):
        os.makedirs("Logs")
    logging.basicConfig(filename=f'Logs/{today.strftime("%d%m%y") + "connectionLog.txt"}',
                        filemode='a',
                        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S',
                        level=logging.DEBUG)

def run(port=12345): # defalult blind to local IP and port 12345
    """Accept the port parameter and start to listen connections from sender with corresponding port number.
        When new connection received from client, it will create a new thread from class clientThread to handle it"""
    
    try:
        initLogger()

        listenerSocket = socket(AF_INET, SOCK_STREAM)
        listenerSocket.bind(("", port))
        threads = []


        inputT = inputThread()
        inputT.start()
        threads.append(inputT)

 
        while True:
            listenerSocket.listen(5) # max 5 incoming connections
            logging.getLogger('secureChat').info("Listening for incoming connections on port:" + str(port) + "...\n")
            (clientsock, (clientIP, clientPort)) = listenerSocket.accept()
            newthread = clientThread(clientIP, clientPort, clientsock)
            newthread.start()
            threads.append(newthread)

        for t in threads:
            t.join()
        
        listenerSocket.close()

        logging.getLogger('secureChat').info('Stopping ...\n')

    except socket.error as e:
            logging.getLogger('secureChat').info(e)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    """Main function of the program, it could take one argument as server's port number"""
    from sys import argv
    
    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
