# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant::Config.run do |config|
  config.vm.box = "ubuntu/xenial64"

  # Forward a port from the guest to the host, which allows for outside
  # computers to access the VM, whereas host only networking does not.
  config.vm.forward_port 80, 8080

  config.vm.provision "deploy", type: "ansible" do |ansible|
    ansible.verbose = "v"
    ansible.playbook = "deploy.yml"
    ansible.raw_arguments = ["-e", "ansible_python_interpreter=/usr/bin/python3"]
  end

  config.vm.provision "init", type: "ansible" do |ansible|
    ansible.verbose = "v"
    ansible.playbook = "init.yml"
    ansible.raw_arguments = ["-e", "ansible_python_interpreter=/usr/bin/python3"]
  end

  # Boot with a GUI so you can see the screen. (Default is headless)
  # config.vm.boot_mode = :gui

  # Assign this VM to a host-only network IP, allowing you to access it
  # via the IP. Host-only networks can talk to the host machine as well as
  # any other machines on the same network, but cannot be accessed (through this
  # network interface) by any external networks.
  # config.vm.network :hostonly, "192.168.33.10"

  # Assign this VM to a bridged network, allowing you to connect directly to a
  # network using the host's network device. This makes the VM appear as another
  # physical device on your network.
  # config.vm.network :bridged

  # Share an additional folder to the guest VM. The first argument is
  # an identifier, the second is the path on the guest to mount the
  # folder, and the third is the path on the host to the actual folder.
  # config.vm.share_folder "v-data", "/vagrant_data", "../data"

end
