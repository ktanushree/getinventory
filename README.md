# Prisma SD-WAN Get Inventory
This utility is used to download inventory Prisma SD-WAN (CloudGenix) managed network to a CSV file.

#### Synopsis
Enables downloading inventory information and relavant information such as location, site and element state to a CSV file.


#### Requirements
* Active CloudGenix Account
* Python >=3.6
* Python modules:
    * CloudGenix Python SDK >= 5.5.3b1 - <https://github.com/CloudGenix/sdk-python>
* ProgressBar2

#### License
MIT

#### Installation:
 - **Github:** Download files to a local directory, manually run `getinventory.py`. 

### Usage:
```
./getinventory.py
```

Help Text:
```angular2
Tanushrees-MacBook-Pro:getinventory tanushreekamath$ ./getinventory.py -h
usage: getinventory.py [-h] [--controller CONTROLLER] [--insecure]
                       [--email EMAIL] [--pass PASS] [--debug DEBUG]

CloudGenix Inventory Generator.

optional arguments:
  -h, --help            show this help message and exit

API:
  These options change how this program connects to the API.

  --controller CONTROLLER, -C CONTROLLER
                        Controller URI, ex. C-Prod: https://api.cloudgenix.com
  --insecure, -I        Disable SSL certificate and hostname verification

Login:
  These options allow skipping of interactive login

  --email EMAIL, -E EMAIL
                        Use this email as User Name instead of prompting
  --pass PASS, -PW PASS
                        Use this Password instead of prompting

Debug:
  These options enable debugging output

  --debug DEBUG, -D DEBUG
                        Verbose Debug info, levels 0-2
Tanushrees-MacBook-Pro:getinventory tanushreekamath$ 


```

#### Version
| Version | Build | Changes |
| ------- | ----- | ------- |
| **1.0.0** | **b4** | Removed support for authentication using username and password|
|           | **b3** | Updated script to include device connection state|
|           | **b2** | Updated script to include domains (Service Binding Map)|
|           | **b1** | Initial Release. |


#### For more info
 * Get help and additional CloudGenix Documentation at <http://support.cloudgenix.com>
 
