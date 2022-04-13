import json
import traceback
from fabrictestbed_extensions.fablib.fablib import fablib
from fabrictestbed_extensions.fablib.resources import Resources


class CloudResources:
    def __init__(self, *, slice_name: str, node_name_prefix: str = "node", site: str = "MAX",
                 image: str = "default_rocky_8", node_count: int = 1):
        """ Constructor """
        self.slice_name = slice_name
        self.node_count = node_count # number of nodes to create
        self.node_name_prefix = node_name_prefix
        self.site = site
        self.image = image
        self.slice_id = None

    def get_available_resources(self) -> Resources:
        try:
            available_resources = fablib.get_available_resources()
            print(f"Available Resources: {available_resources}")
            return available_resources
        except Exception as e:
            print(f"Error: {e}")

    def create_resources(self):
        try:
            # Create Slice
            slice_object = fablib.new_slice(self.slice_name)

            interface_list = []

            # Add node
            for i in range(self.node_count):
                node_name = f"{self.node_name_prefix}{i}"
                node = slice_object.add_node(name=node_name, site=self.site, image=self.image)

                iface = node.add_component(model='NIC_Basic', name=f"{node_name}-nic1").get_interfaces()[0]
                interface_list.append(iface)

            # Network
            net1 = slice_object.add_l3network(name=f"{self.slice_name}-network", interfaces=interface_list, type='IPv4')

            # Submit Slice Request
            self.slice_id = slice_object.submit()

        except Exception as e:
            print(f"{e}")

    def delete_resources(self):
        try:
            if self.slice_id is not None:
                slice_object = fablib.get_slice(slice_id=self.slice_id)
            else:
                slice_object = fablib.get_slice(self.slice_name)
            slice_object.delete()
        except Exception as e:
            print(f"Fail: {e}")