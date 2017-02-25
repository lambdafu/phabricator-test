#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of this is based on a script with a nice ASCII dragon (unknown author).

import shutil
import argparse
import collections
import errno
import glob
import hashlib
import json
import logging
import logging.handlers
import os
import pprint
import re
import sqlite3
import sys
import time
import traceback
import simplejson as json

import yaml

##### Utility #####

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

# mysql's 'utf8' type isn't utf8.
def mysql_unicode_hack(s):
    new_s = ''
    for char in unicode(s):
        # how does this get cut and pasted from emails?
        if ord(char) == 0:
            new_s += u' '
        elif ord(char) > 2**16:
            new_s += u'\ufffd'
        else:
            new_s += char
    try:
        return new_s.decode('latin1')
    except Exception:
        pass
    return new_s

################

class Conf(object):
    def __init__(self, confdir):
        with open(os.path.join(confdir, "users.json")) as fh:
            self.users = json.load(fh)
        self.r_users = dict()
        for user, aliases in self.users.items():
            self.r_users[user] = user
            for alias in aliases:
                self.r_users[alias] = user

        with open(os.path.join(confdir, "emails.json")) as fh:
            self.emails = json.load(fh)

        with open(os.path.join(confdir, "components.json")) as fh:
            self.components = json.load(fh)
        self.r_components = dict()
        for comp, aliases in self.components.items():
            self.r_components[comp] = comp
            for alias in aliases:
                self.r_components[alias] = comp

        with open(os.path.join(confdir, "type.json")) as fh:
            self.ticket_type = json.load(fh)

        with open(os.path.join(confdir, "priority.json")) as fh:
            self.priority = json.load(fh)

        with open(os.path.join(confdir, "resolution.json")) as fh:
            self.resolution = json.load(fh)

        with open(os.path.join(confdir, "keywords.json")) as fh:
            self.keywords = json.load(fh)

        with open(os.path.join(confdir, "portals.json")) as fh:
            self.portals = json.load(fh)

        with open(os.path.join(confdir, "status.json")) as fh:
            self.status = json.load(fh)

        with open(os.path.join(confdir, "milestones.json")) as fh:
            self.milestones = json.load(fh)

    def get_user(self, alias):
        if alias is None or alias == '':
            return 'admin'
        return self.r_users[alias]

    def get_email(self, user):
        return self.emails[user]

    def get_component(self, alias):
        if alias is None or alias == '':
            return None
        return self.r_components[alias]

    def get_ticket_type(self, ticket_type):
        return self.ticket_type[ticket_type]

    def get_priority(self, priority):
        return self.priority[priority]

    def get_resolution(self, resolution):
        if resolution is None or resolution == '':
            return 'open'
        return self.resolution[resolution]

    def get_keywords(self, keyword):
        return self.keywords[keyword]

    def get_portals(self, portal):
        return self.portals[portal]

    def get_status(self, status):
        return self.status[status]

    def get_milestone(self, milestone):
        return self.milestones[milestone]

conf = Conf("conf")

##### Trac #####

class TracDB(object):
    def __init__(self, db_file):
        self.db_file = db_file
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()

    def cursor(self):
        return self.cursor



class TracDAO(TracDB):

    AttachmentMetaData = collections.namedtuple('AttachmentMetaData', ['id', 'filename', 'description', 'author', 'time'])

    def get_email_for(self, user):
        for row in self.cursor.execute("SELECT value FROM session_attribute WHERE sid='%s' AND name='email'" % user):
            return row[0]

    def get_realname_for(self, user):
        for row in self.cursor.execute("SELECT value FROM session_attribute WHERE sid='%s' AND name='name'" % user):
            return row[0]

    def get_all_ticket_users(self):
        users = set()
        for row in self.cursor.execute("SELECT sid FROM session_attribute WHERE name='enabled' AND value=1"):
            user = conf.get_user(row[0])
            users.add(user)
        return users


    def get_all_final_ticket_states(self, trac_key):
        """ Get all of the relevant information about tickets in their final state.  So we know who owns them
        """
        tickets = []
        for row in self.cursor.execute("SELECT id from ticket ORDER BY id").fetchall():
            ticket = TracTicket(row[0])
            tickets.append(ticket)
        return tickets


    def handle_ticket_attachments(self, ticket, import_info, changes):
        for row in self.cursor.execute("SELECT id,filename,description,author,time from attachment WHERE type='ticket' AND author!='' and id=%i ORDER BY time" % ticket.ticket_id).fetchall():
            attachment = self.AttachmentMetaData(row[0], row[0] + "_" + row[1], row[2], row[3], row[4])
            ticket.handle_attachment(attachment, import_info, changes)

    def get_attachment_metadata(self):
        """
        Get all attachments for tickets. (No interest in importing the
        wiki or other things with attachments)

        All attachments with empty authors appaer to be useless crap.
        """
        attachments = set()
        for row in self.cursor.execute("SELECT id,filename,description,author,time from attachment WHERE type='ticket' AND author!='' ORDER BY time").fetchall():
            attachments.add(self.AttachmentMetaData(row[0], row[1], row[2], row[3], row[4]))
        return attachments

    __extension_re = re.compile(r'\.[A-Za-z0-9]+\Z')

    def attachment_path(self, base_dir, attachment):
        """
        Figure out where the hell the attachment actually is.
        Based on http://trac.edgewall.org/browser/trunk/trac/attachment.py
        """
        path = os.path.join(base_dir, 'ticket')
        path_hash = hashlib.sha1(attachment.id.encode('utf-8')).hexdigest()

        file_hash = hashlib.sha1(attachment.filename.encode('utf-8')).hexdigest()
        match = self.__extension_re.search(attachment.filename)
        file_name = file_hash + match.group(0) if match else file_hash
        full_path = os.path.join(path, path_hash[0:3], path_hash, file_name)
        return full_path


def get_parents(val):
    parents = set()
    if val is None:
        val = ""
    candidates = val.split(",")
    for candidate in candidates:
        candidate = candidate.strip()
        if candidate == '':
            continue
        try:
            candidate = int(candidate)
        except ValueError as e:
            raise ValueError("parents: %r" % val)
        parents.add(candidate)
    return parents


def get_due_date(duedate):
    val = duedate
    if val is None or val == '':
        return None
    if val[:2] == '15':
        val = '20'+val
    if val == '04-09-15':
        val = '2015-09-04'
    if val == '04-10-15':
        val = '2015-10-04'
    if val == '2016-04':
        val = '2016-04-30'
    if val != '':
        pattern = '%Y-%m-%d'
        return int(time.mktime(time.strptime(val, pattern)))
    raise ValueError("due-date: %r" % duedate)

def get_subscriber(cc):
    if cc is None:
        cc = ""
    cc = cc.replace(";", ",")
    cc = cc.replace(" ", ",")
    ccs = cc.split(",")
    subscriber = set()
    for name in ccs:
        _name = name.strip()
        if _name == '':
            continue
        _name = conf.get_user(_name)
        subscriber.add(_name)
    return subscriber

def get_projects_from_keywords(keywords):
    kws = set([kw.strip() for kw in keywords.split(',') if kw != ""]) if keywords else []
    keys = []
    for kw in kws:
        keys.extend(conf.get_keywords(kw.lower()))
    return set(keys)

def get_projects_from_component(component):
    return set([conf.get_component(component)])

def get_projects_from_type(ticket_type):
    return set([conf.get_ticket_type(ticket_type)])

def get_projects_from_portal(portal):
    val = portal
    if val is None or val == '' or val == 'all':
        return set()
    try:
        val = conf.get_portals(val.lower())
    except KeyError as e:
        log.warn("Can not lookup portal %i %s" % (self.ticket_id, val))
        raise e
    if val is None or val == '' or val == 'all':
        return set()
    return set(val)

def get_projects_from_status(status):
    return set(conf.get_status(status))

def get_projects_from_milestone(s):
    if s is None:
        return set()
    ms = conf.get_milestone(s)
    if ms is None:
        return set()
    return set([ms])


class TracTicket(object):
    # except for ticket id, define in terms of the db row names where possible
    def __init__(self, ticket_id):
        self.ticket_id = int(ticket_id)

    def __repr__(self):
        return 'TracTicket(' + str(self.ticket_id) + ')'

    def handle_attachment(self, attachment, import_info, changes):
        key = attachment.id + '|' + attachment.filename
        if key not in import_info:
            log.warn("Missing attachment info ticket:%i filename:%s" % (self.ticket_id, attachment.filename))
            return
        change = {'field': 'attachment', 'author': conf.get_user(attachment.author),
                  'attachment': attachment.filename,
                  'time': attachment.time}
        changes.append(change)

    def remarkupify(self, s):
        if s is None:
            return None
        """Sort of turn trac wiki formatting into remarkup, where easy to do so """
        s = s.replace('{{{', '```')
        s = s.replace('}}}', '```')
        s = s.replace('[[BR]]', '')
        # Prevent #->T for color codes (at least we try!) and insanely large numbers.
        #ticket = re.compile(r"([^\n\t])#([1-9][0-9]{0,3})([^0-9A-F])", re.MULTILINE | re.DOTALL)
        ticket = re.compile(r"([^\n\t])#([1-9][0-9]{0,3})\b", re.MULTILINE | re.DOTALL)
        s = ticket.sub(r'\1T\2', s)
        rev = re.compile(r"\br([1-9][0-9]{0,4})\b", re.MULTILINE)
        s = rev.sub(r'rV\1', s)
        return s


    def new_get_initial_values(self, db=None):
        basefields = set(["type", "time", "component", "severity", "priority",
                          "owner", "reporter", "cc", "version", "milestone",
                          "status", "resolution", "summary", "description", "keywords"])
        customfields = set(["due_date", "portal", "parents"])

        # The initial value can be:
        # 1) In the oldvalue of the first change.
        # 2) In the ticket itself.
        data = {}
        for field in basefields:
            query = ("SELECT oldvalue FROM ticket_change WHERE ticket=%i AND field='%s' ORDER BY time ASC" %
                     (self.ticket_id, field))
            rows = db.cursor.execute(query).fetchall()
            if len(rows) > 0:
                value = rows[0][0]
            else:
                query = ("SELECT %s FROM ticket WHERE id=%i" % (field, self.ticket_id))
                rows = db.cursor.execute(query).fetchall()
                value = rows[0][0]
            data[field] = value
        for field in customfields:
            query = ("SELECT oldvalue FROM ticket_change WHERE ticket=%i AND field='%s' ORDER BY time ASC" %
                     (self.ticket_id, field))
            rows = db.cursor.execute(query).fetchall()
            if len(rows) > 0:
                value = rows[0][0]
            else:
                query = ("SELECT value FROM ticket_custom WHERE ticket=%i AND name='%s'" % (self.ticket_id, field))
                rows = db.cursor.execute(query).fetchall()
                if len(rows) == 0:
                    value = None
                else:
                    value = rows[0][0]
            data[field] = value
        return data

    def new_get_changes(self, db=None):
        query = ("SELECT field, time, author, oldvalue, newvalue FROM ticket_change WHERE ticket=%i ORDER BY time ASC" %
                 self.ticket_id)
        rows = db.cursor.execute(query).fetchall()
        result = []
        for row in rows:
            author = conf.get_user(row[2])
            result.append({'field': row[0], 'time': long(row[1]), 'author': author, 'oldvalue': row[3], 'newvalue': row[4] })
        return result

    def new_make_phab_data(self, data, changes):
        #log.warn("Processing %i" % self.ticket_id)
        transform = {}
        transform['id'] = self.ticket_id
        transform['ts'] = data['time'] / 1000 / 1000
        transform['author'] = conf.get_user(data['reporter'])
        transform['owner'] = conf.get_user(data['owner'])
        transform['title'] = data['summary']
        transform['priority'] = conf.get_priority(data['priority'])
        transform['description'] = mysql_unicode_hack(self.remarkupify(data['description']))
        # We drop severity and version.

        if data['cc']:
            transform['subscriber'] = list(get_subscriber(data['cc']))

        projects = (set()
                    .union(get_projects_from_keywords(data['keywords']))
                    .union(get_projects_from_component(data['component']))
                    .union(get_projects_from_type(data['type']))
                    .union(get_projects_from_portal(data['portal']))
                    .union(get_projects_from_status(data['status']))
                    .union(get_projects_from_milestone(data['milestone'])))
        if len(projects) > 0:
            transform['projects'] = list(projects)

        # create fake initial parents and due-date change
        if data['due_date']:
            changes.insert(0, {'field': 'due_date', 'time': data['time'], 'author': transform['author'],
                               'oldvalue': '', 'newvalue': data['due_date']})
        if data['parents']:
            changes.insert(0, {'field': 'parents', 'time': data['time'], 'author': transform['author'],
                               'oldvalue': '', 'newvalue': data['parents']})

        new_changes = []
        for change in changes:
            self.new_make_phab_change(new_changes, change)
        if len(new_changes) > 0:
            transform['changes'] = new_changes
        return transform

    def new_make_phab_change(self, changes, change):
        transform = {}
        transform['ts'] = change['time'] / 1000 / 1000
        transform['author'] = change['author']

        field = change['field']
        if field == 'attachment':
            # Special case
            transform['type'] = 'attachment'
            transform['value'] = change['attachment']
            changes.append(transform)
            return None

        oldvalue = change['oldvalue']
        newvalue = change['newvalue']
        if oldvalue == newvalue:
            return None

        if field == 'reporter':
            return None
        elif field == 'owner':
            old = conf.get_user(oldvalue)
            new = conf.get_user(newvalue)
            if old == new:
                return None
            transform['type'] = 'owner'
            transform['value'] = new
        elif field == 'due_date':
            old = get_due_date(oldvalue)
            new = get_due_date(newvalue)
            if old == new:
                return None
            transform['type'] = 'due-date'
            transform['value'] = new
        elif field == 'summary':
            transform['type'] = 'title'
            transform['value'] = newvalue
        elif field == 'description':
            old = mysql_unicode_hack(self.remarkupify(oldvalue))
            new = mysql_unicode_hack(self.remarkupify(newvalue))
            if old == new:
                return None
            transform['type'] = 'description'
            transform['value'] = new
        elif field == 'comment':
            if newvalue is None or newvalue == '':
                return None
            if newvalue.startswith("Add a subticket #"):
                return None
            if newvalue.startswith("Remove a subticket #"):
                return None
            if newvalue.startswith("Milestone ") and newvalue.endswith(" deleted"):
                return None
            transform['type'] = 'add_comment'
            transform['value'] = mysql_unicode_hack(self.remarkupify(newvalue))
        elif field == 'milestone':
            old = get_projects_from_milestone(oldvalue)
            new = get_projects_from_milestone(newvalue)
            if old == new:
                return None
            return self.new_make_phab_project_changes(changes, transform, old, new)
        elif field == 'type':
            old = get_projects_from_type(oldvalue)
            new = get_projects_from_type(newvalue)
            if old == new:
                return None
            return self.new_make_phab_project_changes(changes, transform, old, new)
        elif field == 'component':
            old = get_projects_from_component(oldvalue)
            new = get_projects_from_component(newvalue)
            if old == new:
                return None
            return self.new_make_phab_project_changes(changes, transform, old, new)
        elif field == 'keywords':
            old = get_projects_from_keywords(oldvalue)
            new = get_projects_from_keywords(newvalue)
            if old == new:
                return None
            return self.new_make_phab_project_changes(changes, transform, old, new)
        elif field == 'portal':
            old = get_projects_from_portal(oldvalue)
            new = get_projects_from_portal(newvalue)
            if old == new:
                return None
            return self.new_make_phab_project_changes(changes, transform, old, new)
        elif field == 'status':
            old = get_projects_from_status(oldvalue)
            new = get_projects_from_status(newvalue)
            if old == new:
                return None
            return self.new_make_phab_project_changes(changes, transform, old, new)
        elif field == 'cc':
            old = get_subscriber(oldvalue)
            new = get_subscriber(newvalue)
            if old == new:
                return None
            if len(old-new) > 0:
                _transform = dict(transform)
                _transform['type'] = 'subscriber'
                _transform['method'] = '-'
                _transform['value'] = list(old-new)
                changes.append(_transform)
            if len(new-old) > 0:
                _transform = dict(transform)
                _transform['type'] = 'subscriber'
                _transform['method'] = '+'
                _transform['value'] = list(new-old)
                changes.append(_transform)
            return None
        elif field == 'resolution':
            old = conf.get_resolution(oldvalue)
            new = conf.get_resolution(newvalue)
            if old == new:
                return None
            transform['type'] = 'status'
            transform['value'] = new
        elif field == 'priority':
            old = conf.get_priority(oldvalue)
            new = conf.get_priority(newvalue)
            if old == new:
                return None
            transform['type'] = 'priority'
            transform['value'] = new
        elif field == 'parents':
            transform['type'] = 'parent'
            old = get_parents(oldvalue)
            new = get_parents(newvalue)
            if new == old:
                return None
            if len(new-old) == 0 and len(old-new) > 0:
                transform['method'] = '-'
                transform['value'] = list(old-new)
            elif len(new-old) > 0 and len(old-new) == 0:
                transform['method'] = '+'
                transform['value'] = list(new-old)
            else:
                transform['method'] = '='
                transform['value'] = list(new)
        elif field == 'blockedby':
            return None
        elif field == 'blocking':
            return None
        elif field == 'name':
            return None
        elif field.startswith('_comment'):
            # Comment edit.  Bah.
            return None
        else:
            raise ValueError("Unknown field: %r" % field)
        changes.append(transform)

    def new_make_phab_project_changes(self, changes, transform, old, new):
        if len(old-new) > 0:
            _transform = dict(transform)
            _transform['type'] = 'project'
            _transform['method'] = '-'
            _transform['value'] = list(old-new)
            changes.append(_transform)
        if len(new-old) > 0:
            _transform = dict(transform)
            _transform['type'] = 'project'
            _transform['method'] = '+'
            _transform['value'] = list(new-old)
            changes.append(_transform)





##### cmds #####


def cmd_users_dump_json(args):
    db = TracDAO(args.db_file)
    raw_users = db.get_all_ticket_users()
    j_users = {}
    for raw_user in raw_users:
        uid = conf.get_user(raw_user)
        j_users[uid] = {'name': uid, 'bot': False }
        email = db.get_email_for(uid)
        if email is None or email == "":
            email = conf.get_email(uid)
        if email is None or email == "":
            raise ValueError("Unknown email: %s" % uid)
        realname = db.get_realname_for(uid)
        if realname is None:
            realname = uid
        j_users[uid]['realname'] = realname
        j_users[uid]['email'] = email

    all_users = [
        { "name": "admin", "realname": "Admin", "email": conf.get_email('admin'), "admin": True }
    ]
    for uid in j_users:
        all_users.append(j_users[uid])

    mkdir_p(args.users_out)
    fname = os.path.join(args.users_out, 'users.json')
    with open(fname, 'w') as f:
        f.write(json.dumps(all_users, indent=2))

def cmd_verify_attachments(args):
    db = TracDAO(args.db_file)
    num_ok = 0
    num_bad = 0
    attachments = db.get_attachment_metadata()
    for attachment in attachments:
        attachment_path = db.attachment_path(args.attachment_dir, attachment)
        if os.path.exists(attachment_path):
            num_ok += 1
        else:
            print 'path not found ', attachment, attachment_path
            num_bad += 1
    print 'num ok: ', num_ok
    print 'num bad: ', num_bad


def cmd_dump_attachments(args):
    db = TracDAO(args.db_file)
    mkdir_p(args.dump_dir)
    attachments = db.get_attachment_metadata()
    j_files = []
    for attachment in attachments:
        local_attachment_path = db.attachment_path(args.attachment_dir, attachment)
        server_attachment_path = db.attachment_path(args.server_dir, attachment)
        filename = str(attachment.id) + "_" + attachment.filename
        j_file = {'ticket-id': attachment.id, 'filename': filename,
                  'author': conf.get_user(attachment.author)}
        if os.path.exists(local_attachment_path):
            j_file['location'] = server_attachment_path
        else:
            j_file['location'] = 'MISSING'
        dst = os.path.join(args.server_dir, filename)
        shutil.copy(local_attachment_path, dst)
        j_files.append(j_file)
    j_files.sort(key=lambda x: int(x['ticket-id']))

    fname = os.path.join(args.dump_dir, 'all-attachments.json')
    with open(fname, 'w') as f:
        f.write(json.dumps(j_files,  sort_keys=True,
                           indent=4, separators=(',', ': ')))


def cmd_dump_tickets(args):
    d_dir = os.path.join(args.dump_dir, "tickets")
    mkdir_p(d_dir)

    db = TracDAO(args.db_file)
    with open(args.attachment_info) as f:
        attachment_info = json.load(f)
    attachment_import_info = {}
    for attachment in attachment_info:
        key = attachment['ticket-id'] + '|' + attachment['filename']
        attachment_import_info[key] = attachment
    tickets = db.get_all_final_ticket_states(args.trac_key)
    phabs = []
    for ticket in tickets:
        data = ticket.new_get_initial_values(db)
        changes = ticket.new_get_changes(db)
        db.handle_ticket_attachments(ticket, attachment_import_info, changes)
        phab = ticket.new_make_phab_data(data, changes)

        phabs.append(phab)

    fname = os.path.join(args.dump_dir, "tasks.json")
    with open(fname, 'w') as f:
        f.write(json.dumps(phabs, indent=2))

##### main and friends #####


def parse_args(argv):
    def db_cmd(sub_p, cmd_name, cmd_help):
        cmd_p = sub_p.add_parser(cmd_name, help=cmd_help)
        cmd_p.add_argument('--log',
                           action='store', dest='log', default='stdout', choices=['stdout', 'syslog', 'both'],
                           help='log to stdout and/or syslog')
        cmd_p.add_argument('--log-level',
                           action='store', dest='log_level', default='WARNING',
                           choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'],
                           help='log to stdout and/or syslog')
        cmd_p.add_argument('--log-facility',
                           action='store', dest='log_facility', default='user',
                           help='facility to use when using syslog')
        cmd_p.add_argument('--db-file',
                           action='store', dest='db_file', required=True,
                           help='sqlite db file')

        return cmd_p

    parser = argparse.ArgumentParser(description="")
    sub_p = parser.add_subparsers(dest='cmd')

    users_dump_json_p = db_cmd(sub_p, 'users-dump-json', '')
    users_dump_json_p.add_argument('--users-out',
                                   action='store', dest='users_out', default='out',
                                   help='')
    users_dump_json_p.set_defaults(func=cmd_users_dump_json)

    verify_attachments_p = db_cmd(sub_p, 'verify-attachments', '')
    verify_attachments_p.add_argument('--attachment-dir',
                                      action='store', dest='attachment_dir', required=True)
    verify_attachments_p.set_defaults(func=cmd_verify_attachments)

    dump_attachments_p = db_cmd(sub_p, 'dump-attachments', '')
    dump_attachments_p.add_argument('--attachment-dir',
                                      action='store', dest='attachment_dir', required=True)
    dump_attachments_p.add_argument('--dump-dir',
                                      action='store', dest='dump_dir', default='out/attachments')
    dump_attachments_p.add_argument('--server-dir', # where are they are in phab server
                                      action='store', dest='server_dir', required=True)
    dump_attachments_p.set_defaults(func=cmd_dump_attachments)


    dump_tickets_p = db_cmd(sub_p, 'dump-tickets', '')
    dump_tickets_p.add_argument('--attachment-info',
                                action='store', dest='attachment_info', default='out/attachments/all-attachments.json')
    dump_tickets_p.add_argument('--dump-dir',
                                action='store', dest='dump_dir', default='out')
    dump_tickets_p.add_argument('--trac-key',
                                action='store', dest='trac_key', required=True)
    dump_tickets_p.add_argument('--id-offset',
                                action='store', type=int, dest='id_offset', default=0)
    dump_tickets_p.set_defaults(func=cmd_dump_tickets)

    args = parser.parse_args(argv)
    return args


def setup_logging(handlers, facility, level):
    global log

    log = logging.getLogger('export-trac')
    formatter = logging.Formatter(' | '.join(['%(asctime)s', '%(name)s',  '%(levelname)s', '%(message)s']))
    if handlers in ['syslog', 'both']:
        sh = logging.handlers.SysLogHandler(address='/dev/log', facility=facility)
        sh.setFormatter(formatter)
        log.addHandler(sh)
    if handlers in ['stdout', 'both']:
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        log.addHandler(ch)
    lmap = {
        'CRITICAL': logging.CRITICAL,
        'ERROR': logging.ERROR,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG,
        'NOTSET': logging.NOTSET
        }
    log.setLevel(lmap[level])


def main(argv):
    args = parse_args(argv)
    try:
        setup_logging(args.log, args.log_facility, args.log_level)
    except Exception as e:
        print >> sys.stderr, 'Failed to setup logging'
        traceback.print_exc()
        raise e

    args.func(args)


if __name__ == '__main__':
    main(sys.argv[1:])
