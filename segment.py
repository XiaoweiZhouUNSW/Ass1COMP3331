class segment:
    def __init__(self, syn=0, fin=0, ack=0, seq_num=0, ack_num=0, data=""):
        self.SYN = syn
        self.FIN = fin
        self.ACK = ack
        self.ack_num = ack_num
        self.seq_num = seq_num
        self.data = data
        self.seg_str = str(self.SYN) + str(self.FIN) + str(self.ACK) + "{0:08d}".format(self.seq_num) + "{0:08d}".format(self.ack_num) + data
        self.seg = self.seg_str.encode("UTF-8")
        self.send_time = None
