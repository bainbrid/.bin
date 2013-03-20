#! /usr/bin/env python

__doc__     = "shell-like environment to navigate in root files. Similar to rootpy roosh, but with no rootpy deps and faster to load"
__author__  = "Mauro Verzetti (mauro.verzetti@cern.ch)"

import sys
from cStringIO import StringIO
import os
import re
import fnmatch
from optparse import OptionParser
import rootfind
import ROOT

class stdout_locker(object):
    def __init__(self):
        self.locked = False
        self.backup = None
        
    def lock(self):
        if not self.locked:
            self.backup = sys.stdout
            sys.stdout  = StringIO()
            self.locked = True
            
    def read(self):
        if self.locked:
            ret = sys.stdout.getvalue()
            sys.stdout.close()       # close the stream 
            sys.stdout = self.backup # restore original stdout
            self.locked = False
            return ret


#most probably redundant
global __main_dir 
global __file     
global __file_name
global __PWD      
global __env_vars

__main_dir = None
__file     = None
__file_name= None
__PWD      = ''
__env_vars = re.compile("\$\w+")
__BLUE     = '\033[94m'
__GREEN    = '\033[92m'
__RED      = '\033[91m'
__END_COL  = '\033[0m'
__locker   = stdout_locker()
__file_map = {}



def write_file_map_entry(obj):
    color = ''
    if obj.InheritsFrom('TH1'):
        color = __RED
    elif obj.InheritsFrom('TTree'):
        color = __GREEN
    elif obj.InheritsFrom('TDirectory'):
        color = __BLUE

    return {
        'name' : obj.GetName(),
        'color': color,
        'cname': obj.ClassName(),
        'title': obj.GetTitle(),
        }

def MapDirStructure( directory, dirName ):
    dirContent = rootfind.GetContent(directory)
    for entry in dirContent:
        pathname = os.path.join(dirName,entry.GetName())
        __file_map[pathname] = write_file_map_entry(entry)
        if entry.InheritsFrom('TDirectory'):
            MapDirStructure(entry, pathname)

def get_proper_path(path):
    'relative to absolute path translation'
    ret = re.sub('\w+/\.\./?','',path)
    ret = ret.replace('//','/')
    ret = ret.replace('./','')
    ret = ret.strip('/')
    if ret == path:
        return ret
    else:
        return get_proper_path(ret)

def absolute_to_relative(path):
    'absolute to relative path translation'
    #Finds the longest common prefix of two strings, as effecicient as possible since it is likely to be repeated multiple times
    if path == __PWD: #special case to avoid empty string
        return '../'+path.split('/')[-1]
    dir_pwd = __PWD.split('/')
    dir_pat = path.split('/')
    max_len = min( len(dir_pwd), len(dir_pat) )
    char    = max_len
    for i in xrange(max_len):
        if dir_pwd[i] != dir_pat[i]:
            char = i
    ret = '/'.join(dir_pat[char:])
    backs = len(dir_pwd[char:]) if __PWD != '' else 0
    return '../'*backs+ret
        
    
def get_object(path):
    'gets the root object'
    return __file.Get(path) if path != '' else __file

def expand_vars(string):
    ret = string
    for var in __env_vars.findall(string):
        if var.strip('$') in os.environ:
            ret = ret.replace(var,os.environ[var.strip('$')])
    return ret

def ls(*args):
    parser = OptionParser(description='List information about the OBJECTSs (the current directory by default).')
    parser.add_option('--no-colors', action='store_true', default = False,
                      help='allows the search for a particular pattern', dest='no_color')
    parser.add_option('-l', action='store_true', default = False, dest='list',
                      help='use a long listing format')
    args = list(args)
    try:
        options, arguments = parser.parse_args(args=args[1:])
    except SystemExit:
        return 0

    def _color_name(entry, tocolor):
        if options.no_color or not entry['color']:
            return  tocolor
        else:
            return  entry['color']+tocolor+__END_COL
    
    directory = arguments[0] if len(arguments) else '*'
    pattern   = get_proper_path(__PWD+'/'+directory)
    # add /* in case it's a directory FIXME add -d option
    pattern   = pattern+'/*' if (pattern in __file_map and __file_map[pattern]['color'] == __BLUE) else pattern
    pattern   = '*' if pattern == '' else pattern
    pattern   = fnmatch.translate(pattern) #translate linux-like matching into regex
    pattern   = pattern.replace('.*','\w*') #the translation is not perfect, / is not treated as special
    regex     = re.compile(pattern)
    for path, entry in __file_map.iteritems():
        if regex.match(path):
            if not options.list:
                print  _color_name( entry, absolute_to_relative(path) )
            else:
                print  '%30s%30s       %s' % (entry['cname'], _color_name( entry, absolute_to_relative(path) ), entry['title']) 
    print
    return 0

def cd(*args):
    new_pwd = get_proper_path(globals()['__PWD']+'/'+args[1]) #for some reason it sees it as local and local only
    obj     = get_object(new_pwd)
    if obj and obj.InheritsFrom('TDirectory'):
        globals()['__PWD'] = new_pwd
        return 0
    elif obj:
        print "%s does not exist"
        return 1
    else:
        print "%s is not a direcotry!"
        return 1

def find(*args):
    args = list(args)
    try:
        (options, directory) = rootfind.parse_options(args[1:])
    except SystemExit:
        return 0
    directory = directory[0]
    rootfind.rootfind( get_object(get_proper_path(__PWD+'/'+directory)), directory, **vars(options) )
    return 0

def sys_exit(*args):
    exit()
    
__cmds = {
    'ls'   : ls,
    'cd'   : cd,
    'find' : find,
    'exit' : sys_exit,
    }

def execute_command( cmd ):
    argvs = cmd.split(' ')
    if argvs[0] in __cmds:
        __locker.lock()
        __cmds[argvs[0]](*argvs)
        print __locker.read(),
    

def shell():
    while True:
        cmd = raw_input("%s:%s> " % (__file_name,__PWD) )
        #remove leading/trailing spaces
        cmd = cmd.strip()
        #expand env variables to their values
        cmd = expand_vars(cmd)
        execute_command(cmd)

if __name__ == '__main__':
    __file_name= sys.argv[-1]
    __file     = ROOT.TFile.Open(__file_name)
    MapDirStructure(__file,'') #Initialize file map
    shell()
    
