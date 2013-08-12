# rgToolFactory.py
# see https://bitbucket.org/fubar/galaxytoolfactory/wiki/Home
# 
# copyright ross lazarus (ross stop lazarus at gmail stop com) May 2012
# 
# all rights reserved
# Licensed under the LGPL
# suggestions for improvement and bug fixes welcome at https://bitbucket.org/fubar/galaxytoolfactory/wiki/Home
#
# January 2013
# problem pointed out by Carlos Borroto
# added escaping for <>$ - thought I did that ages ago...
#
# August 11 2012 
# changed to use shell=False and cl as a sequence

# This is a Galaxy tool factory for simple scripts in python, R or whatever ails ye.
# It also serves as the wrapper for the new tool.
# 
# you paste and run your script
# Only works for simple scripts that read one input from the history.
# Optionally can write one new history dataset,
# and optionally collect any number of outputs into links on an autogenerated HTML page.

# DO NOT install on a public or important site - please.

# installed generated tools are fine if the script is safe.
# They just run normally and their user cannot do anything unusually insecure
# but please, practice safe toolshed.
# Read the fucking code before you install any tool 
# especially this one

# After you get the script working on some test data, you can
# optionally generate a toolshed compatible gzip file
# containing your script safely wrapped as an ordinary Galaxy script in your local toolshed for
# safe and largely automated installation in a production Galaxy.

# If you opt for an HTML output, you get all the script outputs arranged
# as a single Html history item - all output files are linked, thumbnails for all the pdfs.
# Ugly but really inexpensive.
# 
# Patches appreciated please. 
#
#
# long route to June 2012 product
# Behold the awesome power of Galaxy and the toolshed with the tool factory to bind them
# derived from an integrated script model  
# called rgBaseScriptWrapper.py
# Note to the unwary:
#   This tool allows arbitrary scripting on your Galaxy as the Galaxy user
#   There is nothing stopping a malicious user doing whatever they choose
#   Extremely dangerous!!
#   Totally insecure. So, trusted users only
#
# preferred model is a developer using their throw away workstation instance - ie a private site.
# no real risk. The universe_wsgi.ini admin_users string is checked - only admin users are permitted to run this tool.
#

import sys 
import shutil 
import subprocess 
import os 
import time 
import tempfile 
import optparse
import tarfile
import re
import shutil
import math

progname = os.path.split(sys.argv[0])[1] 
myversion = 'V000.2 June 2012' 
verbose = False 
debug = False
toolFactoryURL = 'https://bitbucket.org/fubar/galaxytoolfactory'

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))

html_escape_table = {
     "&": "&amp;",
     ">": "&gt;",
     "<": "&lt;",
     "$": "\$"
     }

def html_escape(text):
     """Produce entities within text."""
     return "".join(html_escape_table.get(c,c) for c in text)


class ScriptRunner:
    """class is a wrapper for an arbitrary script
    """

    def __init__(self,opts=None,treatbashSpecial=True):
        """
        cleanup inputs, setup some outputs
        
        """
        self.treatbashSpecial = treatbashSpecial
        if opts.output_dir: # simplify for the tool tarball
            os.chdir(opts.output_dir)
        self.thumbformat = 'jpg'
        self.opts = opts
        self.toolname = re.sub('[^a-zA-Z0-9_]+', '', opts.tool_name) # a sanitizer now does this but..
        self.toolid = self.toolname
        self.myname = sys.argv[0] # get our name because we write ourselves out as a tool later
        self.pyfile = self.myname # crude but efficient - the cruft won't hurt much
        self.xmlfile = '%s.xml' % self.toolname
        s = open(self.opts.script_path,'r').readlines()
        s = [x.rstrip() for x in s] # remove pesky dos line endings if needed
        self.script = '\n'.join(s)
        fhandle,self.sfile = tempfile.mkstemp(prefix=self.toolname,suffix=".%s" % (opts.interpreter))
        tscript = open(self.sfile,'w') # use self.sfile as script source for Popen
        tscript.write(self.script)
        tscript.close()
        self.indentedScript = '\n'.join([' %s' % x for x in s]) # for restructured text in help
        self.escapedScript = '\n'.join([html_escape(x) for x in s])
        if opts.output_dir: # may not want these complexities 
            self.tlog = os.path.join(opts.output_dir,"%s_runner.log" % self.toolname)
            art = '%s.%s' % (self.toolname,opts.interpreter)
            artpath = os.path.join(self.opts.output_dir,art) # need full path
            artifact = open(artpath,'w') # use self.sfile as script source for Popen
            artifact.write(self.script)
            artifact.close()
        self.cl = []
        self.html = []
        a = self.cl.append
        a(opts.interpreter)
        if self.treatbashSpecial and opts.interpreter in ['bash','sh']:
            a(self.sfile)
        else:
            a('-') # stdin
        a(opts.input_tab)
        a(opts.output_tab)
        self.outFormats = 'tabular' # TODO make this an option at tool generation time
        self.inputFormats = 'tabular' # TODO make this an option at tool generation time
        self.test1Input = '%s_test1_input.xls' % self.toolname
        self.test1Output = '%s_test1_output.xls' % self.toolname
        self.test1HTML = '%s_test1_output.html' % self.toolname

    def makeXML(self):
        """
        Create a Galaxy xml tool wrapper for the new script as a string to write out
        fixme - use templating or something less fugly than this example of what we produce

        <tool id="reverse" name="reverse" version="0.01">
            <description>a tabular file</description>
            <command interpreter="python">
            reverse.py --script_path "$runMe" --interpreter "python" 
            --tool_name "reverse" --input_tab "$input1" --output_tab "$tab_file" 
            </command>
            <inputs>
            <param name="input1"  type="data" format="tabular" label="Select a suitable input file from your history"/><param name="job_name" type="text" label="Supply a name for the outputs to remind you what they contain" value="reverse"/>

            </inputs>
            <outputs>
            <data format="tabular" name="tab_file" label="${job_name}"/>

            </outputs>
            <help>
            
**What it Does**

Reverse the columns in a tabular file

            </help>
            <configfiles>
            <configfile name="runMe">
            
# reverse order of columns in a tabular file
import sys
inp = sys.argv[1]
outp = sys.argv[2]
i = open(inp,'r')
o = open(outp,'w')
for row in i:
     rs = row.rstrip().split('\t')
     rs.reverse()
     o.write('\t'.join(rs))
     o.write('\n')
i.close()
o.close()
 

            </configfile>
            </configfiles>
            </tool>
        
        """ 
        newXML="""<tool id="%(toolid)s" name="%(toolname)s" version="%(tool_version)s">
            %(tooldesc)s
            %(command)s
            <inputs>
            %(inputs)s
            </inputs>
            <outputs>
            %(outputs)s
            </outputs>
            <configfiles>
            <configfile name="runMe">
            %(script)s
            </configfile>
            </configfiles>
            %(tooltests)s
            <help>
            %(help)s
            </help>
            </tool>""" # needs a dict with toolname, toolid, interpreter, scriptname, command, inputs as a multi line string ready to write, outputs ditto, help ditto
               
        newCommand="""<command interpreter="python">
            %(toolname)s.py --script_path "$runMe" --interpreter "%(interpreter)s" 
            --tool_name "%(toolname)s" %(command_inputs)s %(command_outputs)s 
            </command>""" # may NOT be an input or htmlout
        tooltestsTabOnly = """<tests><test>
        <param name="input1" value="%(test1Input)s" ftype="tabular"/>
        <param name="job_name" value="test1"/>
        <param name="runMe" value="$runMe"/>
        <output name="tab_file" file="%(test1Output)s" ftype="tabular"/>
        </test></tests>"""
        tooltestsHTMLOnly = """<tests><test>
        <param name="input1" value="%(test1Input)s" ftype="tabular"/>
        <param name="job_name" value="test1"/>
        <param name="runMe" value="$runMe"/>
        <output name="html_file" file="%(test1HTML)s" ftype="html" lines_diff="5"/>
        </test></tests>"""
        tooltestsBoth = """<tests><test>
        <param name="input1" value="%(test1Input)s" ftype="tabular"/>
        <param name="job_name" value="test1"/>
        <param name="runMe" value="$runMe"/>
        <output name="tab_file" file="%(test1Output)s" ftype="tabular" />
        <output name="html_file" file="%(test1HTML)s" ftype="html" lines_diff="10"/>
        </test></tests>"""
        xdict = {}
        xdict['tool_version'] = self.opts.tool_version
        xdict['test1Input'] = self.test1Input
        xdict['test1HTML'] = self.test1HTML
        xdict['test1Output'] = self.test1Output   
        if self.opts.make_HTML and self.opts.output_tab <> 'None':
            xdict['tooltests'] = tooltestsBoth % xdict
        elif self.opts.make_HTML:
            xdict['tooltests'] = tooltestsHTMLOnly % xdict
        else:
            xdict['tooltests'] = tooltestsTabOnly % xdict
        xdict['script'] = self.escapedScript 
        # configfile is least painful way to embed script to avoid external dependencies
        # but requires escaping of <, > and $ to avoid Mako parsing
        if self.opts.help_text:
            xdict['help'] = open(self.opts.help_text,'r').read()
        else:
            xdict['help'] = 'Please ask the tool author for help as none was supplied at tool generation'
        coda = ['**Script**','Pressing execute will run the following code over your input file and generate some outputs in your history::']
        coda.append(self.indentedScript)
        coda.append('**Attribution** This Galaxy tool was created by %s at %s\nusing the Galaxy Tool Factory.' % (self.opts.user_email,timenow()))
        coda.append('See %s for details of that project' % (toolFactoryURL))
        coda.append('Please cite: Creating re-usable tools from scripts: The Galaxy Tool Factory. Ross Lazarus; Antony Kaspi; Mark Ziemann; The Galaxy Team. ')
        coda.append('Bioinformatics 2012; doi: 10.1093/bioinformatics/bts573')
        xdict['help'] = '%s\n%s' % (xdict['help'],'\n'.join(coda))
        if self.opts.tool_desc:
            xdict['tooldesc'] = '<description>%s</description>' % self.opts.tool_desc
        else:
            xdict['tooldesc'] = ''
        xdict['command_outputs'] = '' 
        xdict['outputs'] = '' 
        if self.opts.input_tab <> 'None':
            xdict['command_inputs'] = '--input_tab "$input1" ' # the space may matter a lot if we append something
            xdict['inputs'] = '<param name="input1"  type="data" format="%s" label="Select a suitable input file from your history"/> \n' % self.inputFormats
        else:
            xdict['command_inputs'] = '' # assume no input - eg a random data generator       
            xdict['inputs'] = ''
        xdict['inputs'] += '<param name="job_name" type="text" label="Supply a name for the outputs to remind you what they contain" value="%s"/> \n' % self.toolname
        xdict['toolname'] = self.toolname
        xdict['toolid'] = self.toolid
        xdict['interpreter'] = self.opts.interpreter
        xdict['scriptname'] = self.sfile
        if self.opts.make_HTML:
            xdict['command_outputs'] += ' --output_dir "$html_file.files_path" --output_html "$html_file" --make_HTML "yes" '
            xdict['outputs'] +=  ' <data format="html" name="html_file" label="${job_name}.html"/>\n'
        if self.opts.output_tab <> 'None':
            xdict['command_outputs'] += ' --output_tab "$tab_file"'
            xdict['outputs'] += ' <data format="%s" name="tab_file" label="${job_name}"/>\n' % self.outFormats
        xdict['command'] = newCommand % xdict
        xmls = newXML % xdict
        xf = open(self.xmlfile,'w')
        xf.write(xmls)
        xf.write('\n')
        xf.close()
        # ready for the tarball


    def makeTooltar(self):
        """
        a tool is a gz tarball with eg
        /toolname/tool.xml /toolname/tool.py /toolname/test-data/test1_in.foo ...
        """
        retval = self.run()
        if retval:
            print >> sys.stderr,'## Run failed. Cannot build yet. Please fix and retry'
            sys.exit(1)
        self.makeXML()
        tdir = self.toolname
        os.mkdir(tdir)
        if self.opts.input_tab <> 'None': # no reproducible test otherwise? TODO: maybe..
            testdir = os.path.join(tdir,'test-data')
            os.mkdir(testdir) # make tests directory
            shutil.copyfile(self.opts.input_tab,os.path.join(testdir,self.test1Input))
            if self.opts.output_tab <> 'None':
                shutil.copyfile(self.opts.output_tab,os.path.join(testdir,self.test1Output))
            if self.opts.make_HTML:
                shutil.copyfile(self.opts.output_html,os.path.join(testdir,self.test1HTML))
            if self.opts.output_dir:
                shutil.copyfile(self.tlog,os.path.join(testdir,'test1_out.log'))
        op = '%s.py' % self.toolname # new name
        outpiname = os.path.join(tdir,op) # path for the tool tarball
        pyin = os.path.basename(self.pyfile) # our name - we rewrite ourselves (TM)
        notes = ['# %s - a self annotated version of %s generated by running %s\n' % (op,pyin,pyin),]
        notes.append('# to make a new Galaxy tool called %s\n' % self.toolname)
        notes.append('# User %s at %s\n' % (self.opts.user_email,timenow()))
        pi = open(self.pyfile,'r').readlines() # our code becomes new tool wrapper (!) - first Galaxy worm
        notes += pi
        outpi = open(outpiname,'w')
        outpi.write(''.join(notes))
        outpi.write('\n')
        outpi.close()
        stname = os.path.join(tdir,self.sfile)
        if not os.path.exists(stname):
            shutil.copyfile(self.sfile, stname)
        xtname = os.path.join(tdir,self.xmlfile)
        if not os.path.exists(xtname):
            shutil.copyfile(self.xmlfile,xtname)
        tarpath = "%s.gz" % self.toolname
        tar = tarfile.open(tarpath, "w:gz")
        tar.add(tdir,arcname=self.toolname)
        tar.close()
        shutil.copyfile(tarpath,self.opts.new_tool)
        shutil.rmtree(tdir)
        ## TODO: replace with optional direct upload to local toolshed?
        return retval

    def compressPDF(self,inpdf=None,thumbformat='png'):
        """need absolute path to pdf
        """
        assert os.path.isfile(inpdf), "## Input %s supplied to %s compressPDF not found" % (inpdf,self.myName)
        hf,hlog = tempfile.mkstemp(suffix="%s.log" % self.toolname)
        sto = open(hlog,'w')
        outpdf = '%s_compressed' % inpdf
        cl = ["gs", "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dBATCH", "-sOutputFile=%s" % outpdf,inpdf]
        x = subprocess.Popen(cl,stdout=sto,stderr=sto,cwd=self.opts.output_dir)
        retval1 = x.wait()
        if retval1 == 0:
            os.unlink(inpdf)
            shutil.move(outpdf,inpdf)
        outpng = '%s.%s' % (os.path.splitext(inpdf)[0],thumbformat)
        cl2 = ['convert', inpdf, outpng]
        x = subprocess.Popen(cl2,stdout=sto,stderr=sto,cwd=self.opts.output_dir)
        retval2 = x.wait()
        sto.close()
        retval = retval1 or retval2
        return retval


    def getfSize(self,fpath,outpath):
        """
        format a nice file size string
        """
        size = ''
        fp = os.path.join(outpath,fpath)
        if os.path.isfile(fp):
            size = '0 B'
            n = float(os.path.getsize(fp))
            if n > 2**20:
                size = '%1.1f MB' % (n/2**20)
            elif n > 2**10:
                size = '%1.1f KB)' % (n/2**10)
            elif n > 0:
                size = '%d B' % (int(n))
        return size

    def makeHtml(self):
        """ Create an HTML file content to list all the artifacts found in the output_dir
        """

        galhtmlprefix = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"> 
        <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en"> 
        <head> <meta http-equiv="Content-Type" content="text/html; charset=utf-8" /> 
        <meta name="generator" content="Galaxy %s tool output - see http://g2.trac.bx.psu.edu/" /> 
        <title></title> 
        <link rel="stylesheet" href="/static/style/base.css" type="text/css" /> 
        </head> 
        <body> 
        <div class="toolFormBody"> 
        """ 
        galhtmlattr = """<hr/><div class="infomessage">This tool (%s) was generated by the <a href="https://bitbucket.org/fubar/galaxytoolfactory/overview">Galaxy Tool Factory</a></div><br/>""" 
        galhtmlpostfix = """</div></body></html>\n"""

        flist = os.listdir(self.opts.output_dir)
        flist = [x for x in flist if x <> 'Rplots.pdf']
        flist.sort()
        html = []
        html.append(galhtmlprefix % progname)
        html.append('<div class="infomessage">Galaxy Tool "%s" run at %s</div><br/>' % (self.toolname,timenow()))
        fhtml = []
        if len(flist) > 0:
            pdflist = []
            npdf = len([x for x in flist if os.path.splitext(x)[-1].lower() == '.pdf'])
            nacross = 1
            if npdf > 0:
               nacross = int(round(math.log(npdf,2)))
            nacross = max(1,nacross)
            width = min(400,int(1200/nacross))
            for rownum,fname in enumerate(flist):
                dname,e = os.path.splitext(fname)
                sfsize = self.getfSize(fname,self.opts.output_dir)
                if e.lower() == '.pdf' : # compress and make a thumbnail
                    thumb = '%s.%s' % (dname,self.thumbformat)
                    pdff = os.path.join(self.opts.output_dir,fname)
                    retval = self.compressPDF(inpdf=pdff,thumbformat=self.thumbformat)
                    if retval == 0:
                        pdflist.append((fname,thumb))
                if (rownum+1) % 2 == 0:
                    fhtml.append('<tr class="odd_row"><td><a href="%s">%s</a></td><td>%s</td></tr>' % (fname,fname,sfsize))
                else:
                    fhtml.append('<tr><td><a href="%s">%s</a></td><td>%s</td></tr>' % (fname,fname,sfsize))
            ntogo = nacross # counter for table row padding with empty cells
            if len(pdflist) > 0:
                html.append('<div><table class="simple" cellpadding="2" cellspacing="2">\n<tr>')
                for i,paths in enumerate(pdflist):
                    fname,thumb = paths
                    s= """<td><a href="%s"><img src="%s" title="Click to download a PDF of %s" hspace="5" width="%d" 
                       alt="Image called %s"/></a></td>\n""" % (fname,thumb,fname,width,fname)
                    if ((i+1) % nacross == 0):
                        s += '</tr>\n'
                        ntogo = 0
                        if i < (npdf - 1): # more to come
                            s += '<tr>'
                            ntogo = nacross
                    else:
                        ntogo -= 1
                    html.append(s)
                if html[-1].strip().endswith('</tr>'):
                    html.append('</table></div>\n')
                else:
                    if ntogo > 0: # pad
                        html.append('<td>&nbsp;</td>'*ntogo)
                    html.append('</tr></table></div>\n')
        if len(fhtml) > 0:
           fhtml.insert(0,'<div><table class="colored" cellpadding="3" cellspacing="3"><tr><th>Output File Name (click to view)</th><th>Size</th></tr>\n')
           fhtml.append('</table></div><br/>')
           html += fhtml # add all non-pdf files to the end of the display
        else:
            html.append('<div class="warningmessagelarge">### Error - %s returned no files - please confirm that parameters are sane</div>' % self.opts.interpreter)
        rlog = open(self.tlog,'r').readlines()
        rlog = [x for x in rlog if x.strip() > '']
        if len(rlog) > 1:
            html.append('<div class="toolFormTitle">%s log</div>\n<pre>\n' % self.opts.interpreter)
            html += rlog
            html.append('\n</pre>\n')
        html.append(galhtmlattr % (self.toolname))
        html.append(galhtmlpostfix)
        htmlf = file(self.opts.output_html,'w')
        htmlf.write('\n'.join(html))
        htmlf.write('\n')
        htmlf.close()
        self.html = html


    def run(self):
        """
        scripts must be small enough not to fill the pipe!
        """
        if self.treatbashSpecial and self.opts.interpreter in ['bash','sh']:
          retval = self.runBash()
        else:
            if self.opts.output_dir:
                sto = open(self.tlog,'w')
                sto.write('## Toolfactory generated command line = %s\n' % ' '.join(self.cl))
                sto.flush()
                p = subprocess.Popen(self.cl,shell=False,stdout=sto,stderr=sto,stdin=subprocess.PIPE,cwd=self.opts.output_dir)
            else:
                p = subprocess.Popen(self.cl,shell=False,stdin=subprocess.PIPE)
            p.stdin.write(self.script)
            p.stdin.close()
            retval = p.wait()
            if self.opts.output_dir:
                sto.close()
            if self.opts.make_HTML:
                self.makeHtml()
        return retval

    def runBash(self):
        """
        cannot use - for bash so use self.sfile
        """
        if self.opts.output_dir:
            s = '## Toolfactory generated command line = %s\n' % ' '.join(self.cl)
            sto = open(self.tlog,'w')
            sto.write(s)
            sto.flush()
            p = subprocess.Popen(self.cl,shell=False,stdout=sto,stderr=sto,cwd=self.opts.output_dir)
        else:
            p = subprocess.Popen(self.cl,shell=False)            
        retval = p.wait()
        if self.opts.output_dir:
            sto.close()
        if self.opts.make_HTML:
            self.makeHtml()
        return retval
  

def main():
    u = """
    This is a Galaxy wrapper. It expects to be called by a special purpose tool.xml as:
    <command interpreter="python">rgBaseScriptWrapper.py --script_path "$scriptPath" --tool_name "foo" --interpreter "Rscript"
    </command>
    """
    op = optparse.OptionParser()
    a = op.add_option
    a('--script_path',default=None)
    a('--tool_name',default=None)
    a('--interpreter',default=None)
    a('--output_dir',default=None)
    a('--output_html',default=None)
    a('--input_tab',default="None")
    a('--output_tab',default="None")
    a('--user_email',default='Unknown')
    a('--bad_user',default=None)
    a('--make_Tool',default=None)
    a('--make_HTML',default=None)
    a('--help_text',default=None)
    a('--tool_desc',default=None)
    a('--new_tool',default=None)
    a('--tool_version',default=None)
    opts, args = op.parse_args()
    assert not opts.bad_user,'UNAUTHORISED: %s is NOT authorized to use this tool until Galaxy admin adds %s to admin_users in universe_wsgi.ini' % (opts.bad_user,opts.bad_user)
    assert opts.tool_name,'## Tool Factory expects a tool name - eg --tool_name=DESeq'
    assert opts.interpreter,'## Tool Factory wrapper expects an interpreter - eg --interpreter=Rscript'
    assert os.path.isfile(opts.script_path),'## Tool Factory wrapper expects a script path - eg --script_path=foo.R'
    if opts.output_dir:
        try:
            os.makedirs(opts.output_dir)
        except:
            pass
    r = ScriptRunner(opts)
    if opts.make_Tool:
        retcode = r.makeTooltar()
    else:
        retcode = r.run()
    os.unlink(r.sfile)
    if retcode:
        sys.exit(retcode) # indicate failure to job runner


if __name__ == "__main__":
    main()


