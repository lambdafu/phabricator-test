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

class Conf(object):
    def __init__(self, confdir):
        with open(os.path.join(confdir, "users.json")) as fh:
            self.users = json.load(fh)

        # with open(os.path.join(confdir, "emails.json")) as fh:
        #     self.emails = json.load(fh)
        #
        # with open(os.path.join(confdir, "components.json")) as fh:
        #     self.components = json.load(fh)
        # self.r_components = dict()
        # for comp, aliases in self.components.items():
        #     self.r_components[comp] = comp
        #     for alias in aliases:
        #         self.r_components[alias] = comp
        #
        # with open(os.path.join(confdir, "type.json")) as fh:
        #     self.ticket_type = json.load(fh)

        with open(os.path.join(confdir, "priority.json")) as fh:
            self.priority = json.load(fh)

        with open(os.path.join(confdir, "priority-projects.json")) as fh:
            self.priority_projects = json.load(fh)

        with open(os.path.join(confdir, "category.json")) as fh:
            self.category = json.load(fh)

        # with open(os.path.join(confdir, "keywords.json")) as fh:
        #     self.keywords = json.load(fh)
        #
        # with open(os.path.join(confdir, "portals.json")) as fh:
        #     self.portals = json.load(fh)

        with open(os.path.join(confdir, "status.json")) as fh:
            self.status = json.load(fh)

        with open(os.path.join(confdir, "status-projects.json")) as fh:
            self.status_projects = json.load(fh)

        # with open(os.path.join(confdir, "milestones.json")) as fh:
        #     self.milestones = json.load(fh)

        self.extlink_projects = {}
        with open(os.path.join(confdir, "extlink-projects.json")) as fh:
            extlink_projects = json.load(fh)
        for regex, projects in extlink_projects.items():
            self.extlink_projects[re.compile(regex)] = projects

    def get_username(self, email, username):
        return self.users.get(email, username)

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

    def get_keywords(self, keyword):
        return self.keywords[keyword]

    def get_portals(self, portal):
        return self.portals[portal]

    def get_status(self, status):
        return self.status[status]

    def get_status_projects(self, status):
        if status is None:
            return set()
        return set(self.status_projects[status])

    def get_milestone(self, milestone):
        return self.milestones[milestone]

conf = Conf("conf")




keyword_map = {
    'iobuf': (), # 1/1 issues
    'asm': (), # 8/8 issues
    'keyserver': (), # 10/10 issues
    'ssh': (), # 9/9 issues
    'w32': (), # 57/57 issues
    'wontfix': (), # 109/109 issues
    'nobug': (), # 176/176 issues
    'scd': (), # 33/33 issues
    'noinfo': (), # 65/65 issues
    'tooold': (), # 120/120 issues
    'agent': (), # 43/44 issues
    'smime': (), # 28/28 issues
    'openpgp': (), # 17/17 issues
    'cross': (), # 1/1 issues
    'faq': (), # 5/5 issues
    'notdup': (), # 5/5 issues
    'macos': (), # 13/13 issues
    'mistaken': (), # 67/67 issues
    'patch': (), # 22/22 issues
    'kks': (), # 8/8 issues
    'gpg4win': (), # 68/68 issues
    'pinentry': (), # 26/26 issues
    'uiserver': (), # 4/4 issues
    'i18n': (), # 8/8 issues
    'backport': (), # 14/15 issues
    'gpg14': (), # 36/36 issues
    'endoflife': (), # 12/12 issues
    'dup': (), # 1/1 issues
    'doc': (), # 27/27 issues
    'gpg20': (), # 34/34 issues
    'ipc': (), # 0/0 issues
    'w64': (), # 13/13 issues
    'npth': (), # 3/3 issues
    'clangbug': (), # 3/3 issues
    'eol': (), # 1/1 issues
    'forwardport': (), # 1/1 issues
    'gpgtar': (), # 3/3 issues
    'isc13': (), # 0/0 issues
    'gpg21': (), # 55/55 issues
    'spam': (), # 1/1 issues
    'dirmngr': (), # 51/51 issues
    'maybe': (), # 1/1 issues
    'kleopatra': (), # 9/9 issues
    'debian': (), # 3/3 issues
    'fedora': (), # 3/3 issues
    'sillyUB': (), # 1/1 issues
    'question': (), # 13/13 issues
    'gpgol-addin': (), # 19/19 issues
    'gpg23': (), # 6/6 issues
    'gpg22': (), # 24/24 issues
    'python': (), # 2/2 issues
    'tofu': (), # 6/6 issues
    'tests': (), # 1/1 issues
    'qt': (), # 1/1 issues
    'rc': (), # 1/1 issues
    'gpgv': () # 1/1 issues
}


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
        by_email[user.address].append(user)
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
            data['email'] = user.address
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
    return projects

def process_tasks(db):
    dbissues = db.issue

    tasks = []
    for ident in dbissues.getnodeids(retired=None):
        is_retired = dbissues.is_retired(ident)
        issue = dbissues.getnode(ident)
        author = issue.creator
        author = user_normal.get(author, author)
        author = db.user.getnode(author)
        status = db.status.getnode(issue.status).name
        cat = db.category.getnode(issue.category).name if issue.category else None
        assignee = db.user.getnode(issue.assignedto).username if issue.assignedto else None
        priority = db.priority.getnode(issue.priority).name if issue.priority else "triage"
        topics = map(lambda x: db.keyword.getnode(x).name,issue.topic)
        msgs = map(lambda x: db.msg.getnode(x),issue.messages)
        files = map(lambda x: db.file.getnode(x),issue.files)
        nosy = map(lambda x: db.user.getnode(x),issue.nosy)
        superseder = map(lambda x: db.issue.getnode(x),issue.superseder)

        # missing: extlink, version
        if is_retired:
             # Spam, FIXME
            continue

        data = {}
        data['id'] = int(ident)
        data['ts'] = int(issue.creation.timestamp())
        data['author'] = author.username
        data['owner'] = issue.assignedto
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

        project_state = {
            'status': status,
            'priority': priority,
            'category': cat,
            'extlink': issue.extlink
        }

        data['projects'] = list(build_projects(project_state))

        print "[ISSUE %s] %s (%s) in %s (%s) with %d messages, %d files, superseder by %d and %d subscribers" % \
                (issue.id, issue.title, status, cat, ",".join(topics),len(msgs),len(files),len(superseder),len(nosy))

        # The issue data is the current state, and the history
        # contains previous values.  By walking the history backwards, we
        # can recover the original ticket and all changes easily.
        all_changes = []
        history = issue.history()
        history.sort() # (id, date, ...)
        history.reverse()
        for hist_item in history:
            (_, date, change_author, action, params) = hist_item
            change_author = user_normal.get(change_author, change_author)
            change_author = db.user.getnode(change_author)

            changes = []
            change_templ = {}
            change_templ['ts'] = int(date.timestamp())
            change_templ['author'] = change_author.username
            if action == 'create':
                # Ignore
                pass
            elif action == 'set':
                print "-", action, params
                known_params = set(['files', 'messages', 'assignedto',
                'topic', 'category', 'nosy', 'superseder',
                'status', 'priority',
                'extlink', 'title', 'duedate', 'version'])
                unknown_params = set(params.keys()) - known_params
                if len(unknown_params) > 0:
                    raise ValueError("Unknown params: %r" % unknown_params)

                prev_project_state = dict(project_state)
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
                        change['type'] = 'projects'
                        change['method'] = '+'
                        change['value'] = list(prev_projects - projects)
                        data['projects'] = list(projects)
                        changes.append(change)
                    if len(projects - prev_projects) > 0:
                        # The change removes projects.
                        change = dict(change_templ)
                        change['type'] = 'projects'
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

        null_keys = [key for key in data.keys() if data[key] is None]
        for key in null_keys:
            data.pop(key)
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

if __name__ == '__main__':
    tracker = instance.open(sys.argv[1])
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
