all: out/users.json
	rm -fR out/files
	mkdir out/files
	python export-trac.py dump-attachments --db-file data/trac.db --attachment-dir data/attachments --server-dir out/files 
	python export-trac.py dump-tickets --db-file data/trac.db --trac-key trac

out/users.json: export-trac.py data/trac.db conf/trac-scrub.yaml
	python export-trac.py users-dump-json --db-file data/trac.db 



