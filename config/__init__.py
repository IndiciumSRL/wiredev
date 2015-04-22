import ConfigParser

config = None

if config == None:
    config = ConfigParser.SafeConfigParser()
    config.read('wiredev.conf')