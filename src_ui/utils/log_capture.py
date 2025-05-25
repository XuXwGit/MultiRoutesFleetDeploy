from io import StringIO

class LogCapture:
    def __init__(self, callback):
        self.callback = callback
        self.buffer = StringIO()

    def write(self, message):
        self.buffer.write(message)
        if message.strip():
            self.callback(message.strip())

    def flush(self):
        pass 