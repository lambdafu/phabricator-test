bugs.gnupg.org
==============

Usernames
---------

* Some people had their email address as username.  This is not valid in phabricator.
  So '@' in usernames are replaced by '\_'.
* Also, ' ', '+', and '#' are replaced by '\_'.
* Some people had greek letters in their username. αβγ... are replace by abg...
* "Á" is replaced by "A".
* Some people had multiple accounts.  Those have been mapped to a single account based on email address and/or username.
* A few accounts had to be renamed manually.  Contact us if you have trouble.
* Phabricator doesn't like email address with "=" or "{^\_^}" as local-part.

Status and Priority
-------------------

Phabricator Status
* open
* resolved
* wontfix
* invalid
* duplicate
* spite

Phabricator priority
* unbreak
* triage
* high
* normal
* low
* wishlist

Roundup Status vs priority

| Status/Priority | crit | urg | bug  | feat | wish | nobug | minor | total |
|:----------------|:-----|:----|:-----|:-----|:-----|:------|:------|:------|
| unread          | 1    | 2   | 60   | 27   | 11   | 0     | 21    | 122   |
| deferred        | 0    | 0   | 6    | 2    | 1    | 0     | 0     | 9     |
| chatting        | 0    | 3   | 137  | 58   | 35   | 0     | 32    | 265   |
| need-eg         | 0    | 0   | 15   | 1    | 1    | 0     | 2     | 19    |
| in-progress     | 1    | 0   | 8    | 2    | 3    | 0     | 0     | 14    |
| testing         | 0    | 1   | 9    | 0    | 0    | 0     | 0     | 10    |
| done-cbb        | 0    | 0   | 0    | 0    | 0    | 0     | 0     | 0     |
| resolved        | 267  | 377 | 1258 | 199  | 182  | 118   | 88    | 2489  |
| not-released    | 0    | 2   | 8    | 1    | 0    | 1     | 1     | 12    |

Conclusions:
* (*any-status*, nobug) => (invalid)
* all other status either open or resolved
* priorities (crit, urg, bug, feat, wish, minor) => (unbreak, high, normal, normal, wish, low)
* prio feat gets extra tag "feature request" so we don't lose that info (in the future: phabricator supports ticket types)

In GnuPG, categories are more or less repos: http://git.gnupg.org/cgi-bin/gitweb.cgi

Keywords
--------

| Keyword     | Frequency |
|:------------|:----------|
| wontfix     | 109       |
| nobug       | 176       |
| noinfo      | 65        |
| tooold      | 120       |
| notdup      | 5         |
| mistaken    | 67        |
| faq         | 5         |
| patch       | 22        |
| asm         | 8         |
| iobuf       | 1         |
| keyserver   | 10        |
| ssh         | 9         |
| w32         | 57        |
| scd         | 33        |
| agent       | 43        |
| smime       | 28        |
| openpgp     | 17        |
| cross       | 1         |
| macos       | 13        |
| kks         | 8         |
| gpg4win     | 68        |
| pinentry    | 26        |
| uiserver    | 4         |
| i18n        | 8         |
| backport    | 14        |
| gpg14       | 36        |
| endoflife   | 12        |
| dup         | 1         |
| doc         | 27        |
| gpg20       | 34        |
| ipc         | 0         |
| w64         | 13        |
| npth        | 3         |
| clangbug    | 3         |
| eol         | 1         |
| forwardport | 1         |
| gpgtar      | 3         |
| isc13       | 0         |
| gpg21       | 55        |
| spam        | 1         |
| dirmngr     | 51        |
| maybe       | 1         |
| kleopatra   | 9         |
| debian      | 3         |
| fedora      | 3         |
| sillyUB     | 1         |
| question    | 13        |
| gpgol-addin | 19        |
| gpg23       | 6         |
| gpg22       | 24        |
| python      | 2         |
| tofu        | 6         |
| tests       | 1         |
| qt          | 1         |
| rc          | 1         |
| gpgv        | 1         |

Custom Fields
============
```
{
  "gnupg.due-date": {
    "name": "Due Date",
    "type": "date",
    "caption": "Deadline"
  },
  "gnupg.extlink": {
    "name": "External Link",
    "type": "link",
    "caption": "External Link"
  },
  "gnupg.version": {
    "name": "Version",
    "type": "text",
    "caption": "Version"
  }

}
```

TODO
=====

* https://bugs.gnupg.org/gnupg/issue1493 ticket reference


Phabricator
===========

* https://secure.phabricator.com/book/phabricator/article/arcanist_quick_start/
* https://secure.phabricator.com/T1205 allow external users to email phabricator, cf. https://phabricator.wikimedia.org/T52

Examples
========

* T2034 (subtasks, mentions)
* T2905 (external link)
* T2941 (git rev)
