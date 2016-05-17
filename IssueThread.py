# -*- coding: utf-8 -*-

# ########################## Copyrights and license ############################
#                                                                              #
# Copyright 2016 David Roegiers <david.roegiers@gmail.com>                     #
#                                                                              #
# This file is part of the author's master thesis on OSS research :            #
# https://github.com/droegier/ThesisOSS                                        #
#                                                                              #
# This script is free software: you can redistribute it and/or modify it under #
# the terms of the GNU Lesser General Public License as published by the Free  #
# Software Foundation, either version 3 of the License, or (at your option)    #
# any later version.                                                           #
#                                                                              #
# This script is based on the PyGithub library v 1.26.0                        #
# http://pygithub.github.io/PyGithub/v1/introduction.html                      #
#                                                                              #
# ##############################################################################

"""
IssueThread picks up Issues from a repository and stores them in the 'issues.xml' file.
"""

import threading
import xml.etree.ElementTree as ET
import codecs
import ssl
import github
import time
import Repository

class IssueThread (threading.Thread):

    def __init__(self, locks, repository, gh_iterator):
        threading.Thread.__init__(self)
        self.lock_p = locks[0]
        self.lock_i = locks[1]
        self.R = repository
        self.ghi = gh_iterator

    def run(self):
        try:
            while True:
                issues = self.R.issue_q.get()
                for issue in issues:
                    self.lock_i.acquire()
                    try:
                        chk = self.R.issues_root.findall("./issue[@id='" + str(issue.number) + "']")
                    finally:
                        self.lock_i.release()
                    #[AMENDMENT1]
                    if (len(chk) == 0) and (issue.created_at.isocalendar()[0]*100+issue.created_at.isocalendar()[1] < 201618):
                    #if (len(chk) == 0) and issue.created_at.isocalendar()[0] < 2016:
                            flag = False
                            while not flag:
                                try:
                                    flag = self.handleIssue(issue)
                                except ssl.SSLError as error:
                                    print ' catched SSL : ' + error.message
                                    time.sleep(5)
                                except github.GithubException as error:
                                    print error.message
                                    print 'sleeping'
                                    for g in self.R.g:
                                        if g.get_rate_limit().rate.remaining == 0:
                                            print 'sleeping'
                                            time.sleep(g.rate_limiting_resettime - int(time.time()) + 10)
                                except Exception as error:
                                    if error.message == '_ssl.c:574: The handshake operation timed out':
                                        print error.message
                                        time.sleep(5)
                                    else:
                                        raise
                self.lock_p.acquire()
                try:
                    print self.R.g[self.ghi].get_user().login + '-cycle complete'
                finally:
                    self.lock_p.release()
                self.R.issue_q.task_done()
        finally:
            self.lock_i.acquire()
            try:
                self.R.issues_root.set('page',str(self.R.iss_page_nr-3) if self.R.iss_page_nr-3>0 else str(0))
                self.R.issues_tree.write('data/' + self.R.org_name + '/' + self.R.rep_name + '/issues.xml')
            finally:
                self.lock_i.release()

    def handleIssue(self, issue):
        self.lock_i.acquire()
        try:
            el = ET.SubElement(self.R.issues_root, 'issue')
            el.set('creator', issue.user.login)
            el.set('id', str(issue.number))
            if issue.assignee:
                el.set('assignee', str(issue.assignee))
            if issue.pull_request:
                el.set('pullrequest', 'yes')
            el.set('created_at', str(issue.created_at.day) + '/' + str(issue.created_at.month) + '/' + str(
                issue.created_at.year))
        finally:
            self.lock_i.release()
        if issue.comments > 0:
            comments = issue.get_comments()
            for comment in comments:
                self.lock_i.acquire()
                try:
                    el_c = ET.SubElement(el, 'comment')
                    el_c.set('creator', comment.user.login)
                    el_c.set('created_at',
                             str(comment.created_at.day) + '/' + str(comment.created_at.month) + '/' + str(
                                 comment.created_at.year))
                finally:
                    self.lock_i.release()
        self.lock_p.acquire()
        try:
            print "issue" + str(issue.created_at.day) + '.' + str(issue.created_at.month) + '.' + str(
                issue.created_at.year)
        finally:
            self.lock_p.release()
        return True

    def speak(self, str):
        self.lock_p.acquire()
        try:
            if self.R.logger.closed:
                self.R.logger = codecs.open('data/' + self.R.org_name + '/' + self.R.rep_name + '/log',mode='a',encoding='utf-8')
            self.R.logger.write(str + '\n')
            print str
        finally:
            self.lock_p.release()
