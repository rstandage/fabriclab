#!/usr/bin/env python3

import os, random

GREEN = "\033[32m"

def gen_mac():
    first_byte = random.randint(0x00, 0xFE) & 0xFE
    mac = [first_byte] + [random.randint(0x00, 0xFF) for _ in range(5)]
    mac_address = ':'.join([f'{byte:02X}' for byte in mac])
    return mac_address

def generate_vm_config(vm_id, name):
    config_template = """# Config for {} created automatically
args: -smbios type=1,product=VM-VSRX -chardev socket,id=serial0,port=5{},host=0.0.0.0,server=on,wait=off,telnet=on -device isa-serial,chardev=serial0
boot: order=virtio0
cores: 4
cpu: host
memory: 8192
name: {}.fw
net0: virtio={},bridge=vmbr101
net1: virtio={},bridge=vmbr500
net2: virtio={},bridge=vmbr500
numa: 0
onboot: 1
ostype: l24
scsihw: virtio-scsi-single
sockets: 1
virtio0: local-lvm:vm-{}-disk-0,iothread=1,size=18440M
""".format(name, vm_id, name, gen_mac(), gen_mac(), gen_mac(), vm_id)
    return config_template

def main():
    name = input("Enter vm_name: ")
    vm_id = input("Enter vm_id: ")
    cmd1 = "touch /etc/pve/qemu-server/{}.conf".format(vm_id)
    os.system(cmd1)
    cmd2 = "qm importdisk {} /var/lib/vz/template/qcow/vJunos-switch-23.2R1.14.qcow2 local-lvm".format(vm_id)
    os.system(cmd2)
    config = generate_vm_config(vm_id,name)	
    with open("/etc/pve/qemu-server/{}.conf".format(vm_id), "w") as config_file:
        config_file.write(config)
    print(" Config file created: /etc/pve/qemu-server/{}.conf".format(vm_id))

if __name__ == '__main__':
	main()
