import sys
import socket
import time
import select
import struct


class netGPIB:
    def __init__(self, ip: str, gpibAddr: int, eot: str = '\004', debug: int = 0, auto: bool = False):

        # End of Transmission character
        self.eot = eot
        # EOT character number in the ASCII table
        self.eotNum = struct.unpack('B', eot.encode())[0]

        # Debug flag
        self.debug = debug

        # Auto mode
        self.auto = auto

        self.ip = ip
        self.gpibAddr = gpibAddr
        self.timeout = 100

        # Connect to the GPIB-Ethernet converter
        netAddr = (ip, 1234)
        self.netSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.netSock.settimeout(100)
        self.netSock.connect(netAddr)

        # Initialize the GPIB-Ethernet converter
        self.netSock.setblocking(0)
        self._init_controller()

    def _init_controller(self) -> None:
        """Send initialization commands to the GPIB-Ethernet controller."""
        auto_flag = "1" if self.auto else "0"
        cmds = [
            f"++addr {self.gpibAddr}\n",
            "++eos 3\n",
            "++mode 1\n",
            f"++auto {auto_flag}\n",
            "++ifc\n",
            "++read_tmo_ms 3000\n",
            f"++eot_char {self.eotNum}\n",
            "++eot_enable 1\n",
            f"++addr {self.gpibAddr}\n",
        ]
        for cmd in cmds:
            self.netSock.send(cmd.encode())
            time.sleep(0.1)

    def refresh(self) -> None:
        """Re-send initialization commands to reset the controller state."""
        self._init_controller()

    def getData(self, buf: int, sleep: float = 0.1) -> str:
        """Read data from the socket until the EOT character is received."""
        data = ""
        dlen = 0

        while True:  # Repeat reading until EOT is found
            readSock, _, _ = select.select([self.netSock], [], [], self.timeout)
            if not readSock:
                raise RuntimeError(
                    f"Socket read timed out after {self.timeout}s waiting for data from {self.ip}"
                )

            data1 = readSock[0].recv(buf).decode('latin-1')

            if self.debug:
                dlen += len(data1)
                sys.stdout.write(f'\r{dlen} bytes received')
                sys.stdout.flush()

            if data1[-1] == self.eot:  # EOT found at end of chunk
                data += data1[:-1]     # Strip EOT and stop
                break
            else:
                data += data1
                time.sleep(sleep)

        if self.debug:
            sys.stdout.write(f'\r{dlen} bytes received\n')
            sys.stdout.flush()

        return data

    def query(self, string: str, buf: int = 100, sleep: float = 0) -> str:
        """Send a query to the device and return the result."""
        self.netSock.send(string.encode() + b"\n")
        if not self.auto:
            time.sleep(sleep)
            self.netSock.send("++read eoi\n".encode())  # Switch to listening mode
        return self.getData(buf)

    def command(self, string: str, sleep: float = 0) -> None:
        """Send a command to the device."""
        self.netSock.send(string.encode() + b"\n")
        time.sleep(sleep)

    def spoll(self) -> bytes:
        """Perform a serial poll and return the result."""
        self.netSock.send("++spoll\n".encode())
        readSock, _, _ = select.select([self.netSock], [], [], 3)
        if not readSock:
            raise RuntimeError(f"Serial poll timed out waiting for response from {self.ip}")
        data = readSock[0].recv(100)
        return data[:-2]

    def close(self) -> None:
        """Close the socket connection."""
        self.netSock.close()

    def setDebugMode(self, debugFlag: bool) -> None:
        self.debug = bool(debugFlag)


def gpibGetData(netSock: socket.socket, buf: int, eot: str, debug: bool = False) -> str:
    """Standalone helper: read data from a raw socket until EOT is found."""
    data = ""

    while True:  # Repeat reading until EOT is found
        readSock, _, _ = select.select([netSock], [], [], 3)
        if not readSock:
            raise RuntimeError("Socket read timed out in gpibGetData")

        data1 = readSock[0].recv(buf).decode('latin-1')

        if debug:
            print(f'{len(data1)} bytes received')

        if data1[-1] == eot:        # EOT found at end of chunk
            data += data1[:-1]      # Strip EOT and stop
            break
        else:
            data += data1
            time.sleep(1)

    return data
