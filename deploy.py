import os
import urllib.request
import randommac as rm

def system_command(cmd):
    #runs a command and waits for completion
    os.system(cmd)

def download_file(url, filename):
    with urllib.request.urlopen(url) as response:
        with open(filename, "wb") as fd:
            for chunk in response.read().iter_bytes():
                fd.write(chunk)

def create_config_file(filename, content):
    with open(filename, "w") as fd:
        fd.write(content)

def main():
    #Run system commands
    update = "apt-get update && apt-get -y upgrade && apt-get install -y nmap python3-pip "
    system_command(update)


    download_file("https://example.com/file1.txt", "file1.txt")
    download_file("https://example.com/file2.txt", "file2.txt")

    create_config_file("config.txt", "This is my configuration file.")

if __name__ == "__main__":
    main()