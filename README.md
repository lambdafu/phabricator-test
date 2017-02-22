Use
===

```
vagrant up --provider virtualbox
```

Which is equivalent to:

```
vagrant up --provider virtualbox --no-provision
vagrant provision --provision-with deploy
vagrant provision --provision-with init
```

Then go to

http://127.0.0.1:8080/

and recover the admin password and follow the instructions:

```
vagrant ssh -c "/opt/phacility/phabricator/bin/auth recover admin"
```

Replay Data
===========

vagrant provision --provision-with init

TODO
====

* git ssh access
