"""Nonblocking, bounded JSON/TCP transport for a two-player LAN room."""
import errno
import json
import select
import socket
import time

PORT=24872
PROTOCOL=8
MAX_PACKET=256*1024
MAX_BUFFER=2*1024*1024


def encode(message):
    raw=json.dumps(message,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')+b'\n'
    if len(raw)>MAX_PACKET:raise ValueError('Network message too large')
    return raw


def address(text):
    host,separator,port=text.strip().partition(':')
    if host=='localhost':host='127.0.0.1'
    socket.inet_aton(host)
    if len(host.split('.'))!=4:raise ValueError('Use an IPv4 address')
    port=int(port) if separator else PORT
    if not 1<=port<=65535:raise ValueError('Invalid port')
    return host,port


def local_addresses():
    try:ips=socket.gethostbyname_ex(socket.gethostname())[2]
    except OSError:ips=[]
    return sorted(set(x for x in ips if not x.startswith('127.'))) or ['127.0.0.1']


class Link:
    def __init__(self):
        self.listener=None;self.sock=None;self.connecting=False;self.connected=False
        self.incoming=bytearray();self.outgoing=bytearray();self.events=[]
        self.started=time.monotonic();self.last_rx=self.started;self.last_ping=self.started
        self.closed=False;self.port=PORT
    @classmethod
    def host(cls,port=PORT,interface='0.0.0.0'):
        link=cls();s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        try:s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind((interface,port));s.listen(1);s.setblocking(False)
        except OSError:s.close();raise
        link.listener=s;link.port=s.getsockname()[1];return link
    @classmethod
    def join(cls,text):
        target=address(text);link=cls();s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.setblocking(False)
        code=s.connect_ex(target)
        if code not in (0,errno.EINPROGRESS,errno.EWOULDBLOCK,errno.EALREADY,10035):
            s.close();raise OSError(code,'Cannot connect')
        link.sock=s;link.connecting=True;return link
    def send(self,message):
        if self.closed:return
        raw=encode(message)
        if len(self.outgoing)+len(raw)>MAX_BUFFER:self.close('Peer is too slow');return
        self.outgoing.extend(raw)
    def close(self,reason='Disconnected'):
        if self.closed:return
        self.closed=True;self.connected=False
        for s in (self.sock,self.listener):
            if s:
                try:s.close()
                except OSError:pass
        self.sock=self.listener=None;self.events.append({'type':'closed','reason':reason})
    def poll(self):
        now=time.monotonic()
        try:
            if self.listener:
                try:self.sock,_=self.listener.accept()
                except BlockingIOError:pass
                else:
                    self.sock.setblocking(False);self.sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1);self.listener.close();self.listener=None
                    self.connected=True;self.last_rx=now;self.events.append({'type':'connected'})
            if self.connecting:
                _,writable,errors=select.select([], [self.sock], [self.sock],0)
                if writable or errors:
                    code=self.sock.getsockopt(socket.SOL_SOCKET,socket.SO_ERROR)
                    if code:raise OSError(code,'Connection failed')
                    self.connecting=False;self.connected=True;self.sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1);self.last_rx=now;self.events.append({'type':'connected'})
                elif now-self.started>8:self.close('Connection timeout')
            if self.connected:
                if now-self.last_ping>1:self.send({'type':'ping'});self.last_ping=now
                if self.closed:
                    events=self.events;self.events=[];return events
                if self.outgoing:
                    try:sent=self.sock.send(self.outgoing)
                    except BlockingIOError:pass
                    else:del self.outgoing[:sent]
                for _ in range(8):
                    try:chunk=self.sock.recv(65536)
                    except BlockingIOError:break
                    if not chunk:self.close('Peer disconnected');break
                    self.last_rx=now;self.incoming.extend(chunk)
                    if len(self.incoming)>MAX_BUFFER:raise ValueError('Receive buffer limit')
                for _ in range(64):
                    end=self.incoming.find(b'\n')
                    if end<0:break
                    if end>MAX_PACKET:raise ValueError('Message limit')
                    raw=bytes(self.incoming[:end]);del self.incoming[:end+1]
                    message=json.loads(raw.decode('utf-8'),parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite number')))
                    if not isinstance(message,dict):raise ValueError('Invalid message')
                    if message.get('type')!='ping':self.events.append(message)
                if len(self.incoming)>MAX_PACKET and b'\n' not in self.incoming:raise ValueError('Unterminated message')
                if now-self.last_rx>12:self.close('Peer timed out')
        except (OSError,ValueError,UnicodeError,RecursionError) as exc:self.close(str(exc))
        events=self.events;self.events=[];return events
