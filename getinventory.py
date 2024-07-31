#! /usr/bin/env python

"""
Get Inventory
tkamath@paloaltonetworks.com

Version: 1.0.0 b4
Date: 07/31/2024
"""

import cloudgenix
import csv
import pandas as pd
import argparse
import sys
import os
import datetime


SDK_VERSION = cloudgenix.version
SCRIPT_NAME = 'Prisma SDWAN Inventory Generator'

HEADER = ["serial_number","model_name","model_type", "software_version", "site_name", "element_name", "element_role", "site_state", "element_state", "connected", "domain", "street", "city", "state", "country", "post_code", "longitude", "latitude"]


sys.path.append(os.getcwd())
try:
    from cloudgenix_settings import CLOUDGENIX_AUTH_TOKEN
    print(CLOUDGENIX_AUTH_TOKEN)

except ImportError:
    # Get AUTH_TOKEN/X_AUTH_TOKEN from env variable, if it exists. X_AUTH_TOKEN takes priority.
    if "X_AUTH_TOKEN" in os.environ:
        CLOUDGENIX_AUTH_TOKEN = os.environ.get('X_AUTH_TOKEN')
    elif "AUTH_TOKEN" in os.environ:
        CLOUDGENIX_AUTH_TOKEN = os.environ.get('AUTH_TOKEN')
    else:
        # not set
        CLOUDGENIX_AUTH_TOKEN = None


def getaddr(address):
    if address:
        for item in address.keys():
            if address[item] is None:
                address[item] = ""

        addr = "{} {} {} {} {} {}".format(address["street"], address["street2"],
                                          address["city"], address["state"],
                                          address["country"], address["post_code"])

        return addr
    else:
        return None



domain_id_name = {}
servicelabel_id_name = {}
serviceendpoint_id_name = {}
epid_dcsiteid = {}
dcsiteid_domainmaplist = {}
cg_service_labels = []



def getdomainmapping(cgx_session):

    # Service Labels
    resp = cgx_session.get.servicelabels()
    if resp.cgx_status:
        labels = resp.cgx_content.get("items", None)
        for lab in labels:
            if lab["type"] == "cg-transit":
                cg_service_labels.append(lab["id"])
                servicelabel_id_name[lab["id"]] = lab["name"]

    else:
        print("ERR: Could not retrieve service bindings")
        cloudgenix.jd_detailed(resp)

    # Service Endpoints
    resp = cgx_session.get.serviceendpoints()
    if resp.cgx_status:
        endpointlist = resp.cgx_content.get("items", None)
        for ep in endpointlist:
            if ep["type"] == "cg-transit":
                serviceendpoint_id_name[ep["id"]] = ep["name"]
                epid_dcsiteid[ep["id"]] = ep["site_id"]


    # Service Binding Maps
    resp = cgx_session.get.servicebindingmaps()
    if resp.cgx_status:
        domainlist = resp.cgx_content.get("items", None)

        for domain in domainlist:
            domain_id_name[domain["id"]] = domain["name"]

            service_bindings = domain["service_bindings"]

            for sb in service_bindings:
                label_id = sb["service_label_id"]

                if label_id in cg_service_labels:
                    service_endpoints = sb["service_endpoint_ids"]

                    domain_map = domain["name"] + "_" + servicelabel_id_name[label_id]

                    if service_endpoints is not None:
                        for ep in service_endpoints:
                            dcsiteid = epid_dcsiteid[ep]

                            if dcsiteid in dcsiteid_domainmaplist.keys():
                                domainmaplist = dcsiteid_domainmaplist[dcsiteid]
                                domainmaplist.append(domain_map)
                                dcsiteid_domainmaplist[dcsiteid] = domainmaplist

                            else:
                                dcsiteid_domainmaplist[dcsiteid] = [domain_map]

    else:
        print("ERR: Could not retrieve service bindings")
        cloudgenix.jd_detailed(resp)

    return


def go():
    ############################################################################
    # Begin Script, start login / argument handling.
    ############################################################################
    # Parse arguments
    parser = argparse.ArgumentParser(description="{0}.".format(SCRIPT_NAME))

    # Allow Controller modification and debug level sets.
    controller_group = parser.add_argument_group('API', 'These options change how this program connects to the API.')
    controller_group.add_argument("--controller", "-C",
                                  help="Controller URI, ex. "
                                       "C-Prod: https://api.cloudgenix.com",
                                  default=None)

    controller_group.add_argument("--insecure", "-I", help="Disable SSL certificate and hostname verification",
                                  dest='verify', action='store_false', default=True)


    debug_group = parser.add_argument_group('Debug', 'These options enable debugging output')
    debug_group.add_argument("--debug", "-D", help="Verbose Debug info, levels 0-2", type=int,
                             default=0)

    args = vars(parser.parse_args())

    ############################################################################
    # Instantiate API
    ############################################################################
    cgx_session = cloudgenix.API(controller=args["controller"], ssl_verify=args["verify"])
    cgx_session.set_debug(args["debug"])

    ############################################################################
    # Draw Interactive login banner, run interactive login including args above.
    ############################################################################

    print("{0} v{1} ({2})\n".format(SCRIPT_NAME, SDK_VERSION, cgx_session.controller))

    # login logic. Use cmdline if set, use AUTH_TOKEN next, finally user/pass from config file, then prompt.


    # check for token
    if CLOUDGENIX_AUTH_TOKEN:
        cgx_session.interactive.use_token(CLOUDGENIX_AUTH_TOKEN)
        if cgx_session.tenant_id is None:
            print("AUTH_TOKEN login failure, please check token.")
            sys.exit()

    ############################################################################
    # Get Service Bindings
    ############################################################################
    getdomainmapping(cgx_session)

    ############################################################################
    # Iterate through tenant_ids and get machines, elements and sites
    ############################################################################
    curtime_str = datetime.datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
    tenantname = cgx_session.tenant_name
    tenantname = tenantname.replace(" ","")
    tenantname = tenantname.replace("/","")


    filename = "{}/{}_inventory_{}.csv".format(os.getcwd(),tenantname,curtime_str)

    with open(filename, 'w') as csvfile:

        writer = csv.DictWriter(csvfile, fieldnames=HEADER)
        writer.writeheader()

        hwids = []
        machines = {}
        resp = cgx_session.get.machines()
        if resp.cgx_status:
            machinelist = resp.cgx_content.get("items", None)
            print("\tMachines: {}".format(len(machinelist)))

            for machine in machinelist:

                if machine['machine_state'] in ["claimed"]:
                    em_element_id = machine["em_element_id"]
                else:
                    em_element_id = "n/a"

                machines[machine["sl_no"]] = {"em_element_id": em_element_id, "model_name": machine["model_name"],
                                              "software_version": machine["image_version"],
                                              "ship_state": machine["ship_state"], "connected": machine["connected"]}
                hwids.append(machine["sl_no"])

        else:
            print("ERR: Failed to retrieve machines")
            cloudgenix.jd_detailed(resp)

        elements = {}
        elemid_siteid_dict = {}
        resp = cgx_session.get.elements()
        if resp.cgx_status:
            elemlist = resp.cgx_content.get("items", None)
            print("\tElements: {}".format(len(elemlist)))

            for elem in elemlist:
                elements[elem['serial_number']] = {"site_id": elem["site_id"],
                                                   "software_version": elem["software_version"],
                                                   "name": elem["name"], "role": elem["role"],
                                                   "state": elem["state"], "connected": elem["connected"]}

                elemid_siteid_dict[elem["id"]] = elem["site_id"]

        else:
            print("ERR: Failed to retrieve elements")
            cloudgenix.jd_detailed(resp)

        sites = {}
        resp = cgx_session.get.sites()
        if resp.cgx_status:
            sitelist = resp.cgx_content.get("items", None)
            print("\tSites: {}".format(len(sitelist)))

            for site in sitelist:
                if site["service_binding"] in domain_id_name.keys():
                    domain = domain_id_name[site["service_binding"]]
                else:
                    domain = "-"
                    if site["element_cluster_role"] == "HUB":
                        dcsiteid = site["id"]

                        if dcsiteid in dcsiteid_domainmaplist.keys():
                            domain = dcsiteid_domainmaplist[dcsiteid]



                sites[site["id"]] = {"name": site["name"], "admin_state": site["admin_state"],
                                     "address": site["address"], "location": site["location"],"domain": domain}


        else:
            print("ERR: Failed to retrieve sites")
            cloudgenix.jd_detailed(resp)

        # Extract data from dicts for CSV
        hwidslist = list(dict.fromkeys(hwids))
        for item in hwidslist:
            site_name = "Unbound"
            element_name = "Unclaimed"
            element_role = "-"
            site_state = "-"
            element_state = "-"
            connected = "-"
            street = ""
            city = ""
            state = ""
            country = ""
            post_code = ""
            longitude = ""
            latitude = ""
            domain = "-"
            model_type = None
            model_name = None

            curmachine = machines[item]
            ship_state = curmachine["ship_state"]
            software_version = curmachine["software_version"]
            model_name = curmachine["model_name"]
            connected = curmachine["connected"]

            if "v" in model_name:
                model_type = "Virtual"
            else:
                model_type = "Physical"

            if item in elements.keys():
                curelement = elements[item]
                software_version = curelement["software_version"]
                element_name = curelement["name"]
                element_state = curelement["state"]
                connected = curelement["connected"]
                element_role = curelement["role"]

                site_id = curelement["site_id"]
                if site_id != "1":
                    cursite = sites[site_id]
                    site_name = cursite["name"]
                    site_state = cursite["admin_state"]
                    address = cursite["address"]
                    domain = cursite["domain"]

                    if address:
                        street = address.get("street",None)
                        street2 = address.get("street2",None)
                        if street is None:
                            street = ""

                        if street2 is None:
                            street2 = ""

                        street = "{} {}".format(street,street2)
                        city = address.get("city")
                        state = address.get("state")
                        country = address.get("country")
                        post_code = address.get("post_code")

                    location = cursite["location"]
                    longitude = location["longitude"]
                    latitude = location["latitude"]


            writer.writerow({
                "serial_number": item,
                "model_name":model_name,
                "model_type":model_type,
                "software_version": software_version,
                "site_name": site_name,
                "element_name": element_name,
                "element_role": element_role,
                "site_state": site_state,
                "element_state": element_state,
                "connected": connected,
                "domain": domain,
                "street": street,
                "city": city,
                "state": state,
                "country": country,
                "post_code": post_code,
                "longitude": longitude,
                "latitude": latitude})


    #############################################################
    # Logout
    #############################################################
    print("INFO: Logging Out")
    cgx_session.get.logout()
    sys.exit()


if __name__ == "__main__":
    go()
