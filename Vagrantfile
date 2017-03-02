# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/xenial64"

  config.vm.network "forwarded_port", guest: 80, host: 8080

  config.vm.provider "virtualbox" do |v|
    v.memory = 2048
    v.cpus = 2
  end

  config.vm.provision "deploy", type: "ansible" do |ansible|
    ansible.verbose = "v"
    ansible.playbook = "deploy.yml"
    ansible.raw_arguments = ["-e", "ansible_python_interpreter=/usr/bin/python3"]
  end

  config.vm.provision "init", type: "ansible" do |ansible|
    ansible.verbose = "v"
    ansible.playbook = "init.yml"
    # Apparently this setting is used by the synchronize module on the host, too.
    # For NixOS, we can not use an absolute path, but this should work everywhere.
    ansible.raw_arguments = ["-e", "ansible_python_interpreter=python"]
  end

end
