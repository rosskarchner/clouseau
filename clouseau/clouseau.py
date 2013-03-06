#! /usr/bin/ENV python
# -*- coding: utf-8 -*-
#
# Clouseau, a silly git repo inspector
#
#
import os
import subprocess
import re
import json
import argparse as arse
import sys
from jinja2 import Template, Environment, PackageLoader
from colors import *


VERSION='0.1.0'


#
# To Do: Make Clouseau the API. Decouple console client.
# Clouseau accepts arguments and returns a predictable data structure.
# 
# Perhaps Clouseau accepts a client with a known interface; e.g., client.render() or
# client.render_to( location )
#
class Clouseau:
    """
    Wrap and delegate
    """
    

    def __init__(self):
        pass


    def main(self , _args, terms=['gov','password','pwd', 'user', 'cfpb']):
        args = self.parse_args( _args )
#        print args
        parser = Parser()
        terms = args['patterns'].readlines()
        terms = [term.strip() for term in terms if not term.startswith('#')]
        #print terms
        self.clone_repo( args['url'], args['repo_dir'] ) 
        self.render_to_console( terms, args )
        


    # This belongs in a console client. Let's clarify the interface
    def render_to_console(self, terms, parsed):
        """
        Much refactoring to do!
            - setup Jinja and template
            - fetch data (parse)
            - highlight search terms
            - render template
            - fix/improve paging
         
        """
        p = Parser()
        env = Environment(loader=PackageLoader('clouseau', 'templates'))
        env.filters['purple'] = purple
        env.filters['cyan'] = cyan
        env.filters['darkcyan'] = darkcyan
        env.filters['blue'] = blue
        env.filters['darkblue'] = darkblue
        env.filters['red'] = red
        env.filters['darkred'] = darkred
        env.filters['green'] = green
        env.filters['darkgreen'] = darkgreen
        env.filters['yellow'] = yellow
        env.filters['smoke'] = smoke
        env.filters['bold'] = bold
        env.filters['ok'] = ok
        env.filters['fail'] = fail
        env.filters['gray'] = gray
        env.filters['orange_bg'] = orange_bg
          
        template = env.get_template('console.html')
    
        ids = p.parse(terms, parsed['repo_dir'], kargs=parsed )
        #print ids

       # Highlight (Ack! This feels like the worst code I've written) 
        for item in ids:
            for x in ids[item]:
                for y in ids[item][x]:
                    if y == 'matched_lines':
                        match = ids[item][x][y]
                        for m in match:
                            for term in terms:
                                if term == item:
                                    regx = re.compile(term)
                                    match = regx.search( m[1] )
                                    if match:
                                        m[1] = m[1].replace( match.group(0) , orange_bg( match.group(0)  ) ) 
                                    # This matches only the term, not the matched expression
                                    #m[1] = m[1].replace(term, orange_bg(term) ) 


        
        
        data_to_render = template.render(data=ids)
        #From git core 
        try:
            pager = subprocess.Popen(['less', '-F', '-R', '-S', '-X', '-K'], stdin=subprocess.PIPE, stdout=sys.stdout)
            lines = data_to_render.split('\n')
            #print lines
            for line in lines:
                pager.stdin.write( line.encode('utf-8') + '\n' )
            pager.stdin.close()
            pager.wait()
        except KeyboardInterrupt:
            pass





    def clone_repo(self, url, destination):
        try:
            _out = subprocess.check_output(['git', 'clone', url, destination])        
        
        except subprocess.CalledProcessError:
            print blue( "Directory, %s, exits. Trying git-pull instead of clone." % destination )
            _out = subprocess.check_output(['git', '--git-dir=%s/.git' % destination, 'pull'])       
            print smoke( "Git says: %s" % _out )
        
        except :
            e = sys.exc_info()[0]
            print red( 'Problem writing to destination: %s' % destination ) 
            raise
        
        return _out
            


    # Belongs in console client
    def parse_args( self, arguments ):

        #print ( os.path.abspath( 'clouseau/patterns/patterns.txt' ) )
        p = arse.ArgumentParser (description="  Clouseau: A silly git inspector", version=VERSION)
        p.add_argument('--url', '-u', required=True,  action="store", dest="url",
                        help="Fully qualified git URL (http://www.kernel.org/pub//software/scm/git/docs/git-clone.html)")
        p.add_argument('--patterns', '-p', action="store", dest="patterns", type=file ,  default="clouseau/patterns/patterns.txt",
                        help="Path to list of regular expressions to use.")
        p.add_argument('--clean', '-c',  dest="clean", action="store_true", default=False, 
                        help="Delete the existing git repo and re-clone")
        p.add_argument('--output', '-o', dest="output_format", required=False, 
                        help="Output formats: console, markdown, raw, html, json")
        p.add_argument('--output-destination', '-od', dest="output_destination", required=False, 
                        help="Location where the output is to be stored. Default ./temp.")
        p.add_argument('--dest', '-d', dest="dest", default="temp", 
                        help="The directory where the git repo is stored. Default: ./temp")
        p.add_argument('--pathspec', '-ps', required=False, dest="pathspec",
                        help="The pattern of files or commits to search. Default: all.")

        args = p.parse_args( arguments )
        url = args.url.rstrip('/')
        github_url = url.rstrip('.git')
        repo = url.rsplit('/',1)[1]
        repo_name = repo.rstrip('.git')
        self.args = args
        return { "url": url,
                 "github_url": github_url ,
                 "repo": repo,
                 "repo_name": repo_name,
                 "repo_dir": ("%s/%s" % (args.dest,repo_name) ),
                 "clean": args.clean,
                 "output_format": args.output_format,
                 "dest": args.dest,
                 "patterns": args.patterns,
                 "pathspec": args.pathspec
              }






class Parser:    
    """
    Converts git-grep's stdout to Python dictionary
    """
    
    def __init__(self):
        pass

    def parse(self, terms, repo, **kargs):
        """
        For each term in @terms perform a search of the git repo and store search results
        (if any) in an iterable.
        """
        #print kargs['kargs']

        # Lexemes:
        file_name_heading = re.compile( '^[0-9a-zA-Z]{40}:.+$' )
        function_name = re.compile( '^[0-9]+=' )            
        matched_line = re.compile( '^[0-9]+:' ) 
        
        # Main results data structure
        clouseau = {}

        clouseau.update( {'meta' : {'github_url': kargs['kargs']['github_url']} } )
        #print clouseau

        # - A collection of nodes
        #ast_root = Node( type='root', value=None, parent=None )
        os.chdir( repo )
        

        if ( kargs['kargs']['pathspec'] != None ):
            rev_list = kargs['kargs']['pathspec'] 
        else:
            #May be large
            git_revlist = subprocess.Popen( ['git' ,'rev-list' ,'--all' ], \
                                        stderr=subprocess.PIPE, stdout=subprocess.PIPE )
        
            rev_list = git_revlist.communicate()[0]
            
        term = None

        for term in terms:
            
            git_grep_cmd = ['git','grep','-inwa', '--heading', '--no-color', \
                                '--max-depth','-1', '-E', '--break', '--', term]
            
            cmd = git_grep_cmd + rev_list.split()

            #print cmd

            git_grep = subprocess.Popen( cmd , stderr=subprocess.PIPE, 
                                         stdout=subprocess.PIPE)
            # Maybe write it all to a file first, aka Raw.log, and then parse that, which could 
            # allow for multiple passes

            (out,err) = git_grep.communicate()
        
            clouseau.update( {term: {}}  )

            for line in out.split('\n'):
                # We don't  know how a lot of the data is encoded, so make sure it's utf-8 before 
                # processing
                if line == '':
                    continue
                try:
                    line = unicode( line, 'utf-8' ) 
                except UnicodeDecodeError:
                    line = unicode( line, 'latin-1' ) 
                

                if file_name_heading.match( line ):
                    title = line.split(':', 1)[1]
                    title = line.replace('/','_')
                    title = title.replace('.','_').strip()
                    _src = line.strip().encode('utf-8')
                    _srca = _src.split(':', 1)
                    clouseau[term][title] = {'src' : _srca[1] }
                    clouseau[term][title]['refspec'] =  _srca[0]
                    #clouseau[term][title] = {'ref' : _srca[0] }
                    clouseau[term][title]['matched_lines'] = []
                    continue

                if function_name.match( line ):
                    function = line.split('=')
                    clouseau[term][title].update( {'function': function} ) 
                    #Node( type='function', value=function, parent=node )
                    clouseau[term][title].update( {'matches': len(function)} )
                    continue

                if matched_line.match( line ):
                    matched = line.split(':' , 1)
                    matched[0] = matched[0].strip()
                    matched[1] = matched[1].strip()
                    clouseau[term][title]['matched_lines'].append( matched )
                    continue
                    #Node( type='matched_line', value=line.split(':',1), parent=node )

        return clouseau








class Node:
    """
    Placeholder ....
    """
    
    def __init__(self,type,value,parent):
        self.type = type
        self.value = value
        self.parent = parent

    def visit(self, _lambda):
        """
        Recursivley visits this node and all children 
        """
        pass
