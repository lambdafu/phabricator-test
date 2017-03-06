# encoding=utf8

import sys
import json
import logging
import os
from collections import defaultdict
import re

from roundup import instance

reload(sys)
sys.setdefaultencoding('utf8')

# Roundup to Phabricator
#
# Design choices:
#
# * Roundup Categories are Phabricator Projects.  If project exists, reuse it.  This allows
#   to set up categories in a nested hierarchy first.  Use dry-run to get names.
# * Roundup Retired Categories are Phabricator Archived Projects.
# * Additional Phabricator Projects: "Feature Request", "Bug Report", "Design & Planning",
#   "Security", "Contributor Onboarding", "Public & Media Relations", "Prioritized" ($$$)

# Phabricator status: open, resolved, wontfix, invalid, spite, duplicate
# priority: unblock now!, needs triage, high, normal, low, wishlist
# IDEA: Move some states to Kanban workoard columns.

# Normalize map for user id.  We deduplicate some users. id-2-id (str)
user_normal = {}

# int to str
status_map = {}

# int to str
priority_map = {}

def get_priority(status, priority):
    if priority is None:
        return None # "normal" ?
    return conf.get_priority(priority)

def get_status(status, priority):
    if priority == 'nobug':
        return 'invalid'
    if status is None:
        return 'open'
    return conf.get_status(status)

def get_username(user):
    if user is None or user == '':
        return None
    user = user_normal.get(user, user)
    user = db.user.getnode(user)
    username = conf.get_username(user.address, user.username)
    return username

class Conf(object):
    def __init__(self, confdir):
        with open(os.path.join(confdir, "users.json")) as fh:
            self.users = json.load(fh)

        with open(os.path.join(confdir, "priority.json")) as fh:
            self.priority = json.load(fh)

        with open(os.path.join(confdir, "priority-projects.json")) as fh:
            self.priority_projects = json.load(fh)

        with open(os.path.join(confdir, "category.json")) as fh:
            self.category = json.load(fh)

        with open(os.path.join(confdir, "status.json")) as fh:
            self.status = json.load(fh)

        with open(os.path.join(confdir, "status-projects.json")) as fh:
            self.status_projects = json.load(fh)

        with open(os.path.join(confdir, "topic-projects.json")) as fh:
            self.topic_projects = json.load(fh)

        self.extlink_projects = {}
        with open(os.path.join(confdir, "extlink-projects.json")) as fh:
            extlink_projects = json.load(fh)
        for regex, projects in extlink_projects.items():
            self.extlink_projects[re.compile(regex)] = projects

    def get_username(self, email, username):
        email = email.lower()
        username = self.users.get(email, username)
        username = username.replace("@", "_")
        username = username.replace(" ", "_")
        username = username.replace("+", "_")
        username = username.replace("#", "_")
        username = username.replace("α", "a")
        username = username.replace("β", "b")
        username = username.replace("γ", "g")
        username = username.replace("Á", "A")
        return username

    def get_priority(self, priority):
        return self.priority[priority]

    def get_priority_projects(self, priority):
        if priority is None:
            return set()
        return set(self.priority_projects[priority])

    def get_category_projects(self, category):
        if category is None or category == '':
            return set()
        return self.category[category]

    def get_extlink_projects(self, extlink):
        if extlink is None or extlink == '':
            return set()
        for extlink_re, projects in self.extlink_projects.items():
            if extlink_re.search(extlink):
                return projects
        return set()

    def get_topic_projects(self, topics):
        result = set()
        for topic in topics:
            topic = db.keyword.getnode(topic).name
            topic = self.topic_projects[topic]
            result = result.union(topic)
        return result

    def get_status(self, status):
        return self.status[status]

    def get_status_projects(self, status):
        if status is None:
            return set()
        return set(self.status_projects[status])

conf = Conf("conf")


def process_categories(db):
    # Schema: activity, actor, creation, creator, name, id
    cats = db.category
    for ident in cats.getnodeids(retired=None):
        is_retired = cats.is_retired(ident)
        cat = cats.getnode(ident)
        issues = db.issue.find(category=ident)
        all_issues = db.issue.getnodeids(retired=None)
        all_issues = [db.issue.getnode(issue_id) for issue_id in all_issues]
        all_issues = [issue for issue in all_issues if issue.category == ident]

        print "[CATEGORY %s] %s%s: %s/%s issues" % (cat.id, cat.name, " (retired)" if is_retired else "", len(issues), len(all_issues))
        creator = db.user.getnode(cat.creator)
        actor = db.user.getnode(cat.actor)
        print "Created: %s by %s/%s" % (cat.creation, cat.creator, creator.username)
        print "Acted:   %s by %s/%s" % (cat.activity, cat.actor, actor.username)

def process_keywords(db):
    # In GnuPG, some topics are reasons for close, some topics are projects.
    # See https://bugs.gnupg.org/roundup-topics.html

    # Schmea: activity, actor, creation, creator, name, id
    kws = db.keyword
    for ident in kws.getnodeids(retired=None):
        is_retired = kws.is_retired(ident)
        kw = kws.getnode(ident)

        issues = db.issue.find(topic=ident)
        all_issues = db.issue.getnodeids(retired=None)
        all_issues = [db.issue.getnode(issue_id) for issue_id in all_issues]
        all_issues = [issue for issue in all_issues if ident in issue.topic]

        print "[KEYWORD %s] %s%s: %s/%s issues" % (kw.id, kw.name, " (retired)" if is_retired else "", len(issues), len(all_issues))
        creator = db.user.getnode(kw.creator)
        actor = db.user.getnode(kw.actor)
        #print "Created: %s by %s/%s" % (kw.creation, kw.creator, creator.username)
        #print "Acted:   %s by %s/%s" % (kw.activity, kw.actor, actor.username)

def process_query(db):
    # Schema: activity, actor, creation, creator, klass, name, private_for, url, id
    # (klass is always "issue")
    qrs = db.query
    for ident in qrs.getnodeids(retired=None):
        is_retired = qrs.is_retired(ident)
        qr = qrs.getnode(ident)

        print "[QUERY %s] %s%s: %s for %s: %s" % (qr.id, qr.name, " (retired)" if is_retired else "", qr.klass, qr.private_for, qr.url)
        creator = db.user.getnode(qr.creator)
        actor = db.user.getnode(qr.actor)
        #print "Created: %s by %s/%s" % (qr.creation, qr.creator, creator.username)
        #print "Acted:   %s by %s/%s" % (qr.activity, qr.actor, actor.username)

def process_files(db):
    files = db.file
    for ident in files.getnodeids(retired=None):
        is_retired = files.is_retired(ident)
        file = files.getnode(ident)

        print "[FILE %s] %s (%s)" % (file.id, file.name, file.type)


def process_users(db):
    dbusers = db.user

    retired = {}
    by_name = defaultdict(list)
    by_email = defaultdict(list)
    by_id = {}
    for ident in dbusers.getnodeids(retired=None):
        is_retired = dbusers.is_retired(ident)
        user = dbusers.getnode(ident)
        # We disambiguate some usernames by email.
        username = conf.get_username(user.address, user.username)
        retired[user] = is_retired
        by_name[username].append(user)
        email = user.address.lower()
        by_email[email].append(user)
        by_id[user.id] = user

    # Sort first by retired status, then by id.
    def cmp_user(u1, u2):
        if retired[u1] == retired[u2]:
            id1 = int(u1.id)
            id2 = int(u2.id)
            if id1 < id2:
                return -1
            elif id1 == id2:
                return 0
            elif id1 > id2:
                return 1
        elif retired[u1] == True:
            return -1
        else:
            return 1

    for username, users in by_email.items():
        username = conf.get_username(user.address, user.username)
        if len(users) <= 1:
            continue
        users = sorted(users, cmp=cmp_user)
        ref_user = users[-1]
        users = users[:-1]
        for user in users:
            user_normal[user.id] = ref_user.id
            # logging.warn("USER: MAP (%s, %s, %s, %s) to (%s, %s, %s, %s) by email" %
            #     (user.id, user.username, user.address, "retired" if retired[user] else "active",
            #     ref_user.id, ref_user.username, ref_user.address, "retired" if retired[ref_user] else "active"))

    for username, users in by_name.items():
        username = conf.get_username(user.address, user.username)
        if len(users) <= 1:
            continue
        mapped_ids = set()
        for user in users:
            if user.id in user_normal:
                mapped_ids.add(user_normal[user.id])
        if len(mapped_ids) > 1:
            log.warning("USER: Unclear username %s with targets %s",
                username, ", ".join([by_id[ident].username for ident in mapped_ids]))
            ref_user = None
        if len(mapped_ids) == 1:
            # logging.warning("USER: Reusing existing mapping")
            ref_user = by_id[list(mapped_ids)[0]]
        if ref_user == None:
            users = sorted(users, cmp=cmp_user)
            ref_user = users[-1]
        users = users[:-1]
        for user in users:
            if user.id in user_normal or user.id == ref_user.id:
                continue
            user_normal[user.id] = ref_user.id
            # logging.warn("USER: MAP (%s, %s, %s, %s) to (%s, %s, %s, %s) by name" %
            #     (user.id, user.username, user.address, "retired" if retired[user] else "active",
            #     ref_user.id, ref_user.username, ref_user.address, "retired" if retired[ref_user] else "active"))

    users = []
    roles = set()
    for ident in sorted(by_id.keys()):
        user = by_id[ident]
        username = conf.get_username(user.address, user.username)
        if user.id not in user_normal:
            data = {}
            data['name'] = username
            data['realname'] = user.realname if user.realname else username
            data['email'] = user.address.lower()
            data['disabled'] = retired[user]
            # tags = sorted([role.strip().lower() for role in user.roles.split(",")])
            users.append(data)
        roles.add(user.roles)
    return users

def process_status(db):
    # Schmea: activity, actor, creation, creator, name, id
    sts = db.status
    for ident in sts.getnodeids(retired=None):
        is_retired = sts.is_retired(ident)
        st = sts.getnode(ident)

        status_map[st.id] = st.name

        # issues = db.issue.find(status=ident)
        # all_issues = db.issue.getnodeids(retired=None)
        # all_issues = [db.issue.getnode(issue_id) for issue_id in all_issues]
        # all_issues = [issue for issue in all_issues if ident == issue.status]
        #
        # print "[STATUS %s] %s.%s%s: %s/%s issues" % (st.id, st.order, st.name, " (retired)" if is_retired else "", len(issues), len(all_issues))
        # creator = db.user.getnode(st.creator)
        # actor = db.user.getnode(st.actor)
        # print "Created: %s by %s/%s" % (st.creation, st.creator, creator.username)
        # print "Acted:   %s by %s/%s" % (st.activity, st.actor, actor.username)

def process_priority(db):
    # Schmea: activity, actor, creation, creator, name, id
    prs = db.priority
    for ident in prs.getnodeids(retired=None):
        is_retired = prs.is_retired(ident)
        pr = prs.getnode(ident)

        priority_map[pr.id] = pr.name

        # issues = db.issue.find(priority=ident)
        # all_issues = db.issue.getnodeids(retired=None)
        # all_issues = [db.issue.getnode(issue_id) for issue_id in all_issues]
        # all_issues = [issue for issue in all_issues if ident == issue.priority]
        #
        # print "[PRIORITY %s] %s.%s%s: %s/%s issues" % (pr.id, pr.order, pr.name, " (retired)" if is_retired else "", len(issues), len(all_issues))
        # creator = db.user.getnode(pr.creator)
        # actor = db.user.getnode(pr.actor)
        # print "Created: %s by %s/%s" % (pr.creation, pr.creator, creator.username)
        # print "Acted:   %s by %s/%s" % (pr.activity, pr.actor, actor.username)

def build_projects(project_state):
    projects = set()
    projects = projects.union(conf.get_status_projects(project_state['status']))
    projects = projects.union(conf.get_priority_projects(project_state['priority']))
    projects = projects.union(conf.get_category_projects(project_state['category']))
    projects = projects.union(conf.get_extlink_projects(project_state['extlink']))
    projects = projects.union(conf.get_topic_projects(project_state['topic']))
    return projects

def process_tasks(db):
    dbissues = db.issue

    tasks = []
    for ident in dbissues.getnodeids(retired=None):
        is_retired = dbissues.is_retired(ident)
        issue = dbissues.getnode(ident)
        author = get_username(issue.creator)
        status = db.status.getnode(issue.status).name
        cat = db.category.getnode(issue.category).name if issue.category else None
        assignee = get_username(issue.assignedto)
        priority = db.priority.getnode(issue.priority).name if issue.priority else "triage"
        msgs = map(lambda x: db.msg.getnode(x),issue.messages)
        files = map(lambda x: db.file.getnode(x),issue.files)
        nosy = map(lambda x: db.user.getnode(x),issue.nosy)
        superseder = map(lambda x: db.issue.getnode(x),issue.superseder)
        assignedto = get_username(issue.assignedto)

        # missing: extlink, version
        if is_retired:
             # Spam, FIXME
            continue

        data = {}
        data['id'] = int(ident)
        data['ts'] = int(issue.creation.timestamp())
        data['author'] = author
        data['owner'] = assignedto
        data['title'] = issue.title
        data['priority'] = get_priority(status, priority)
        data['status'] = get_status(status, priority)
        if issue.duedate != None:
            data['due-date'] = int(issue.duedate.timestamp())
        else:
            data['due-date'] = None
        data['extlink'] = issue.extlink
        data['version'] = issue.version

        # FIXME
        #data['description'] = issue.description
        messages_added = set()
        messages_removed = set()

        project_state = {
            'status': status,
            'priority': priority,
            'category': cat,
            'extlink': issue.extlink,
            'topic': set(issue.topic)
        }

        data['projects'] = list(build_projects(project_state))

        print "[ISSUE %s] %s (%s) in %s with %d messages, %d files, superseder by %d and %d subscribers" % \
                (issue.id, issue.title, status, cat, len(msgs),len(files),len(superseder),len(nosy))
        # The issue data is the current state, and the history
        # contains previous values.  By walking the history backwards, we
        # can recover the original ticket and all changes easily.
        all_changes = []
        history = issue.history()
        history.sort() # (id, date, ...)
        history.reverse()
        for hist_item in history:
            (_, date, change_author, action, params) = hist_item
            change_author = get_username(change_author)

            changes = []
            change_templ = {}
            change_templ['ts'] = int(date.timestamp())
            change_templ['author'] = change_author
            if action == 'create':
                # Ignore
                pass
            elif action == 'set':
                print "-", action, params
                known_params = set(['files', 'messages',
                'nosy', 'superseder',
                'topic',
                'status', 'priority', 'category', 'assignedto',
                'extlink', 'title', 'duedate', 'version'])
                unknown_params = set(params.keys()) - known_params
                if len(unknown_params) > 0:
                    raise ValueError("Unknown params: %r" % unknown_params)

                prev_project_state = dict(project_state)
                if 'messages' in params:
                    if len(params['messages']) > 1:
                        raise ValueError("messages: %r" % (params['messages'],))
                    method, messages = params['messages'][0]
                    # We only store the latest state.
                    all_messages = messages_added.union(messages_removed)
                    messages = set(messages)
                    if method == '-':
                        messages_removed = messages_removed.union(messages - all_messages)
                    elif method == '+':
                        messages_added = messages_added.union(messages - all_messages)
                    else:
                        raise ValueError("messages method: %s" % method)
                if 'assignedto' in params:
                    old_owner = get_username(params['assignedto']) or ""
                    change = dict(change_templ)
                    change['type'] = 'owner'
                    change['value'] = data['owner']
                    data['owner'] = old_owner
                    changes.append(change)
                if 'topic' in params:
                    topics = project_state['topic']
                    for method, topic_args in params['topic']:
                        if method == '+':
                            topics = topics - set(topic_args)
                        elif method == '-':
                            topics = topics.union(set(topic_args))
                        else:
                            raise ValueError("unknown method: %s" %method)

                    project_state['topic'] = topics
                if 'title' in params:
                    change = dict(change_templ)
                    change['type'] = 'title'
                    change['value'] = data['title']
                    data['title'] = safe_str(params['title'])
                    changes.append(change)
                if 'duedate' in params:
                    change = dict(change_templ)
                    change['type'] = 'due-date'
                    change['value'] = data['due-date']
                    data['due-date'] = safe_ts(params['duedate'])
                    changes.append(change)
                if 'extlink' in params:
                    change = dict(change_templ)
                    change['type'] = 'extlink'
                    change['value'] = data['extlink']
                    data['extlink'] = params['extlink']
                    changes.append(change)
                if 'version' in params:
                    change = dict(change_templ)
                    change['type'] = 'version'
                    change['value'] = data['version']
                    data['version'] = params['version']
                    changes.append(change)
                if 'category' in params:
                    project_state['category'] = db.category.getnode(params['category']).name if params['category'] else None
                if 'status' in params or 'priority' in params:
                    prev_status = prev_project_state['status']
                    prev_priority = prev_project_state['priority']
                    if 'status' in params:
                        if params['status'] is None:
                            status = None
                        else:
                            status = db.status.getnode(params['status']).name
                    else:
                        status = prev_status
                    if 'priority' in params:
                        if params['priority'] is None:
                            priority = None
                        else:
                            priority = db.priority.getnode(params['priority']).name
                    else:
                        priority = prev_priority
                    prev_task_status = get_status(prev_status, prev_priority)
                    prev_task_priority = get_priority(prev_status, prev_priority)
                    task_status = get_status(status, priority)
                    task_priority = get_priority(status, priority)

                    if prev_task_status != task_status:
                        change = dict(change_templ)
                        change['type'] = 'status'
                        change['value'] = data['status']
                        data['status'] = task_status
                        changes.append(change)
                    if prev_task_priority != task_priority:
                        change = dict(change_templ)
                        change['type'] = 'priority'
                        change['value'] = data['priority']
                        data['priority'] = task_priority
                        changes.append(change)
                    project_state['status'] = status
                    project_state['priority'] = priority

                # prev_projects is chronologically later
                prev_projects = build_projects(prev_project_state)
                projects = build_projects(project_state)
                if prev_projects != projects:
                    if len(prev_projects - projects) > 0:
                        # The change adds projects.
                        change = dict(change_templ)
                        change['type'] = 'project'
                        change['method'] = '+'
                        change['value'] = list(prev_projects - projects)
                        data['projects'] = list(projects)
                        changes.append(change)
                    if len(projects - prev_projects) > 0:
                        # The change removes projects.
                        change = dict(change_templ)
                        change['type'] = 'project'
                        change['method'] = '-'
                        change['value'] = list(projects - prev_projects)
                        data['projects'] = list(projects)
                        changes.append(change)


            elif action == 'link':
                print "-", action, params
                # what is "issue" and linktype "superseder"
                (what, ident, linktype) = params
                pass
            elif action == 'unlink':
                print "-", action, params
                (what, ident, linktype) = params
                pass
            else:
                raise ValueError("Unknown change type")

            all_changes = changes + all_changes

        all_messages = messages_added.union(messages_removed)
        all_messages = sorted(list(all_messages))
        extra_messages = set(issue.messages) - set(all_messages)
        unknown_messages = set(messages_added) - set(issue.messages)
        if len(unknown_messages) > 0:
            raise ValueError("unknown messages: %r" % unknown_messages)
        if len(extra_messages) > 1:
            raise ValueError("More than one extra message: %r" % extra_messages)
        if len(extra_messages) == 1:
            description_message_id = list(extra_messages)[0]
            all_messages = [description_message_id] + all_messages
        else:
            description_message_id = None
        global DBDIR
        for message_id in all_messages:
            msg = db.msg.getnode(message_id)
            change = {}
            author = get_username(msg.creator)
            change['author'] = author
            change['ts'] = int(msg.creation.timestamp())
            change['type'] = 'add_comment'
            group = int(message_id) / 1000
            if message_id in messages_removed:
                change['value'] = ""
            else:
                with open(os.path.join(DBDIR, "db/files/msg/%i/msg%s" % (group, message_id))) as fh:
                    change['value'] = safe_str(fh.read()).strip()
            if message_id == description_message_id:
                if (change['author'] == data['author']
                    and abs(change['ts'] - data['ts'])) < 1000:
                    data['description'] = change['value']
                else:
                    raise ValueError("Inconsistent description: %s vs %s, %s vs %s"
                        % (change['author'], data['author'], change['ts'], data['ts']))
            else:
                all_changes.insert(0, change)
            first_message = False

        def cmp_change(a,b):
            if a['ts'] < b['ts']:
                return -1
            elif a['ts'] > b['ts']:
                return 1
            else:
                return 0
        all_changes.sort(cmp_change)

        null_keys = [key for key in data.keys() if data[key] is None]
        for key in null_keys:
            data.pop(key)
        if 'owner' in data and data['owner'] == '':
            data.pop('owner')
        if 'due-date' in data:
            # insert fake initial change
            all_changes.insert(0,
            { 'author': data['author'],
              'ts': data['ts'],
              'type': 'due-date',
              'value': data['due-date']})
            data.pop('due-date')
        if 'extlink' in data:
            # insert fake initial change
            all_changes.insert(0,
            { 'author': data['author'],
              'ts': data['ts'],
              'type': 'extlink',
              'value': data['extlink']})
            data.pop('extlink')
        if 'version' in data:
            # insert fake initial change
            all_changes.insert(0,
            { 'author': data['author'],
              'ts': data['ts'],
              'type': 'version',
              'value': data['version']})
            data.pop('version')
        if 'projects' in data:
            # insert fake initial change
            projects = data.pop('projects')
            if len(projects) > 0:
                all_changes.insert(0,
                                   { 'author': data['author'],
                                     'ts': data['ts'],
                                     'type': 'project',
                                     'method': '=',
                                     'value': projects })
        if 'description' not in data:
            data['description'] = ""
        data['changes'] = all_changes
        tasks.append(data)
    return tasks


def safe_ts(d):
    if d is None:
        return None
    return int(d.timestamp())


def safe_str(s):
    if s is None:
        return None
    try:
        return s.decode("utf-8")
    except:
        try:
            return s.decode("ISO-8859-1")
        except:
            return s.decode("latin1")

DBDIR = None

if __name__ == '__main__':
    DBDIR = sys.argv[1]
    tracker = instance.open(DBDIR)
    db = tracker.open('admin')

    # Some strings are not valid UTF-8. FIXME: Automagically correct.
    db.conn.text_factory = safe_str

    # clsname_list = db.getclasses()
    # # ['category', 'file', 'issue', 'keyword', 'msg', 'priority', 'query', 'status', 'user']
    # print db.user.is_retired(1862)
    # for clsname in clsname_list:
    #     cls = db.getclass(clsname)
    #
    #     retired = 0
    #     for ident in cls.getnodeids(retired=None):
    #         if cls.is_retired(ident):
    #             retired = retired + 1
    #         obj = cls.getnode(ident)
    #
    #     print "%s: %i (retired: %i)" % (clsname, cls.count(), retired)

    # # ['category', 'file', 'issue', 'keyword', 'msg', 'priority', 'query', 'status']

    if not os.path.exists("out"):
        os.makedirs("out")
    # Also sets up normalization data structure, so must always be called first.
    users = process_users(db)
    with open("out/users.json", "w") as fh:
        fh.write(json.dumps(users, indent=2))

    process_status(db)
    process_priority(db)

    tasks = process_tasks(db)
    with open("out/tasks.json", "w") as fh:
        fh.write(json.dumps(tasks, indent=2))
    #process_keywords(db)
    #process_query(db)
    #process_files(db)
