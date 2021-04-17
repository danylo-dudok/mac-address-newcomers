from dataclasses import dataclass

BROADCASTING_MAC_ADDRESS = 'ff:ff:ff:ff:ff:ff'


@dataclass
class Person:
    mac: str
    manufacturer: str


@dataclass
class People:
    newcomers: list
    left: list
    connected: list


def get_manufacturer(mac_address: str) -> str or None:
    from requests import get
    response = get(f'https://api.macvendors.com/{mac_address}')
    if response.status_code == 200:
        return response.content


def get_clients(ip: str) -> list[dict[str, any]]:
    from scapy.all import srp
    from scapy.layers.l2 import ARP, Ether

    arp = ARP(pdst=ip)
    ether = Ether(dst=BROADCASTING_MAC_ADDRESS)
    packet = ether / arp

    srps = srp(packet, timeout=3, verbose=0)

    return [
        {'ip': received.psrc, 'mac': received.hwsrc}
        for sent, received in srps[0]
    ]


def get_clients_manufacturers(mac_addresses: list[str]) -> list[dict[str, str]]:
    return [
        { 'mac': mac, 'manufacturer': get_manufacturer(mac) }
        for mac in mac_addresses
        if mac
    ]


def find_mac_addresses(router_ip: str) -> list[str]:
    clients = get_clients(router_ip)
    return [
        client['mac']
        for client in clients
    ]


cache = []


def find_people(connected: list, router_ip: str, ignore_addresses: list[str]) -> People:
    people = People(
        newcomers=[],
        left=[],
        connected=[*connected]
    )
    connected_addresses = [
        address
        for address in find_mac_addresses(router_ip)
        if address and address not in ignore_addresses
    ]
    addresses_to_get = []

    for address in connected_addresses:
        existing = [c for c in cache if c.mac == address]
        existing_mac = existing[0] if len(existing) else None
        if not existing_mac:
            addresses_to_get.append(address)

    if len(addresses_to_get):
        client_manufacturers = [
            Person(mac=client['mac'], manufacturer=client['manufacturer'])
            for client in get_clients_manufacturers(addresses_to_get)
        ]
        cache.extend([
            client
            for client in client_manufacturers
            if all(client.mac != cached.mac for cached in cache)
        ])

        for client in client_manufacturers:
            mac = client.mac
            if all(mac != c.mac for c in people.connected):
                people.connected.append(client)
                people.newcomers.append(client)

        for connected_client in [*people.connected]:
            mac = connected_client.mac
            if mac not in connected_addresses:
                people.connected.remove(connected_client)
                people.left.append(connected_client)

    return people


def main() -> None:
    def print_people(people: People) -> None:
        for client in people.newcomers:
            print(f'New client connected: {client}')
        print('\n')
        for client in people.left:
            print(f'Client left: {client}')
        print('\n')

        print(f'Connected: {people.connected}')
        print('\n\n\n\n')

    def freeze() -> None:
        from time import sleep
        sleep(2)

    ROUTER_IP = '192.168.0.1/24'
    MY_MAC_ADDRESSES = [
        # your devices
    ]
    current_people = []

    while True:
        people = find_people(current_people, ROUTER_IP, MY_MAC_ADDRESSES)
        current_people = people.connected
        print_people(people)
        freeze()


if __name__ == '__main__':
    main()
