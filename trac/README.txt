I have used this to export a medium-sized trac project (20 user, 3000
tickets, 400 attachments, 3 custom fields).

However, the projects.json file has to be written by hand, and there
is a lot of configuration to be done.

Large attachments must be uploaded manually.

Spaces and workboards need to be managed manually in post-processing.

I am including it here because it may be useful for anyone who has to
do a similar task, but please be aware that you may need to do some
manual digging in the trac database and/or the code.
