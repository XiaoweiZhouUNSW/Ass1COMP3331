from socket import *
from select import *
import sys
import segment

def encode(data):
    seg_str = data.decode("UTF-8")
    self = segment.segment(syn = int(seg_str[0]),fin = int(seg_str[1]), ack = int(seg_str[2]),
                    seq_num = int(seg_str[3:11]),
                    ack_num = int(seg_str[11:19]), data = seg_str[19:])
    return self

def start(port):
    RCVADDR = ('127.0.0.1', int(port))
    Socket = socket(AF_INET, SOCK_DGRAM)  
    Socket.bind(RCVADDR)
    data,RCVADDR = Socket.recvfrom(1024)  
    seg = encode(data)
    if seg.SYN == 1:
        Socket.sendto(segment.segment(syn=1, ack=1, seq_num=0, ack_num=seg.seq_num+1).seg, RCVADDR)
    data,RCVADDR = Socket.recvfrom(1024)  
    seg = encode(data)

    if seg.ACK == 1:
        return Socket,seg.seq_num, RCVADDR,1
    else:
        Socket.close()
        exit("Fail to connect")

port = sys.argv[1]
file_name = sys.argv[2]
Socket, ack, RCVADDR, sequence_number =start(port)
f=open(file_name,'w')
log_file = open("Receiver_log.txt", "w")
data_amount = 0
seg_count = 0
seg_dup = 0

while True:
    inf, outf, errf = select([Socket, ], [], [], 0)
    if inf:
        data,RCVADDR = Socket.recvfrom(1024)
        seg = encode(data)
        line = seg.data
        print(seg.seq_num);
        if seg.FIN == 1:
            Socket.sendto(segment.segment(ack_num=seg.seq_num+3, seq_num=sequence_number, fin=1, ack=1).seg, RCVADDR)
            data,RCVADDR = Socket.recvfrom(1024)
            seg = encode(data);
            if seg.ACK == 1:
                Socket.close()
                break
        if ack == seg.seq_num:
            ack = seg.seq_num + len(line)
            f.write(line)
        else:
            seg_dup += 1
        seg_count += 1
        data_amount += len(seg.data.encode("UTF-8"))
        send_seg = segment.segment(ack_num=ack, seq_num=sequence_number, ack=1)
        Socket.sendto(send_seg.seg, RCVADDR)

log_file.writelines("Amount of Data Received:%d\n"%data_amount)
log_file.writelines("Number of Data Segments Received:%d\n"%seg_count)
log_file.writelines("Number of duplicate segments received:%d\n"%seg_dup)
