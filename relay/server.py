"""Mistvale room relay. Run python server.py on a public host with UDP 31975 open."""
import secrets
import socket
import time

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", 31975))
sock.settimeout(1)
rooms = {}
while True:
    now = time.monotonic()
    for room, state in list(rooms.items()):
        if now - state["host"][2] > 20:
            del rooms[room]
        else:
            state["peers"] = {k: v for k, v in state["peers"].items() if now - v[2] <= 20}
    try:
        packet, address = sock.recvfrom(65535)
        header, body = packet.split(b"\n", 1)
        op, room, token, dest = header.decode("ascii").split(" ")
        if len(room) != 12 or len(token) != 32 or not room.isalnum():
            continue
        state = rooms.get(room)
        entry = (address, token, now)
        if op == "H":
            if not state and len(rooms) < 1024:
                rooms[room] = {"host": entry, "peers": {}}
            elif state and state["host"][:2] == entry[:2]:
                state["host"] = entry
        elif state:
            peers = state["peers"]
            key = next((k for k, v in peers.items() if v[:2] == entry[:2]), None)
            if op == "L" and key:
                del peers[key]
            elif op == "J" and (key or len(peers) < 3):
                peers[key or secrets.token_hex(4)] = entry
            elif op == "D" and state["host"][:2] == entry[:2] and dest in peers:
                sock.sendto(b"C\n" + body, peers[dest][0])
            elif op == "D" and key:
                sock.sendto(key.encode() + b"\n" + body, state["host"][0])
    except (ValueError, UnicodeError, OSError):
        continue

