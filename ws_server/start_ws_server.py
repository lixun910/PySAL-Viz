from SimpleWebSocketServer import WebSocket, SimpleWebSocketServer
import json
    
ACTIVE_WPCLIENTS = set()

class WSPySAL(WebSocket):

    def handleMessage(self):
        if self.data is None:
            self.data = ''
            
        print 'receive msg', self.data
        # echo message back to client
        for client in self.server.connections.itervalues():
            if client != self:
                try:
                    client.sendMessage(str(self.data))
                except Exception as n:
                    print 'err:',n

    def handleConnected(self):
        print self.address, 'connected'
        global ACTIVE_WPCLIENTS
        ACTIVE_WPCLIENTS.add(self.address)        
        for client in self.server.connections.itervalues():
            if client != self:
                try:
                    client.sendMessage(str(self.address[0]) + ' - connected')
                except Exception as n:
                    print 'err:',n

    def handleClose(self):
        print self.address, 'closed'
        global ACTIVE_WPCLIENTS
        ACTIVE_WPCLIENTS.remove(self.address)        
        for client in self.server.connections.itervalues():
            if client != self:
                try:
                    client.sendMessage(str(self.address[0]) + ' - disconnected')
                except Exception as n:
                    print 'err:', n


server = SimpleWebSocketServer('', 9000, WSPySAL)
server.serveforever()
print "Serving PySAL WebSocket server on port 9000..."

