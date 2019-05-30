import pymongo
from bson.objectid import ObjectId
import os
import subprocess

serial_number = '2003080800'
refresh = '172800'
update_retry = '900'
expiry = '1209600'
ttl = '3600'

client = pymongo.MongoClient('mongodb://192.168.56.1:27017/')
db = client['licenta']
collection = db['zones']

object = collection.find_one({'_id': ObjectId("5cd5c0dbedb355c0a630e15a")})
zone_file_path = '/var/named/{0}.zone'.format(object['domain'])

# check if a zone file for this domain already exists
if os.path.isfile(zone_file_path):
    print("zone file already exists")
    exit(-1)

with open(zone_file_path, "w+") as zone_file:
    zone_file.write('$ORIGIN ' + object['domain'] + '.' + '\n')   # $ORIGIN domain1.org.

    if 'ttl' in object:                                           # $TTL 86400
        ttl = object['ttl']

    zone_file.write('$TTL ' + ttl + '\n')

    zone_file.write('@\tIN\tSOA\tns1.' + object['domain'] + '.'
                    + '\t' + object['admin_mail'].repalce('@', '.')
                    + '. (' + serial_number + ' ' + refresh + ' '
                    + update_retry + ' ' + expiry + ' ' + ttl + ')\n')

    zone_file.write('\tIN\tNS\t' + 'ns1.' + object['domain'] + '.\n')
    zone_file.write('\tIN\tMX\t' + object['mail_priority'] + '\t' + object['mail_host'] + '.' + object['domain'] + '.\n')
    zone_file.write('\tIN\t' + object['ip_addr_type'] + '\t' + object['ip_address'] + '\n')
    zone_file.write('ns1\tIN\t' + object['ip_addr_type'] + '\t' + object['ip_address'] + '\n')
    zone_file.write(object['mail_host'] + '\tIN\tA\t' + object['mail_ip_host'] + '\n')
    zone_file.write(object['ip_host'] + '\tIN\t' + object['ip_addr_type'] + '\t' + object['ip_address'] + '\n')


dns_config_file_path = '/etc/named.conf'
with open(dns_config_file_path, 'a+') as file:
    file.write('\n')
    file.write('zone \"' + object['domain'] + '\" IN {\n')
    file.write('\ttype master;\n')
    file.write('\tfile \"' + object['domain'] + '.zone\";\n')
    file.write('};\n')

# reload bind9 server
subprocess.check_output(['systemctl', 'restart', 'named.service'])


