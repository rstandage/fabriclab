<html>
<head>
	<title></title>
</head>
<body data-gr-ext-installed="" data-new-gr-c-s-check-loaded="8.907.0" data-new-gr-c-s-loaded="8.907.0">
<h3>Pre-reqs</h3>

<ol>
	<li>Install <a href="https://www.proxmox.com/en/downloads/proxmox-virtual-environment/iso/proxmox-ve-8-0-iso-installer">Proxmox latest</a></li>
	<li>Set static IP on eth0 for management</li>
</ol>

<h3>Process for creating virtual fabric</h3>

<ul>
	<li>run apt-update and install some stuff
	<ul>
		<li><code>&nbsp;apt-get update &amp;&amp; apt-get -y upgrade &amp;&amp; apt-get install -y nmap python3-pip git</code></li>
	</ul>
	</li>
	<li>create directories
	<ul>
		<li>&nbsp;&nbsp;&nbsp; &nbsp;<code>mkdir /var/lib/vz/template/qcow/</code> # for storing qcow files</li>
	</ul>
	</li>
	<li>download files
	<ul>
		<li>Download <a href="https://support.juniper.net/support/downloads/?p=vjunos">vJunos</a> and place in newly created qcow directory</li>
		<li>&nbsp;SSR iso (download via gui or wget to /var/lib/vz/template/iso)</li>
		<li>&nbsp;SRX iso (download via gui or wget to /var/lib/vz/template/qcow)</li>
		<li>&nbsp;ubuntu for hosts iso (download via gui or wget to /var/lib/vz/template/iso)</li>
		<li>&nbsp;mist edge iso (download via gui or wget to /var/lib/vz/template/iso)</li>
	</ul>
	</li>
	<li>sync with github&nbsp;
	<ul>
		<li><code>git clone https://github.com/rstandage/fabriclab.git</code></li>
	</ul>
	</li>
	<li>make scripts executable
	<ul>
		<li><code>chmod +x ~/fabriclab/create_vswitch.py</li></code>
		<li><code>chmod +x ~/fabriclab/enable_lldp.sh</li></code>
	</ul>
	</li>
	<li>create networks and restart networking
	<ul>
		<li><code>nano ~/fabriclab/interfaces.txt</code> # modify IP details on mgmt interface to match static details created on boot</li>
		<li><code>cp /etc/network/interfaces /etc/network/interfaces.bak</code> # create backup of initial network config</li>
		<li><code>cp ~/fabriclab/interfaces.txt /etc/network/interfaces</code> # copy interface config to network file</li>
		<li><code>systemctl restart networking</code></li>
	</ul>
	</li>
	<li>set enable_lldp.sh to run on boot
	<ul>
		<li><code>crontab -e</code> # edit cron tasks file</li>
		<li>add the following to the bottom of the file</li>
	</ul>
	</li>
</ul>

<div style="background:#eee;border:1px solid #ccc;padding:5px 10px;">
<p><code># enable lldp for Linux bonds<br />
@reboot /root/fabriclab/enable_lldp.sh</code></p>
</div>

<p>&nbsp;</p>

<p>&nbsp;</p>

<ul>
	<li>create virtual switches
	<ul>
		<li><code>./fabriclab/create_vswitch.py</code></li>
		<li><code>vm_name needs to be a valid domain name. Script will append '.switch' as uld &#39;core-a.switch&#39; </code></li>
		<li>vm_id is a three digit UID, for example &#39;201&#39;. This will also denote the port for the console ( in this case would be 5201)</li>
	</ul>
	</li>
	<li>modify assigned bridges on switches for the required connectivity
	<ul>
		<li>by default all interfaces are in bond500</li>
		<li>best done via GUI, bonds are named for their function ( e.g. c1-a1 means core1 to access1) and act as a point-to-point sudo wire</li>
	</ul>
	</li>
	<li>adopt switches
	<ul>
		<li>console into the switches from the proxmox cli using &#39;telnet localhost 5{vm_id}'</li>
		<li>log on with &#39;root&#39; no password</li>
		<li>set root password 'set system root-authentication plaintext'</li>
		<li>paste 'adopt switch' config from Mist portal</li>
		<li>commit</li>
	</ul>
	</li>
	<li>create switch template</li>
	<ul>
		<li>fabric_demo.json can be imported as an example</li>
	</ul>
	<li>create site</li>
	<li>assign switches to site</li>
	<ul>
		<li>Name Switches and apply roles</li>
	</ul>
	<li>build fabric
	<ul>
		<li>if lldp is not working, manaully run ~/fabriclab/enable_lldp.sh</li>
	</ul>
	</li>
</ul>
</body>
<grammarly-desktop-integration data-grammarly-shadow-root="true"></grammarly-desktop-integration></html>
