bugs.gnupg.org
==============

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

Status/Priority | crit | urg | bug | feat | wish | nobug | minor | total
----------------|------|-----|-----|------|------|-------|-------|------
unread          |     1|    2|   60|    27|    11|      0|     21|   122
deferred        |     0|    0|    6|     2|     1|      0|      0|     9
chatting        |     0|    3|  137|    58|    35|      0|     32|   265
need-eg         |     0|    0|   15|     1|     1|      0|      2|    19
in-progress     |     1|    0|    8|     2|     3|      0|      0|    14
testing         |     0|    1|    9|     0|     0|      0|      0|    10
done-cbb        |     0|    0|    0|     0|     0|      0|      0|     0
resolved        |   267|  377| 1258|   199|   182|    118|     88|  2489
not-released    |     0|    2|    8|     1|     0|      1|      1|    12

Conclusions:
* (*any-status*, nobug) => (invalid)
* all other status either open or resolved
* priorities (crit, urg, bug, feat, wish, minor) => (unbreak, high, normal, normal, wish, low)
* prio feat gets extra tag "feature request" so we don't lose that info (in the future: phabricator supports ticket types)

In GnuPG, categories are more or less repos: http://git.gnupg.org/cgi-bin/gitweb.cgi
