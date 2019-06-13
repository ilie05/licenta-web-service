import pymongo
from bson.objectid import ObjectId
import os
import subprocess

serial_number = '2003080800'
refresh = '172800'
update_retry = '900'
expiry = '1209600'
nxdomain_ttl = '3600'

client = pymongo.MongoClient('mongodb://192.168.56.1:27017/')
db = client['licenta']
collection = db['zones']

# object = collection.find_one({'_id': ObjectId("5cd5c0dbedb355c0a630e15a")})
# zone_file_path = '/var/named/{0}.zone'.format(object['domain'])

last_record = collection.find({}).sort('_id', pymongo.DESCENDING).limit(1)[0]
print(last_record)

# exit(0)
# # check if a zone file for this domain already exists
# if os.path.isfile(zone_file_path):
#     print("zone file already exists")
#     exit(-1)

zone_folder = 'var/named/'


def create_zone_file(record):
    domain_details = record['domain_details']
    ns_records = record['ns_records']
    hosts_records = record['hosts_records']
    mails_records = record['mails_records']

    zone_file_path = '{0}{1}.zone'.format(zone_folder, domain_details['domain_name'])

    # delete file if exists
    if os.path.isfile(zone_file_path):
        os.remove(zone_file_path)

    """
    TODO: Delete reference from   /etc/named.conf   file
    """

    # 'w+' mode create if not exists and overwrites the content
    with open(zone_file_path, "w+") as zone_file:

        zone_file.write('$ORIGIN {}.\n'.format(domain_details['domain_name']))  # $ORIGIN domain1.org.

        if 'domain_ttl' in domain_details:
            domain_ttl = domain_details['domain_ttl']

        zone_file.write('$TTL\t{}\n'.format(domain_ttl))   # $TTL 86400

        original_admin_mail = domain_details['original_admin_mail']
        if original_admin_mail.split('@')[-1] == domain_details['domain_name']:
            admin_mail = original_admin_mail.split('@')[0]
        else:
            admin_mail = domain_details['admin_mail'] + '.'

        # SOA record
        zone_file.write('@\tIN\tSOA\t{0}.{1}. {2} ({3} {4} {5} {6} {7})\n'.format(ns_records[0]['ns'],
                                                                                  domain_details['domain_name'],
                                                                                  admin_mail, serial_number, refresh,
                                                                                  update_retry, expiry, nxdomain_ttl))

        zone_file.write("\n\n; Name server records\n\n")
        # NS records
        for record in ns_records:
            ns_ttl = record['ns_ttl']
            if not ns_ttl:
                ns_ttl = ''
            zone_file.write('\t\tIN\tNS\t{0}\n'.format(record['ns']))
            zone_file.write(
                '{0}\t{1}\tIN\t{2}\t{3}\n'.format(record['ns'], ns_ttl, record['ns_ip_addr_type'], record['ns_ip']))
            zone_file.write("\n")

        zone_file.write("\n; Host records\n\n")
        # HOST records
        for record in hosts_records:
            host_name_ttl = record['host_name_ttl']
            if not host_name_ttl:
                host_name_ttl = ''
            zone_file.write(
                '{0}\t{1}\tIN\t{2}\t{3}\n'.format(record['host_name'], host_name_ttl, record['host_name_ip_addr_type'],
                                                  record['host_name_ip']))
            if record['host_cname']:
                zone_file.write(
                    '{0}\t{1}\tIN\tCNAME\t{2}\n'.format(record['host_cname'], host_name_ttl, record['host_name']))
            zone_file.write("\n")

        zone_file.write("\n\n; Mail records\n\n")
        # Mail records
        mails_records = sorted(mails_records, key=lambda k: k['mail_preference'])
        for record in mails_records:
            mail_ttl = record['mail_ttl']
            if not mail_ttl:
                mail_ttl = ''

            if 'mail_addr_type' in record:
                zone_file.write(
                    '\t{0}\tIN\tMX\t{1}\t{2}\n'.format(mail_ttl, record['mail_preference'], record['mail_host']))
                zone_file.write('{0}\t{1}\t{2}\t{3}\n'.format(record['mail_host'], mail_ttl, record['mail_addr_type'],
                                                              record['mail_ip_host']))

                if record['mail_cname']:
                    zone_file.write(
                        '{0}\t{1}\tIN\tCNAME\t{2}\n'.format(record['mail_cname'], mail_ttl, record['mail_host']))
            else:
                zone_file.write(
                    '\t{0}\tIN\tMX\t{1}\t{2}\n'.format(mail_ttl, record['mail_preference'], record['mail_host']))

            zone_file.write('\n')


# dns_config_file_path = '/etc/named.conf'
# with open(dns_config_file_path, 'a+') as file:
#     file.write('\n')
#     file.write('zone \"' + object['domain'] + '\" IN {\n')
#     file.write('\ttype master;\n')
#     file.write('\tfile \"' + object['domain'] + '.zone\";\n')
#     file.write('};\n')
#
#
# # restart bind9 server
# subprocess.check_output(['systemctl', 'restart', 'named.service'])

if __name__ == '__main__':
    create_zone_file(last_record)


