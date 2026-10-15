# Copyright (c) 2005, Southpaw Technology. MIT; see LICENSE.TACTIC.
import re
basestring = str

class WikiUtil(object):
    '''Converts text into a wiki style'''

    def __init__(self, process_url=False, replace_tag=True):
        self.process_url = process_url
        self.replace_tag = replace_tag

    xxx = 0
        
    def convert(self, text):
        if not isinstance(text, basestring):
            text = str(text)
      
        text = self._replace_tag(text)

        # convert <> inside <code/>
        '''
        code_pat = re.compile(r'((?:.|\n)*)(<code>((?:.|\n)*)</code>)((?:.|\n)*)', re.M+re.I)
        m = code_pat.match(text)
        if m:
            group0 = m.groups()[0]
            group1 = m.groups()[1]
            group2 = m.groups()[2]
            group3 = m.groups()[3]
            group2 = self._replace_tag(group2)
            text = '%s<code>%s</code>%s' %(group0, group2, group3)
        else:    
            text = self._replace_linebreak(text)
        '''

        #text = r"%s" %text
        #text = re.sub(r"\\", "/", text)
        if self.process_url:
            proc = "((?:http|ftp)://)"
            url_part = "([a-z0-9\-.]+\.[a-z0-9\-]+)([\/]([a-z0-9_\/\-.?&%=+])*)"
            url_pat = re.compile(proc + url_part, re.IGNORECASE)
            m = url_pat.search(text)
           
            text = re.sub(url_pat, r"<a href='\1\2\3'><u>[\1\2...]</u></a>", text)

        if text == None:
            text = ""

        return text


    def _replace_linebreak(self, text):
        text = text.replace("\n", "<br/>")
        return text

    def _replace_tag(self, text):
        text = text.replace("<", "&spt_lt;")
        text = text.replace(">", "&spt_gt;")
        #text = text.replace("<", "&lt;")
        #text = text.replace(">", "&gt;")
        text = text.replace("\n", "<br/>")
        return text
