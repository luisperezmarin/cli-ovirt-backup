import time
import os
import click
import logging
import ovirtsdk4 as sdk
import ovirtsdk4.types as types
from cliobrlib import *


FORMAT = '%(asctime)s %(levelname)s %(message)s'
logging.basicConfig(level=logging.DEBUG, format=FORMAT, filename='example.log')
AgentVM = 'backuprestore'
Description = 'cli-ovirt-backup'


@click.group()
def cli():
    pass


@cli.command()
@click.argument('vmname')
@click.option(
    '--username', '-u', envvar='OVIRTUSER', default='admin@internal', show_default=True, help='username for oVirt API'
)
@click.option(
    '--password', '-p', envvar='OVIRTPASS', required=True, help='password for oVirt user'
)
@click.option(
    '--ca', '-c', envvar='OVIRTCA', required=True, type=click.Path(), help='path for ca certificate of Manager'
)
@click.option(
    '--url', '-U', envvar='OVIRTURL', required=True, help='url for oVirt API https://manager.example.com/ovirt-engine/api'
)
@click.option('--debug', is_flag=True, default=False, help='debug mode')
def backup(username, password, ca, vmname, url, debug):
    connection = sdk.Connection(
        url=url,
        username=username,
        password=password,
        ca_file=ca,
        debug=debug,
        log=logging.getLogger(),
    )
    logging.info('Connected to the server.')
    if debug:
        click.echo('Connected to the server.')

    # Get the reference to the root of the services tree:
    system_service = connection.system_service()

    # Get the reference to the service that we will use to send events to
    # the audit log:
    events_service = system_service.events_service()

    # In order to send events we need to also send unique integer ids. These
    # should usually come from an external database, but in this example we
    # will just generate them from the current time in seconds since Jan 1st
    # 1970.
    event_id = int(time.time())

    # Get the reference to the service that manages the virtual machines:
    vms_service = system_service.vms_service()

    vm = vmobj(vms_service, vmname)
    logging.info(
        'Found data virtual machine \'{}\', the id is \'{}\'.'.format(
            vm.name, vm.id)
    )
    if debug:
        click.echo(
            'Found data virtual machine \'{}\', the id is \'{}\'.'.format(vm.name, vm.id))
    vmAgent = vmobj(vms_service, AgentVM)
    logging.info(
        'Found data virtual machine \'{}\', the id is \'{}\'.'.format(
            vmAgent.name, vmAgent.id)
    )
    if debug:
        click.echo(
            'Found data virtual machine \'{}\', the id is \'{}\'.'.format(vm.name, vm.id))
    # Find the services that manage the data and agent virtual machines:
    data_vm_service = vms_service.vm_service(vm.id)
    agent_vm_service = vms_service.vm_service(vmAgent.id)

    send_events(events_service, event_id, types, vm, Description)

    ovf_file = writeconfig(vm)
    logging.info('Wrote OVF to file \'{}\''.format(
        os.path.abspath(ovf_file)))
    if debug:
        click.echo('Wrote OVF to file \'{}\''.format(
            os.path.abspath(ovf_file)))

    snaps_service = data_vm_service.snapshots_service()

    snap = createsnapshot(snaps_service, types, Description)
    logging.info('Sent request to create snapshot \'{}\', the id is \'{}\'.'.format(
        snap.description, snap.id))
    if debug:
        click.echo('Sent request to create snapshot \'{}\', the id is \'{}\'.'.format(
            snap.description, snap.id))

    snap_service = snaps_service.snapshot_service(snap.id)
    waitingsnapshot(snap, types, logging, time, snap_service, click, debug)

    # Retrieve the descriptions of the disks of the snapshot:
    snap_disks_service = snap_service.disks_service()
    snap_disks = snap_disks_service.list()

    # Attach disk service
    attachments_service = agent_vm_service.disk_attachments_service()
    attachments = []
    populateattachments(snap_disks, snap, attachments,
                        attachments_service, types, logging, click, debug)

    disks = disksattachments(attachments, logging, debug, click)
    click.echo(disks)
    # Finish the connection to the VM Manager
    connection.close()
    logging.info('Disconnected to the server.')
    if debug:
        click.echo('Disconnected to the server.')


@cli.command()
@click.argument('vmname')
@click.option(
    '--username', '-u', envvar='OVIRTUSER', help='username for oVirt API'
)
@click.option(
    '--password', '-p', envvar='OVIRTPASS', help='password for oVirt user'
)
def restore(username, password, vmname):
    click.echo('{} {} {}'.format(username, password, vmname))
