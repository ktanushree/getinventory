#! /usr/bin/env python

"""
Get Inventory
tanushree@cloudgenix.com
"""

import cloudgenix
import csv
import pandas as pd
import argparse
import sys
import os
import datetime
from cryptography.fernet import Fernet


SDK_VERSION = cloudgenix.version
SCRIPT_NAME = 'CloudGenix Inventory Generator'

HEADER = ["serial_number","model_name","model_type", "software_version", "site_name", "element_name", "element_role", "site_state", "element_state", "street", "city", "state", "country", "post_code", "longitude", "latitude"]


sys.path.append(os.getcwd())
try:
    from cloudgenix_settings import CLOUDGENIX_CRYPTKEY, CLOUDGENIX_AUTH_TOKEN
    print(CLOUDGENIX_CRYPTKEY,CLOUDGENIX_AUTH_TOKEN)

except ImportError:
    # Get AUTH_TOKEN/X_AUTH_TOKEN from env variable, if it exists. X_AUTH_TOKEN takes priority.
    if "X_AUTH_TOKEN" in os.environ:
        CLOUDGENIX_AUTH_TOKEN = os.environ.get('X_AUTH_TOKEN')
    elif "AUTH_TOKEN" in os.environ:
        CLOUDGENIX_AUTH_TOKEN = os.environ.get('AUTH_TOKEN')
    else:
        # not set
        CLOUDGENIX_AUTH_TOKEN = None

try:
    from cloudgenix_settings import CLOUDGENIX_USER, CLOUDGENIX_PASSWORD

except ImportError:
    # will get caught below
    CLOUDGENIX_USER = None
    CLOUDGENIX_PASSWORD = None


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

    login_group = parser.add_argument_group('Login', 'These options allow skipping of interactive login')
    login_group.add_argument("--email", "-E", help="Use this email as User Name instead of prompting",
                             default=None)
    login_group.add_argument("--pass", "-PW", help="Use this Password instead of prompting",
                             default=None)

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
    # figure out user
    if args["email"]:
        user_email = args["email"]
    elif CLOUDGENIX_USER:
        user_email = CLOUDGENIX_USER
    else:
        user_email = None

    # figure out password
    if args["pass"]:
        user_password = args["pass"]
    elif CLOUDGENIX_PASSWORD:
        user_password = CLOUDGENIX_PASSWORD
    else:
        user_password = None

    # check for token
    if CLOUDGENIX_AUTH_TOKEN and not args["email"] and not args["pass"]:
        cgx_session.interactive.use_token(CLOUDGENIX_AUTH_TOKEN)
        if cgx_session.tenant_id is None:
            print("AUTH_TOKEN login failure, please check token.")
            sys.exit()

    else:
        while cgx_session.tenant_id is None:
            cgx_session.interactive.login(user_email, user_password)
            # clear after one failed login, force relogin.
            if not cgx_session.tenant_id:
                user_email = None
                user_password = None


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
                                              "ship_state": machine["ship_state"]}
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
                                                   "state": elem["state"]}

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
                sites[site["id"]] = {"name": site["name"], "admin_state": site["admin_state"],
                                     "address": site["address"], "location": site["location"]}


        else:
            print("ERR: Failed to retrieve sites")
            cloudgenix.jd_detailed(resp)

        # Extract data from dicts for CSV
        hwidslist = list(dict.fromkeys(hwids))
        for item in hwidslist:
            site_name = "Unbound"
            element_name = "Unclaimed"
            element_role = "n/a"
            site_state = "n/a"
            element_state = "n/a"
            street = "n/a"
            city = "n/a"
            state = "n/a"
            country = "n/a"
            post_code = "n/a"
            longitude = "n/a"
            latitude = "n/a"
            model_type = None
            model_name = None

            curmachine = machines[item]
            ship_state = curmachine["ship_state"]
            software_version = curmachine["software_version"]
            model_name = curmachine["model_name"]

            if "v" in model_name:
                model_type = "Virtual"
            else:
                model_type = "Physical"

            if item in elements.keys():
                curelement = elements[item]
                software_version = curelement["software_version"]
                element_name = curelement["name"]
                element_state = curelement["state"]
                element_role = curelement["role"]

                site_id = curelement["site_id"]
                if site_id != "1":
                    cursite = sites[site_id]
                    site_name = cursite["name"]
                    site_state = cursite["admin_state"]
                    address = cursite["address"]

                    if address:
                        street = "{} {}".format(address.get("street",None),address.get("street2",None))
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