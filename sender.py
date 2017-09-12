from socket import *
from select import *
from random import *
import time
import sys
import segment

def tr_seg(data):
    seg_str = data.decode("UTF-8")
    self = segment.segment(syn = int(seg_str[0]),fin = int(seg_str[1]), ack = int(seg_str[2]),
                    seq_num = int(seg_str[3:11]),
                    ack_num = int(seg_str[11:19]), data = seg_str[19:])
    return self

def start(IP, port):
    global senderLog
    SNDADDR = (IP, int(port))
    Socket = socket(AF_INET, SOCK_DGRAM)
    seq = 0
    data = segment.segment(syn=1,seq_num=seq)
    Socket.sendto(data.seg, SNDADDR)
    senderLog.writelines("snd  %2.3f S %8d %3d %8d\n"%( time.time()%1*10, data.seq_num, len(data.data), 0 ))
    data,SNDADDR = Socket.recvfrom(1024)
    seg = tr_seg(data)
    senderLog.writelines("rcv  %2.3f SA%8d %3d %8d\n"%( time.time()%1*10, seg.seq_num, len(seg.data), seg.ack_num ))
    if seg.SYN == 1 and seg.ACK ==1:
        seq += 1
        Socket.sendto(segment.segment(ack=1, ack_num = seg.seq_num+1, seq_num=seq).seg, SNDADDR)
        senderLog.writelines("snd  %2.3f A %8d %3d %8d\n" % (time.time() % 1*10, seq, 0, seg.seq_num+1))
    else:
        Socket.close()
        exit("connect fail")
    return Socket,SNDADDR,seq,seg.seq_num+1

def receive():
    global ack_dup
    global sndW
    global last_ack
    global fastretrans

    inf, outf, errf = select([Socket, ], [], [], 0)
    recv_flag = False
    while inf:
        data, SNDADDR = inf[0].recvfrom(1024)
        seg = tr_seg(data)
        senderLog.writelines("rcv  %2.3f A %8d %3d %8d \n"
                            % (time.time() % 1*10, seg.seq_num, len(seg.data), seg.ack_num))

        if last_ack == seg.ack_num:
            ack_dup += 1
            fastretrans += 1
            if fastretrans >= 3:
                fastretrans = 0
                return "FR", 0
        else:
            fastretrans = 0
            last_ack = seg.ack_num
            for j in sndW:
                if seg.ack_num == j.seq_num + len(j.data):
                    sndW = sndW[sndW.index(j) + 1:]
                    freeW()
                    return "FW", 0

        inf, outf, errf = select([Socket, ], [], [], 0)
        for i in sndW:
            if i.send_time:
                if time.time() > i.send_time + timeout/1000:
                    return "TO",i
    return "NA",0


def PLD_send(segment):
    global Socket
    global SNDADDR
    global senderLog
    global seg_sent
    global seg_drop
    segment.send_time = time.time()
    rand = random()
    if rand+pdrop < 1:
        Socket.sendto(segment.seg, SNDADDR)
        seg_sent += 1
        senderLog.writelines("snd  %2.3f D %8d %3d %8d\n" %
                            (time.time() % 1*10, segment.seq_num, len(segment.data), segment.ack_num))
    else:
        seg_drop += 1
        senderLog.writelines("drop %2.3f D %8d %3d %8d\n"%( time.time()%1*10, segment.seq_num, len(segment.data), segment.ack_num))
    global data_amount
    data_amount += len(segment.data.encode("utf-8"))

def freeW():
    global sndW
    global file
    global nextseq
    global nextack
    global data
    while len(sndW) < MWS and data:
        sndW.append(segment.segment(data = str(data), seq_num = nextseq, ack_num=nextack))
        nextseq += len(data)
        data = file.read(MSS)
    lastW = 0
    if sndW:
        lastW = sndW[-1]
    return lastW

def finish(SNDADDR):
    global Socket
    global nextseq

    Socket.sendto(segment.segment(seq_num=nextseq + 2, fin=1).seg, SNDADDR)
    senderLog.writelines("snd  %2.3f F %8d %3d %8d\n" % (time.time() % 1*10, nextseq+2, 0, nextack))
    while True:
        inf, outf, errf = select([Socket, ], [], [], 0)
        if inf:
            data,SNDADDR = Socket.recvfrom(1024)
            seg = tr_seg(data)
            if seg.FIN == 1 and seg.ACK == 1:
                senderLog.writelines("rcv  %2.3f FA%8d %3d %8d\n" % (time.time() % 1*10, seg.seq_num, 0, seg.ack_num))
                Socket.sendto(segment.segment(seq_num=nextseq + 3, ack=1).seg, SNDADDR);
                senderLog.writelines("snd  %2.3f A %8d %3d %8d\n" % (time.time() % 1*10, seg.ack_num, 0, seg.seq_num+1))
                Socket.close()
                break


IP = sys.argv[1]
port = sys.argv[2]
read_file = sys.argv[3]
MWS_byte = int(sys.argv[4])
MSS = int(sys.argv[5])
MWS = MWS_byte // MSS
timeout= int(sys.argv[6])
pdrop = float(sys.argv[7])
seeds = int(sys.argv[8])
seed(seeds)
data_amount = 0
seg_sent = 0
seg_drop = 0
file = open(read_file)
ack_dup = 0
seg_retrans = 0
sndW = []
last_ack = -1
fastretrans = 0
senderLog = open("Sender_log.txt", "w")
Socket, SNDADDR, nextseq,nextack = start(IP,port)
data = file.read(MSS)
lastW = freeW()
wait_flag = False
while sndW:
    for i in sndW:
        if not wait_flag:
            status,packet = receive()
        if status == "NA":
            PLD_send(i)
        elif status == "TO":
            PLD_send(packet)
            PLD_send(i)
            seg_retrans += 1
        elif status == "FR":
            PLD_send(sndW[0])
            PLD_send(i)
            seg_retrans += 1
        elif status == "FW":
            if i in sndW:
                PLD_send(i)
            else:
                break

    wait_flag = False
    while status != "FW":
        wait_flag =True
        for i in sndW:
            status, packet = receive()
            if status == "FW":
                break
            if i.send_time:
                if time.time() > i.send_time + timeout / 1000:
                    seg_retrans += 1
                    PLD_send(i)

finish(SNDADDR)
senderLog.writelines("Amount of Data Transferred:%d\n"%data_amount)
senderLog.writelines("Number of Data Segments Sent:%d\n"%seg_sent)
senderLog.writelines("Number of Packets Dropped:%d\n"%seg_drop)
senderLog.writelines("Number of Retransmitted Segments:%d\n"%seg_retrans)
senderLog.writelines("Number of Duplicate Acknowledgements received:%d\n"%ack_dup)
