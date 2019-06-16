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

last_record = collection.find({}).sort('_id', pymongo.DESCENDING).limit(3)[0]
print(last_record)

var_named_folder = 'var/named/'
etc_named_folder = 'etc/named/'


def integrate_zone(record):
    domain_details = record['domain_details']
    zone_folder = var_named_folder + domain_details['domain_name']
    if not os.path.exists(zone_folder):
        os.makedirs(zone_folder)
    zone_file_path = '{0}/{1}.zone'.format(zone_folder, domain_details['domain_name'])
    reverse_zone_file_path = '{0}/{1}.rr.zone'.format(zone_folder, domain_details['domain_name'])

    # create zone files
    create_direct_zone_file(record, zone_file_path)
    create_reverse_zone_file(record, reverse_zone_file_path)

    """
    TODO: Delete reference from   /etc/named.conf   file
    """
    if not os.path.exists(etc_named_folder):
        os.makedirs(etc_named_folder)


    # create config file for domain
    with open(etc_named_folder + domain_details['domain_name'] + '.conf', 'w+') as conf_file:
        conf_file.write('zone "{0}" IN {{\n'.format(domain_details['domain_name']))
        conf_file.write('\ttype master;\n')
        conf_file.write('\tfile "{}";\n'.format(domain_details['domain_name'] + '/' + domain_details['domain_name'] + '.zone'))
        conf_file.write('};\n\n')

        conf_file.write('zone "{}" IN {{\n'.format(domain_details['domain_reverse_addr']))
        conf_file.write('\ttype master;\n')
        conf_file.write('\tfile "{}";\n'.format(domain_details['domain_name'] + '/' + domain_details['domain_name'] + '.rr.zone'))
        conf_file.write('};\n\n')

    # include config file for domain in /etc/named.conf file
    include_in_conf_file(domain_details['domain_name'])


def include_in_conf_file(domain_name):
    with open("etc/named.conf", "r") as f:
        lines = f.readlines()
    with open("etc/named.conf", "w") as f:
        for line in lines:
            if domain_name not in line:
                f.write(line)
        f.write('\ninclude "/etc/named/{}.conf";\n'.format(domain_name))


def create_reverse_zone_file(record, reverse_zone_file_path):
    domain_details = record['domain_details']
    ns_records = record['ns_records']
    hosts_records = record['hosts_records']
    mails_records = record['mails_records']

    with open(reverse_zone_file_path, "w+") as reverse_zone_file:

        reverse_zone_file.write('$ORIGIN {}.\n'.format(domain_details['domain_reverse_addr']))  # $ORIGIN 184.56.128.in-addr.arpa.

        if 'domain_ttl' in domain_details:
            domain_ttl = domain_details['domain_ttl']
        reverse_zone_file.write('$TTL\t{}\n'.format(domain_ttl))  # $TTL 86400

        original_admin_mail = domain_details['original_admin_mail']
        if original_admin_mail.split('@')[-1] == domain_details['domain_name']:
            admin_mail = original_admin_mail.split('@')[0]
        else:
            admin_mail = domain_details['admin_mail'] + '.'

        # find first internal NS record if exists
        first_ns_internal = None
        for record in ns_records:
            if 'ns_ip' in record:
                first_ns_internal = record
                break

        ns_internal_name = ''
        if first_ns_internal:
            ns_internal_name = first_ns_internal['ns']
        else:
            ns_internal_name = ns_records[0]['ns'] + '.'
        # SOA record
        reverse_zone_file.write(
            '@\tIN\tSOA\t{0} {1} ({2} {3} {4} {5} {6})\n'.format(ns_internal_name, admin_mail, serial_number, refresh,
                                                                 update_retry, expiry, nxdomain_ttl))
        reverse_zone_file.write("\n\n; Name server records\n\n")
        # NS records
        for record in ns_records:
            ns_ttl = record['ns_ttl']
            if not ns_ttl:
                ns_ttl = ''
            reverse_zone_file.write('\t{0}\tIN\tNS\t{1}\n'.format(ns_ttl, record['ns']))

            if 'ns_ip' in record:
                reverse_zone_file.write('{0}.\t{1}\tIN\tPTR\t{2}\n'.format(record['ns_ip_reverse'], ns_ttl,
                                                                          record['ns'] + '.' + domain_details[
                                                                              'domain_name'] + '.'))
            reverse_zone_file.write("\n")

        reverse_zone_file.write("\n\n; Host RECORDS \n\n")
        for record in hosts_records:
            host_name_ttl = record['host_name_ttl']
            if not host_name_ttl:
                host_name_ttl = ''
            reverse_zone_file.write('{0}.\t{1}\tIN\tPTR\t{2}\n'.format(record['host_name_ip_reverse'], host_name_ttl,
                                                                      record['host_name'] + '.' + domain_details[
                                                                          'domain_name'] + '.'))
            reverse_zone_file.write("\n")

        reverse_zone_file.write("\n\n; Mail RECORDS \n\n")
        for record in mails_records:
            mail_ttl = record['mail_ttl']
            if not mail_ttl:
                mail_ttl = ''

            # check if is internal record
            if 'mail_ip_host' in record:
                reverse_zone_file.write('{0}.\t{1}\tIN\tPTR\t{2}\n'.format(record['mail_ip_host_reverse'], mail_ttl,
                                                                          record['mail_host'] + '.' + domain_details[
                                                                              'domain_name'] + '.'))
            reverse_zone_file.write('\n')


def create_direct_zone_file(record, zone_file_path):
    domain_details = record['domain_details']
    ns_records = record['ns_records']
    hosts_records = record['hosts_records']
    mails_records = record['mails_records']

    record_type = domain_details['record_type']

    # 'w+' mode create if not exists or overwrites the content
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

        # find first internal NS record if exists
        first_ns_internal = None
        for record in ns_records:
            if 'ns_ip' in record:
                first_ns_internal = record
                break

        ns_internal_name = ''
        if first_ns_internal:
            ns_internal_name = first_ns_internal['ns']
        else:
            ns_internal_name = ns_records[0]['ns'] + '.'
        # SOA record
        zone_file.write(
            '@\tIN\tSOA\t{0} {1} ({2} {3} {4} {5} {6})\n'.format(ns_internal_name, admin_mail, serial_number, refresh,
                                                                 update_retry, expiry, nxdomain_ttl))

        zone_file.write("\n\n; Name server records\n\n")
        # NS records
        for record in ns_records:
            ns_ttl = record['ns_ttl']
            if not ns_ttl:
                ns_ttl = ''
            zone_file.write('\t{0}\tIN\tNS\t{1}\n'.format(ns_ttl, record['ns']))

            # check if is internal record
            if 'ns_ip' in record:
                zone_file.write(
                    '{0}\t{1}\tIN\t{2}\t{3}\n'.format(record['ns'], ns_ttl, record_type, record['ns_ip']))
            zone_file.write("\n")

        zone_file.write("\n; Host records\n\n")
        # HOST records
        for record in hosts_records:
            host_name_ttl = record['host_name_ttl']
            if not host_name_ttl:
                host_name_ttl = ''

            zone_file.write('{0}\t{1}\tIN\t{2}\t{3}\n'.format(record['host_name'], host_name_ttl, record_type,
                                                              record['host_name_ip']))
            if record['host_cname']:
                zone_file.write(
                    '{0}\t{1}\tIN\tCNAME\t{2}\n'.format(record['host_cname'], host_name_ttl, record['host_name']))
            if record['host_txt']:
                zone_file.write(
                    '{0}\t{1}\tIN\tTXT\t"{2}"\n'.format(record['host_name'], host_name_ttl, record['host_txt']))
            zone_file.write("\n")


        zone_file.write("\n\n; Mail records\n\n")
        # Mail records
        mails_records = sorted(mails_records, key=lambda k: k['mail_preference'])
        for record in mails_records:
            mail_ttl = record['mail_ttl']
            if not mail_ttl:
                mail_ttl = ''

            # check if is internal record
            if 'mail_ip_host' in record:
                zone_file.write(
                    '\t{0}\tIN\tMX\t{1}\t{2}\n'.format(mail_ttl, record['mail_preference'], record['mail_host']))
                zone_file.write('{0}\t{1}\tIN\t{2}\t{3}\n'.format(record['mail_host'], mail_ttl, record_type,
                                                                  record['mail_ip_host']))

                if record['mail_cname']:
                    zone_file.write(
                        '{0}\t{1}\tIN\tCNAME\t{2}\n'.format(record['mail_cname'], mail_ttl, record['mail_host']))
                if record['mail_txt']:
                    zone_file.write(
                        '{0}\t{1}\tIN\tTXT\t"{2}"\n'.format(record['mail_host'], mail_ttl, record['mail_txt']))
            else:
                zone_file.write(
                    '\t{0}\tIN\tMX\t{1}\t{2}\n'.format(mail_ttl, record['mail_preference'], record['mail_host']))

            zone_file.write('\n')


if __name__ == '__main__':
    integrate_zone(last_record)

    # restart bind9 server
    subprocess.check_output(['systemctl', 'restart', 'named.service'])
